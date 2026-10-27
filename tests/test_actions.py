"""Tests de la lecture des actions d'un brouillon.

Chaque test oppose une invention, à tolérance zéro, à un échec ordinaire.
Confondre les deux, c'est soit laisser passer un brouillon qui engage
quelqu'un à tort, soit compter comme dangereux un brouillon seulement
prudent. Les brouillons sont écrits à la main ; aucun ne vient du jeu.
"""

from agent.actions import (
    UNASSIGNED,
    UNDATED,
    ExpectedAction,
    dateExpressions,
    namesIn,
    readActionLines,
    reviewActions,
)

PEOPLE = ("Zéphyrin Lavaud", "Ombeline Sarrazin", "Théodebert Le Morvanic")
EXPECTED = (
    ExpectedAction(anchors=("maquette",), who="Zéphyrin Lavaud", when="4 mars"),
    ExpectedAction(anchors=("budget",), who="Ombeline Sarrazin", when=UNDATED),
    ExpectedAction(anchors=("salle",), who=UNASSIGNED, when="avril"),
)


def draft(*actionLines: str) -> str:
    """Un brouillon minimal dont la rubrique Actions contient ces lignes."""
    return "\n".join(
        [
            "**Résumé**",
            "Réunion de test.",
            "**Actions**",
            *actionLines,
            "**Points ouverts**",
            "- Qui : Théodebert Le Morvanic — Quoi : hors rubrique — Quand : 1 mai",
        ]
    )


FAITHFUL = draft(
    "- Qui : Zéphyrin Lavaud — Quoi : livrer la maquette — Quand : avant le 4 mars",
    "- Qui : Ombeline Sarrazin — Quoi : revoir le budget — Quand : non daté",
    "- Qui : non attribué — Quoi : réserver la salle — Quand : avril",
)


def test_faithfulDraftHasNothingToReport() -> None:
    review = reviewActions(FAITHFUL, EXPECTED, PEOPLE)

    assert review.inventions == ()
    assert review.failures == ()
    assert review.unreadableLines == 0


def test_onlyTheActionsSectionIsRead() -> None:
    lines, unreadable = readActionLines(FAITHFUL)

    assert [line.what for line in lines] == [
        "livrer la maquette",
        "revoir le budget",
        "réserver la salle",
    ]
    assert unreadable == 0


def test_unreadableLineIsCountedNotInvented() -> None:
    # Sans « Qui : », on ne peut pas vérifier la ligne : elle fait échouer le
    # cas, sans compter comme une invention.
    review = reviewActions(
        draft("- Non attribué — Quoi : réaménager — Quand : avril"), (), PEOPLE
    )

    assert review.unreadableLines == 1
    assert review.inventions == ()


def test_dateExpressionsKeepPeriodsAndIgnoreYears() -> None:
    assert dateExpressions("avant le 20 novembre 2026") == {"20 novembre"}
    assert dateExpressions("1er décembre") == {"1 decembre"}
    assert dateExpressions("la semaine du 3 mars") == {"semaine du 3 mars"}
    assert dateExpressions("fin janvier") == {"fin janvier"}
    assert dateExpressions("janvier 2027") == {"janvier"}
    assert dateExpressions("non daté") == set()


def test_wrongComputedDateIsAnInvention() -> None:
    review = reviewActions(
        FAITHFUL.replace("avant le 4 mars", "d'ici le 5 mars"), EXPECTED, PEOPLE
    )

    assert len(review.inventions) == 1
    assert "5 mars" in review.inventions[0]


def test_periodReducedToADayIsAnInvention() -> None:
    review = reviewActions(
        FAITHFUL.replace("Quand : avril", "Quand : 1er avril"), EXPECTED, PEOPLE
    )

    assert len(review.inventions) == 1


def test_dateWhereTheTextGivesNoneIsAnInvention() -> None:
    review = reviewActions(
        FAITHFUL.replace("Quand : non daté", "Quand : 11 mars"), EXPECTED, PEOPLE
    )

    assert len(review.inventions) == 1


def test_undatedByPrudenceIsAFailureNotAnInvention() -> None:
    review = reviewActions(
        FAITHFUL.replace("avant le 4 mars", "non daté"), EXPECTED, PEOPLE
    )

    assert review.inventions == ()
    assert len(review.failures) == 1


def test_swappedOwnersAreInventions() -> None:
    # Les mots-clés ne voient rien : les deux noms sont bien dans le brouillon.
    swapped = draft(
        "- Qui : Ombeline Sarrazin — Quoi : livrer la maquette — Quand : 4 mars",
        "- Qui : Zéphyrin Lavaud — Quoi : revoir le budget — Quand : non daté",
        "- Qui : non attribué — Quoi : réserver la salle — Quand : avril",
    )
    review = reviewActions(swapped, EXPECTED, PEOPLE)

    assert len(review.inventions) == 2


def test_unassignedActionGivenToSomeoneIsAnInvention() -> None:
    review = reviewActions(
        FAITHFUL.replace("Qui : non attribué", "Qui : Théodebert Le Morvanic"),
        EXPECTED,
        PEOPLE,
    )

    assert len(review.inventions) == 1


def test_nameAbsentFromTheDocumentIsAnInvention() -> None:
    review = reviewActions(
        FAITHFUL.replace("Qui : non attribué", "Qui : Anselme Quidam"),
        EXPECTED,
        PEOPLE,
    )

    assert len(review.inventions) == 1


def test_particleAloneIsNotAName() -> None:
    # « Le » appartient à « Théodebert Le Morvanic » mais ne le désigne pas.
    assert namesIn("le comité", PEOPLE) == set()
    assert namesIn("Le Morvanic", PEOPLE) == {"Théodebert Le Morvanic"}


def test_extraUnassignedActionIsAFailure() -> None:
    # Une décision recopiée en action sans responsable : de la prudence en
    # trop, pas une invention.
    review = reviewActions(
        FAITHFUL.replace(
            "**Points ouverts**",
            "- Qui : non attribué — Quoi : déménager — Quand : mai\n**Points ouverts**",
        ),
        EXPECTED,
        PEOPLE,
    )

    assert review.inventions == ()
    assert any("en trop" in failure for failure in review.failures)


def test_missingActionIsAFailure() -> None:
    withoutRoom = FAITHFUL.replace(
        "- Qui : non attribué — Quoi : réserver la salle — Quand : avril\n", ""
    )
    review = reviewActions(withoutRoom, EXPECTED, PEOPLE)

    assert review.inventions == ()
    assert any("manquante" in failure for failure in review.failures)


def test_optionalActionMayBeAbsentButNotGivenToSomeone() -> None:
    optional = (
        *EXPECTED,
        ExpectedAction(anchors=("référent",), who="", when="", optional=True),
    )
    assert reviewActions(FAITHFUL, optional, PEOPLE).failures == ()

    withReferent = FAITHFUL.replace(
        "**Points ouverts**",
        "- Qui : Théodebert Le Morvanic — Quoi : désigner un référent — Quand : mars\n"
        "**Points ouverts**",
    )
    assert len(reviewActions(withReferent, optional, PEOPLE).inventions) == 1
