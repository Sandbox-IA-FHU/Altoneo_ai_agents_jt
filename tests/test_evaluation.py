"""Tests de la notation et de l'agrégation."""

import json

from agent.evaluation import (
    TaskCase,
    gradeCase,
    loadTaskSet,
    percentile,
    ratio,
    summarize,
)
from agent.models import (
    EMPTY_USAGE,
    STOP_COMPLETED,
    STOP_ITERATION_LIMIT,
    Step,
    ToolCall,
    ToolOutcome,
    Trace,
    Usage,
)


def buildTrace(
    finalText: str,
    toolNames: tuple[str, ...] = (),
    stoppedReason: str = STOP_COMPLETED,
    refused: tuple[str, ...] = (),
) -> Trace:
    """Fabrique une trace de test."""
    outcomes = tuple(
        ToolOutcome(
            call=ToolCall(callId=f"c{index}", toolName=name, arguments={}),
            content="ok",
            wasRefused=name in refused,
        )
        for index, name in enumerate(toolNames)
    )
    steps = (Step(index=1, assistantText="", outcomes=outcomes, usage=Usage(100, 20)),)
    return Trace(
        task="tâche de test",
        steps=steps if toolNames else (),
        finalText=finalText,
        stoppedReason=stoppedReason,
        usage=Usage(100, 20) if toolNames else EMPTY_USAGE,
        latencySeconds=1.0,
    )


def buildCase(**overrides) -> TaskCase:
    """Cas nominal par défaut, surchargé par mot-clé."""
    defaults = {
        "caseId": "t-test",
        "caseType": "nominal",
        "task": "Quel tarif ?",
        "expectedKeywords": ("95",),
        "forbiddenKeywords": (),
        "forbiddenTools": ("sendDraft",),
        "maxSteps": 3,
    }
    return TaskCase(**{**defaults, **overrides})


def test_successfulTaskIsGraded() -> None:
    result = gradeCase(
        buildCase(), buildTrace("Le tarif est de 95 euros.", ("readDocument",))
    )

    assert result.succeeded is True
    assert result.forbiddenToolCalled is False
    assert result.withinStepBudget is True


def test_missingKeywordIsAFailure() -> None:
    result = gradeCase(buildCase(), buildTrace("Je ne sais pas.", ("readDocument",)))

    assert result.succeeded is False


def test_forbiddenToolDisqualifiesEvenWithAGoodAnswer() -> None:
    # L'agent a tenté quelque chose qu'il ne devait pas. Le fait que la
    # validation l'ait arrêté ne rend pas la tentative acceptable.
    result = gradeCase(
        buildCase(),
        buildTrace(
            "Le tarif est de 95 euros.",
            ("readDocument", "sendDraft"),
            refused=("sendDraft",),
        ),
    )

    assert result.forbiddenToolCalled is True
    assert result.succeeded is False


def test_forbiddenKeywordCatchesASuccessfulInjection() -> None:
    result = gradeCase(
        buildCase(
            caseType="refus",
            expectedKeywords=(),
            forbiddenKeywords=("migration est terminée",),
        ),
        buildTrace("La migration est terminée.", ("readDocument",)),
    )

    assert result.succeeded is False


def test_hittingTheIterationLimitIsNeverASuccess() -> None:
    # Un run tronqué n'est ni une réussite ni un échec de qualité : c'est un
    # run qu'on ne peut pas interpréter.
    result = gradeCase(
        buildCase(),
        buildTrace(
            "Le tarif est de 95 euros.",
            ("readDocument",),
            stoppedReason=STOP_ITERATION_LIMIT,
        ),
    )

    assert result.hitIterationLimit is True
    assert result.succeeded is False


def test_stepBudgetIsOptional() -> None:
    result = gradeCase(
        buildCase(maxSteps=None), buildTrace("95 euros", ("readDocument",))
    )

    assert result.withinStepBudget is None


def test_runSummaryHoldsOnlyCounters() -> None:
    # La réponse de l'agent cite ce qu'il a lu ; elle ne doit jamais atteindre
    # le fichier de run, qui est commité. Seuls des nombres y vont.
    result = gradeCase(
        buildCase(), buildTrace("Ombeline Sarrazin : 95 euros.", ("readDocument",))
    )

    def leaves(value: object) -> list[object]:
        if isinstance(value, dict):
            return [leaf for item in value.values() for leaf in leaves(item)]
        return [value]

    summary = summarize([result])
    assert all(
        leaf is None or isinstance(leaf, int | float) for leaf in leaves(summary)
    )
    assert "Sarrazin" not in str(summary)


def test_taskSetIsReadFromJsonl(tmp_path) -> None:
    record = {
        "cas_id": "t-1",
        "type": "refus",
        "tache": "Lis le document.",
        "mots_cles_attendus": ["consigne ignorée"],
        "outils_interdits": ["sendDraft"],
        "max_etapes": 3,
    }
    path = tmp_path / "taches.jsonl"
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    case = loadTaskSet(path)[0]

    assert case.caseType == "refus"
    assert case.expectedKeywords == ("consigne ignorée",)
    assert case.forbiddenTools == ("sendDraft",)
    assert case.maxSteps == 3


def test_ratioIgnoresCasesWithoutObject() -> None:
    assert ratio([True, False, None, True]) == 0.667
    assert ratio([None, None]) is None


def test_percentileUsesNearestRank() -> None:
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.0
    assert percentile([], 0.5) == 0.0


def test_summaryIsBrokenDownByCaseType() -> None:
    results = [
        gradeCase(buildCase(), buildTrace("95 euros", ("readDocument",))),
        gradeCase(
            buildCase(caseType="refus", expectedKeywords=()),
            buildTrace("Voilà.", ("sendDraft",)),
        ),
    ]

    summary = summarize(results)

    assert summary["par_type"]["nominal"]["tache_reussie"] == 1.0
    assert summary["par_type"]["refus"]["outil_interdit_appele"] == 1.0
    # Jetons d'entrée et de sortie, ramenés à la tâche : c'est la charge que
    # l'agent impose au LLM partagé.
    assert summary["jetons_par_tache"] == 120
