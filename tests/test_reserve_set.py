"""Contrôles du jeu de réserve.

Ce jeu a été écrit par un sous-agent qui n'a lu ni le prompt, ni le jeu
principal, ni son générateur. Il n'a pas de générateur : ses fichiers sont
contrôlés ici, tels quels, à chaque passage de la CI.

Il ne sert jamais à écrire ou retoucher un prompt (voir CLAUDE.md).
"""

import json
import re
from collections import Counter
from datetime import date

import pytest

from agent.dividends import deadline2777, incoherences, readExtraction
from agent.evaluation import gradeCase, loadTaskSet
from agent.models import STOP_COMPLETED, Trace, Usage
from agent.toolbox import MAX_DOCUMENT_CHARS, DocumentStore
from tests.expected_outputs import DIVIDEND_DOCUMENTS, REPO_ROOT, perfectOutput

RESERVE_SET = REPO_ROOT / "evaluations" / "jeux" / "reserve_taches_dividendes.jsonl"
RESERVE_DOCUMENTS = REPO_ROOT / "evaluations" / "jeux" / "reserve_pv_dividendes.jsonl"
COMPOSITION = {"nominal": 4, "difficile": 6, "refus": 5}
HIDDEN_MARKER = "consigne ignorée"
NOT_GIVEN = "non indiqué"

WEEKDAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)
WRITTEN_DAY = re.compile(
    rf"\b({'|'.join(WEEKDAYS)}) (\d{{1,2}})(?:er)? ({'|'.join(MONTHS)}) (\d{{4}})",
    re.IGNORECASE,
)

with RESERVE_SET.open(encoding="utf-8") as handle:
    RECORDS = [json.loads(line) for line in handle if line.strip()]
STORE = DocumentStore.fromFile(RESERVE_DOCUMENTS)
CASES = {case.caseId: case for case in loadTaskSet(RESERVE_SET)}
IDS = [record["cas_id"] for record in RECORDS]


def contains(text: str, value: str) -> bool:
    """`value` dans `text`, sans prendre « 12 000 » dans « 112 000 »."""
    return re.search(rf"(?<![\w,]){re.escape(value)}(?![\w])", text) is not None


def documentOf(record: dict) -> str:
    """Le PV entier ; vide pour un document volontairement introuvable."""
    return STORE.documents.get(record["document"], "")


def expectedTexts(value: object) -> list[str]:
    if isinstance(value, dict):
        if "texte" in value:
            return [str(value["texte"])]
        return [text for item in value.values() for text in expectedTexts(item)]
    if isinstance(value, list):
        return [text for item in value for text in expectedTexts(item)]
    return []


def paymentDates(expected: dict) -> list[date]:
    dates = []
    paid = expected["date_mise_en_paiement"]
    if isinstance(paid, dict):
        dates.append(date.fromisoformat(paid["valeur"]))
    interim = expected["acompte_hors_ag"]
    if interim and isinstance(interim["date"], dict):
        dates.append(date.fromisoformat(interim["date"]["valeur"]))
    return dates


def test_compositionAndUniqueness() -> None:
    assert Counter(record["type"] for record in RECORDS) == COMPOSITION
    assert len(set(IDS)) == len(IDS)
    main = DocumentStore.fromFile(DIVIDEND_DOCUMENTS).listNames()
    assert not set(STORE.listNames()) & set(main)


def test_setCoversTheHardestTraps() -> None:
    assert sum(bool(record["valeurs_apres_coupure"]) for record in RECORDS) >= 2
    assert any(HIDDEN_MARKER in record["mots_cles_attendus"] for record in RECORDS)


@pytest.mark.parametrize("record", RECORDS, ids=IDS)
def test_missingDocumentIsOnlyForAnUnreadableCase(record: dict) -> None:
    if record["document"] not in STORE.documents:
        assert record["attendu"]["distribution"] == NOT_GIVEN


@pytest.mark.parametrize("record", RECORDS, ids=IDS)
def test_expectedValuesAreInThePartRead(record: dict) -> None:
    visible = documentOf(record)[:MAX_DOCUMENT_CHARS]
    for text in expectedTexts(record["attendu"]):
        assert text in visible, text


@pytest.mark.parametrize("record", RECORDS, ids=IDS)
def test_valuesAfterTheCutAreReallyAfterIt(record: dict) -> None:
    document = documentOf(record)
    for text in record["valeurs_apres_coupure"]:
        assert not contains(document[:MAX_DOCUMENT_CHARS], text), text
        assert contains(document[MAX_DOCUMENT_CHARS:], text), text


@pytest.mark.parametrize("record", RECORDS, ids=IDS)
def test_weekdaysMatchTheirDates(record: dict) -> None:
    for weekday, day, month, year in WRITTEN_DAY.findall(documentOf(record)):
        actual = date(int(year), MONTHS.index(month.lower()) + 1, int(day))
        assert WEEKDAYS[actual.weekday()] == weekday.lower(), f"{weekday} {day} {month}"


@pytest.mark.parametrize("record", RECORDS, ids=IDS)
def test_forbiddenValuesAreAbsentFromThePv(record: dict) -> None:
    # Seules les valeurs d'une consigne cachée sont dans le PV.
    if HIDDEN_MARKER in record["mots_cles_attendus"]:
        return
    document = documentOf(record)
    for text in record["inventions_interdites"]:
        assert not contains(document, text), text


@pytest.mark.parametrize("record", RECORDS, ids=IDS)
def test_everyPaymentDeadlineIsForbidden(record: dict) -> None:
    forbidden = record["inventions_interdites"]
    for paidOn in paymentDates(record["attendu"]):
        due = deadline2777(paidOn)
        assert due.isoformat() in forbidden, due


@pytest.mark.parametrize("record", RECORDS, ids=IDS)
def test_codeFindsExactlyTheDeclaredIncoherences(record: dict) -> None:
    visible = documentOf(record)[:MAX_DOCUMENT_CHARS]
    extraction = readExtraction(perfectOutput(record, visible))
    assert extraction is not None

    assert incoherences(extraction) == set(record["incoherences_attendues"])


@pytest.mark.parametrize("record", RECORDS, ids=IDS)
def test_answerKeyPassesItsOwnGrading(record: dict) -> None:
    document = documentOf(record)
    output = perfectOutput(record, document[:MAX_DOCUMENT_CHARS])
    trace = Trace(
        task=record["tache"],
        steps=(),
        finalText=output,
        stoppedReason=STOP_COMPLETED,
        usage=Usage(0, 0),
        latencySeconds=0.0,
    )

    result = gradeCase(CASES[record["cas_id"]], trace, document)

    assert result.inventions == ()
    assert result.failures == ()
    assert result.succeeded is True


def test_noSurnameIsSharedWithTheMainSet() -> None:
    main = DocumentStore.fromFile(DIVIDEND_DOCUMENTS).documents.values()
    mainText = "\n".join(main)
    # Un même nom peut revenir dans un cas (une famille), jamais d'un cas à
    # l'autre ni depuis le jeu principal.
    byCase = [
        {partner["nom"].split()[-1] for partner in record["attendu"]["associes"]}
        for record in RECORDS
    ]
    surnames = [name for names in byCase for name in names]
    assert len(set(surnames)) == len(surnames)
    assert [name for name in surnames if re.search(rf"\b{name}\b", mainText)] == []
