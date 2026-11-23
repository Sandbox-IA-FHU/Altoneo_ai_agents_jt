"""Tests du code hors modèle : lecture de la sortie, calculs, échéances 2777."""

import json
from datetime import date
from decimal import Decimal

import pytest

from agent.dividends import (
    Extraction,
    deadline2777,
    deadlines2777,
    describeChecks,
    incoherences,
    partnerAmounts,
    readExtraction,
)
from agent.toolbox import DocumentStore
from tests.expected_outputs import DIVIDEND_DOCUMENTS, loadRecords, perfectOutput

RECORDS = loadRecords()
STORE = DocumentStore.fromFile(DIVIDEND_DOCUMENTS)


def perfectExtraction(caseId: str) -> Extraction:
    record = next(r for r in RECORDS if r["cas_id"] == caseId)
    extraction = readExtraction(perfectOutput(record, STORE.read(record["document"])))
    assert extraction is not None
    return extraction


def test_outputIsReadWithOrWithoutFence() -> None:
    output = perfectOutput(RECORDS[0], STORE.read(RECORDS[0]["document"]))

    assert readExtraction(output) is not None
    assert readExtraction(f"```json\n{output}\n```") is not None


@pytest.mark.parametrize(
    "output",
    [
        "Voici l'extraction : {}",
        '{"distribution": "oui"}',
        "pas du JSON",
        "[]",
    ],
)
def test_unreadableOutputIsNotRepaired(output: str) -> None:
    assert readExtraction(output) is None


def test_textAroundTheJsonMakesItUnreadable() -> None:
    output = perfectOutput(RECORDS[0], STORE.read(RECORDS[0]["document"]))

    assert readExtraction(f"Voici l'extraction :\n{output}") is None


def test_partnerAmountsAreComputedByTheCode() -> None:
    amounts = partnerAmounts(perfectExtraction("d-01"))

    assert amounts == {
        "Isaure Pruneclaire": Decimal(18000),
        "Théophraste Glanebois": Decimal(6000),
    }


def test_partnerWithoutWrittenPartsHasNoAmount() -> None:
    assert set(partnerAmounts(perfectExtraction("d-23")).values()) == {None}


@pytest.mark.parametrize("record", RECORDS, ids=lambda record: record["cas_id"])
def test_codeFindsExactlyTheDeclaredIncoherences(record: dict) -> None:
    # Le générateur a calculé les incohérences de son côté ; le code de
    # l'agent doit retrouver les mêmes à partir d'une extraction fidèle.
    extraction = readExtraction(perfectOutput(record, STORE.read(record["document"])))
    assert extraction is not None

    assert incoherences(extraction) == set(record["incoherences_attendues"])


def test_totalCheckDoesNotConcludeWithoutWrittenParts() -> None:
    # d-23 et d-27 : la répartition des parts n'est pas écrite.
    assert incoherences(perfectExtraction("d-23")) == set()
    assert incoherences(perfectExtraction("d-27")) == set()


def test_deadlineIsTheFifteenthOfTheFollowingMonth() -> None:
    assert deadline2777(date(2026, 7, 15)) == date(2026, 8, 15)
    assert deadline2777(date(2026, 7, 31)) == date(2026, 8, 15)
    assert deadline2777(date(2026, 12, 3)) == date(2027, 1, 15)


def test_oneDeadlinePerPayment() -> None:
    deadlines = deadlines2777(perfectExtraction("d-04"))

    assert [(d.payment, d.paidOn, d.due) for d in deadlines] == [
        ("acompte", date(2026, 3, 10), date(2026, 4, 15)),
        ("solde", date(2026, 6, 30), date(2026, 7, 15)),
    ]


def test_noDeadlineWithoutPaymentDate() -> None:
    assert deadlines2777(perfectExtraction("d-05")) == []


def test_numericValueIsAccepted() -> None:
    record = json.loads(perfectOutput(RECORDS[0], STORE.read(RECORDS[0]["document"])))
    record["montant_par_part"]["valeur"] = 20

    extraction = readExtraction(json.dumps(record))

    assert extraction is not None
    assert partnerAmounts(extraction)["Isaure Pruneclaire"] == Decimal(18000)


def test_checksAreDescribedForTheCollaborator() -> None:
    lines = describeChecks(perfectExtraction("d-22"))
    text = "\n".join(lines)

    assert "à valider" in lines[0]
    assert "INCOHÉRENCE : le solde écrit" in text
    assert "échéance 2777 (acompte, payé le 2026-04-20) : 2026-05-15" in text
    assert "échéance 2777 (solde, payé le 2026-07-03) : 2026-08-15" in text


def test_checksSayWhenNothingCanBeComputed() -> None:
    assert "hors format" in describeChecks(None)[0]
    lines = describeChecks(perfectExtraction("d-05"))
    assert "aucune date de mise en paiement écrite" in "\n".join(lines)
