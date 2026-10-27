"""Lecture et contrôle des actions d'un brouillon de compte rendu.

Les mots-clés disent si un nom ou une date figure quelque part dans le
brouillon ; ils ne disent pas à quelle action il est rattaché. Ce module lit
la rubrique « Actions » dans le format que le prompt impose,

    - Qui : … — Quoi : … — Quand : …

rapproche chaque ligne d'une action attendue du jeu par ses mots d'ancrage, et
sépare deux choses que la notation ne doit pas confondre :

- **une invention** : un responsable qui ne s'est pas engagé, une échéance
  que le texte ne donne pas, une date mal calculée ou périmée. Tolérance zéro ;
- **un échec** : marqueur manquant, action oubliée, action en trop sans
  responsable. Compté dans la réussite, pas comme une invention.

Une ligne d'action qui ne suit pas le format est illisible : on ne peut pas
vérifier qu'elle n'invente rien, et elle fait échouer le cas.
"""

import re
import unicodedata
from dataclasses import dataclass

UNASSIGNED = "non attribué"
UNDATED = "non daté"

_MONTHS = (
    "janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|"
    "novembre|decembre"
)
# Dans l'ordre : une semaine, un jour précis, un mois éventuellement qualifié.
_DATE_EXPRESSION = re.compile(
    rf"semaine du (\d{{1,2}})(?:er)? ({_MONTHS})"
    rf"|(\d{{1,2}})(?:er)? ({_MONTHS})"
    rf"|(?:(debut|fin|mi)[- ](?:de |d')?)?\b({_MONTHS})\b"
)
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.*)$")
_ACTION_LINE = re.compile(
    r"qui\s*:\s*(?P<who>.*?)\s*[—–-]+\s*quoi\s*:\s*(?P<what>.*?)"
    r"\s*[—–-]+\s*quand\s*:\s*(?P<when>.*)$",
    re.IGNORECASE,
)
_SECTION_END = ("points ouverts", "decision", "resume", "remarque")
_CAPITALIZED = re.compile(r"\b[A-ZÉÈÊÀÂÎÏÔÛÇ][\w'’-]*")
# Mots à majuscule qui ne désignent pas une personne dans un champ « Qui ».
_NOT_A_NAME = {
    "a",
    "aucun",
    "aucune",
    "animateur",
    "animatrice",
    "chaque",
    "comite",
    "direction",
    "ensemble",
    "equipe",
    "groupe",
    "l",
    "la",
    "le",
    "les",
    "non",
    "organisateur",
    "organisatrice",
    "participants",
    "personne",
    "qui",
    "responsable",
    "service",
    "services",
    "tous",
    "tout",
    "toutes",
}
# Une particule (« Le », « El ») n'identifie personne à elle seule.
_MIN_NAME_PART = 3


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


_UNASSIGNED = _normalize(UNASSIGNED)
_UNDATED = _normalize(UNDATED)


@dataclass(frozen=True)
class ExpectedAction:
    """Une action du document, telle qu'un brouillon fidèle la rapporte.

    `anchors` sont des racines de mots : une ligne dont le « Quoi » en
    contient au moins une est rapprochée de cette action. Une action
    `optional` peut manquer et n'a ni responsable ni date attendus ; seule
    une personne inventée y est relevée.
    """

    anchors: tuple[str, ...]
    who: str
    when: str
    optional: bool = False


@dataclass(frozen=True)
class ActionLine:
    """Une ligne lue dans la rubrique « Actions » du brouillon."""

    who: str
    what: str
    when: str


@dataclass(frozen=True)
class ActionReview:
    """Ce que le contrôle des actions a relevé dans un brouillon."""

    inventions: tuple[str, ...]
    failures: tuple[str, ...]
    unreadableLines: int


def readActionLines(draft: str) -> tuple[list[ActionLine], int]:
    """Lit la rubrique « Actions ». Rend les lignes lues et le nombre d'illisibles."""
    lines: list[ActionLine] = []
    unreadable = 0
    inSection = False
    for rawLine in draft.splitlines():
        header = _normalize(rawLine).strip().strip("*#> ").strip()
        if header.startswith("actions"):
            inSection = True
            continue
        if not inSection:
            continue
        if header.startswith(_SECTION_END):
            break
        bullet = _BULLET.match(rawLine)
        if bullet is None:
            continue
        match = _ACTION_LINE.search(bullet.group(1))
        if match is None:
            unreadable += 1
            continue
        lines.append(
            ActionLine(
                who=match.group("who").strip(),
                what=match.group("what").strip(),
                when=match.group("when").strip(),
            )
        )
    return lines, unreadable


