"""Tests de la lecture des montants et des dates : le code lit, jamais le modèle."""

from datetime import date
from decimal import Decimal

import pytest

from agent.amounts import datesIn, parseAmount, parseDate, wordsValue


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("24 000 euros", "24000"),
        ("24000 €", "24000"),
        ("24 000 EUR", "24000"),
        ("24 000 €", "24000"),
        ("24.000 euros", "24000"),
        ("1,75 euro", "1.75"),
        ("4.80 EUR", "4.8"),
        ("2,50 euros", "2.5"),
        ("dix-huit mille euros", "18000"),
        ("dix-huit mille euros (18 000 €)", "18000"),
        ("trois euros (3 €)", "3"),
    ],
)
def test_amountsAreReadAsNumbers(text: str, expected: str) -> None:
    assert parseAmount(text) == Decimal(expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("soixante et onze", 71),
        ("soixante-dix", 70),
        ("quatre-vingts", 80),
        ("quatre-vingt-dix", 90),
        ("quatre-vingt-dix-neuf", 99),
        ("vingt et un", 21),
        ("deux cents", 200),
        ("cent quatre-vingts", 180),
        ("mille deux cent trente", 1230),
        ("deux cent mille", 200000),
        ("un million deux cent mille", 1200000),
        ("un dividende de dix-huit mille euros", 18000),
    ],
)
def test_amountsInWordsAreRead(text: str, expected: int) -> None:
    assert wordsValue(text) == expected


def test_disagreeingFormsAreNotGuessed() -> None:
    # Les lettres et les chiffres ne disent pas la même chose : aucune des
    # deux n'est choisie.
    assert parseAmount("dix-huit mille euros (19 000 €)") is None


def test_twoAmountsInOneValueAreNotGuessed() -> None:
    assert parseAmount("30 000 euros, soit 12 euros par part") is None


def test_textWithoutAmountGivesNothing() -> None:
    assert parseAmount("non indiqué") is None
    assert wordsValue("par part sociale") is None


@pytest.mark.parametrize(
    "text",
    ["15 juillet 2026", "le 15 juillet 2026", "06/07/2026", "2026-07-06"],
)
def test_datesAreRead(text: str) -> None:
    assert parseDate(text) in (date(2026, 7, 15), date(2026, 7, 6))


def test_firstOfTheMonthAndAccentedMonths() -> None:
    assert parseDate("1er juillet 2026") == date(2026, 7, 1)
    assert parseDate("3 août 2026") == date(2026, 8, 3)
    assert parseDate("10 décembre 2026") == date(2026, 12, 10)


def test_ambiguousOrIncompleteDateIsNotGuessed() -> None:
    assert parseDate("3 août") is None
    assert parseDate("entre le 2 mars 2026 et le 10 mars 2026") is None
    assert datesIn("31/02/2026") == []
