"""Lecture des montants et des dates écrits dans un PV.

Le modèle recopie les valeurs telles que le PV les écrit ; c'est ici que le
code les lit, sans aucun appel au modèle. Deux textes qui désignent le même
montant (« 24 000 euros », « 24000 € », « vingt-quatre mille euros ») donnent
le même nombre, et c'est ce nombre qu'on compare.

Ce qui n'est pas lu rend `None` : une valeur illisible n'est jamais devinée.
Les centimes écrits en lettres (« trois euros cinquante ») ne sont pas lus.
"""

import re
import unicodedata
from datetime import date
from decimal import Decimal

MONTHS = (
    "janvier",
    "fevrier",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "aout",
    "septembre",
    "octobre",
    "novembre",
    "decembre",
)

# Espaces ordinaires, insécables et fines, tous traités comme un espace.
_SPACE = "[   ]"
_FIGURE = re.compile(
    rf"(?<![\d,.])\d{{1,3}}(?:{_SPACE}\d{{3}})+(?:,\d+)?|\d+(?:[,.]\d+)?"
)
_DOT_THOUSANDS = re.compile(r"(?<=\d)\.(?=\d{3}(?!\d))")
_WRITTEN_DATE = re.compile(
    rf"\b(\d{{1,2}})(?:er)?\s+({'|'.join(MONTHS)})\s+(\d{{4}})\b"
)
_NUMERIC_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

_UNITS = {
    "zero": 0,
    "un": 1,
    "une": 1,
    "deux": 2,
    "trois": 3,
    "quatre": 4,
    "cinq": 5,
    "six": 6,
    "sept": 7,
    "huit": 8,
    "neuf": 9,
    "dix": 10,
    "onze": 11,
    "douze": 12,
    "treize": 13,
    "quatorze": 14,
    "quinze": 15,
    "seize": 16,
    "trente": 30,
    "quarante": 40,
    "cinquante": 50,
    "soixante": 60,
}
_NUMBER_WORDS = {
    *_UNITS,
    "vingt",
    "vingts",
    "cent",
    "cents",
    "mille",
    "million",
    "millions",
}


def _plain(text: str) -> str:
    """Minuscules, sans accents."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def figuresIn(text: str) -> list[Decimal]:
    """Les nombres écrits en chiffres dans un texte, dans l'ordre.

    « 24 000 » et « 24.000 » valent 24000 ; « 4,80 » et « 4.80 » valent 4,8.
    """
    cleaned = _DOT_THOUSANDS.sub("", text)
    figures = []
    for match in _FIGURE.finditer(cleaned):
        digits = re.sub(_SPACE, "", match.group()).replace(",", ".")
        figures.append(Decimal(digits))
    return figures


def wordsValue(text: str) -> int | None:
    """Le nombre écrit en lettres dans un texte, ou `None` s'il n'y en a pas.

    Entiers seulement, jusqu'aux millions : « dix-huit mille », « soixante et
    onze », « quatre-vingt-dix », « deux cents ». Les mots qui ne sont pas des
    nombres sont ignorés.
    """
    total = current = 0
    seen = False
    words = re.split(r"[\s\-  (),;:]+", _plain(text))
    for index, word in enumerate(words):
        following = words[index + 1] if index + 1 < len(words) else ""
        # Un article (« un dividende »), sauf en fin de nombre (« vingt et un »)
        # ou devant un multiplicateur (« un million »).
        isArticle = word in ("un", "une") and following not in _NUMBER_WORDS
        if isArticle and not seen:
            continue
        if word in _UNITS:
            current += _UNITS[word]
        elif word in ("vingt", "vingts"):
            # « quatre-vingt » : le quatre déjà compté devient quatre-vingts.
            current += 76 if current % 100 == 4 else 20
        elif word in ("cent", "cents"):
            hundreds, rest = divmod(current, 100)
            current = hundreds * 100 + max(rest, 1) * 100
        elif word == "mille":
            total += max(current, 1) * 1000
            current = 0
        elif word in ("million", "millions"):
            total += max(current, 1) * 1_000_000
            current = 0
        else:
            continue
        seen = True
    return total + current if seen else None


def parseAmount(text: str) -> Decimal | None:
    """Le montant d'un texte, ou `None` s'il est absent, ambigu ou illisible.

    Quand le texte donne le montant en lettres et en chiffres, les deux
    doivent concorder.
    """
    figures = set(figuresIn(text))
    written = wordsValue(text)
    if len(figures) > 1:
        return None
    if figures and written is not None and Decimal(written) not in figures:
        return None
    if figures:
        return figures.pop()
    return Decimal(written) if written is not None else None


def datesIn(text: str) -> list[date]:
    """Les dates complètes d'un texte : « 1er juillet 2026 », « 06/07/2026 »…"""
    found: list[date] = []
    plain = _plain(text)
    candidates = [
        (int(year), MONTHS.index(month) + 1, int(day))
        for day, month, year in _WRITTEN_DATE.findall(plain)
    ]
    candidates += [
        (int(year), int(month), int(day))
        for day, month, year in _NUMERIC_DATE.findall(plain)
    ]
    candidates += [
        (int(year), int(month), int(day))
        for year, month, day in _ISO_DATE.findall(plain)
    ]
    for year, month, day in candidates:
        try:
            found.append(date(year, month, day))
        except ValueError:
            continue
    return found


def parseDate(text: str) -> date | None:
    """La date d'un texte, ou `None` s'il n'y en a pas ou s'il y en a plusieurs."""
    dates = set(datesIn(text))
    return dates.pop() if len(dates) == 1 else None