def dateExpressions(text: str) -> set[str]:
    """Les repères de date d'un texte, sous forme normalisée.

    « avant le 20 novembre » et « 20 novembre 2026 » donnent tous deux
    « 20 novembre » ; « la semaine du 30 novembre » reste une semaine, et
    « fin janvier » n'est pas « janvier ».
    """
    found: set[str] = set()
    for match in _DATE_EXPRESSION.finditer(_normalize(text)):
        weekDay, weekMonth, day, month, qualifier, monthAlone = match.groups()
        if weekDay:
            found.add(f"semaine du {int(weekDay)} {weekMonth}")
        elif day:
            found.add(f"{int(day)} {month}")
        else:
            found.add(f"{qualifier} {monthAlone}" if qualifier else monthAlone)
    return found


def namesIn(who: str, people: tuple[str, ...]) -> set[str]:
    """Les personnes désignées dans un champ « Qui ».

    Une personne du document est reconnue à son prénom ou à son nom. Un mot à
    majuscule qui n'est ni une personne du document ni un mot courant est
    rendu tel quel : c'est un nom que le document ne contient pas.
    """
    words = set(re.findall(r"[\w'-]+", _normalize(who)))
    found = {
        person
        for person in people
        if any(
            len(part) >= _MIN_NAME_PART and part in words
            for part in _normalize(person).split()
        )
    }
    known = {part for person in people for part in _normalize(person).split()}
    found |= {
        word
        for word in _CAPITALIZED.findall(who)
        if _normalize(word).strip("'’-") not in known | _NOT_A_NAME
    }
    return found


def reviewActions(
    draft: str, expected: tuple[ExpectedAction, ...], people: tuple[str, ...]
) -> ActionReview:
    """Rapproche les actions du brouillon des actions attendues."""
    lines, unreadable = readActionLines(draft)
    inventions: list[str] = []
    failures: list[str] = []
    matched: set[int] = set()

    for line in lines:
        index = _bestMatch(line, expected, matched)
        if index is None:
            if namesIn(line.who, people):
                inventions.append(
                    f"responsable sur une action inattendue : {line.what}"
                )
            elif _UNASSIGNED in _normalize(line.who):
                failures.append(f"action en trop sans responsable : {line.what}")
            continue
        matched.add(index)
        lineInventions, lineFailures = _checkLine(line, expected[index], people)
        inventions.extend(lineInventions)
        failures.extend(lineFailures)

    failures.extend(
        f"action manquante : {action.anchors[0]}"
        for index, action in enumerate(expected)
        if index not in matched and not action.optional
    )
    return ActionReview(
        inventions=tuple(inventions),
        failures=tuple(failures),
        unreadableLines=unreadable,
    )


def _bestMatch(
    line: ActionLine, expected: tuple[ExpectedAction, ...], matched: set[int]
) -> int | None:
    """L'action attendue, pas encore prise, dont le plus d'ancres sont présentes."""
    what = _normalize(line.what)
    best: int | None = None
    bestScore = 0
    for index, action in enumerate(expected):
        if index in matched:
            continue
        score = sum(_normalize(anchor) in what for anchor in action.anchors)
        if score > bestScore:
            best, bestScore = index, score
    return best


def _checkLine(
    line: ActionLine, action: ExpectedAction, people: tuple[str, ...]
) -> tuple[list[str], list[str]]:
    """Compare une ligne à son action attendue. Rend (inventions, échecs)."""
    inventions: list[str] = []
    failures: list[str] = []
    label = action.anchors[0]
    owner = None if action.optional or action.who == UNASSIGNED else action.who
    named = namesIn(line.who, people)

    if named - {owner}:
        inventions.append(f"responsable inventé pour « {label} » : {line.who}")
    elif owner is not None and owner not in named:
        failures.append(f"responsable manquant pour « {label} » : {line.who}")
    elif (
        owner is None
        and not action.optional
        and _UNASSIGNED not in _normalize(line.who)
    ):
        failures.append(f"« {UNASSIGNED} » manquant pour « {label} »")

    if action.optional:
        return inventions, failures

    got = dateExpressions(line.when)
    if action.when == UNDATED:
        if got:
            inventions.append(f"échéance inventée pour « {label} » : {line.when}")
        elif _UNDATED not in _normalize(line.when):
            failures.append(f"« {UNDATED} » manquant pour « {label} »")
    elif got != dateExpressions(action.when):
        if got:
            inventions.append(f"échéance fausse pour « {label} » : {line.when}")
        else:
            failures.append(f"échéance absente pour « {label} » : {line.when}")
    return inventions, failures
