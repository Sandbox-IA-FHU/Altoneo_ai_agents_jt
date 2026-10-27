"""Tests de la boucle d'agent, sans aucun appel réseau.

Les trois premiers tests portent sur les trois propriétés que le README
annonce comme non négociables. S'ils tombent, ce n'est pas un test à réparer :
c'est une régression de sécurité ou de charge du serveur.
"""

from agent.approval import AllowAll, DenyAll
from agent.loop import runAgent, summarizeTrace
from agent.models import STOP_COMPLETED, STOP_ITERATION_LIMIT
from agent.tools import ToolRegistry
from tests.conftest import LoopingClient, ScriptedClient, textTurn, toolTurn

PROMPT = "Consignes de test."


def test_iterationLimitStopsTheLoop(registry: ToolRegistry) -> None:
    # Sans plafond, ce client ferait tourner la boucle indéfiniment. C'est
    # exactement le scénario d'un agent qui occupe le LLM partagé toute la nuit.
    client = LoopingClient()

    trace = runAgent(
        client=client,
        registry=registry,
        approval=DenyAll(),
        systemPrompt=PROMPT,
        task="tourne en rond",
        maxIterations=4,
    )

    assert client.callCount == 4
    assert trace.stepCount == 4
    assert trace.stoppedReason == STOP_ITERATION_LIMIT


def test_iterationLimitIsNotSilent(registry: ToolRegistry) -> None:
    # Une boucle qui s'arrête sans le dire produit une réponse tronquée qu'on
    # prend pour une réponse.
    trace = runAgent(
        client=LoopingClient(),
        registry=registry,
        approval=DenyAll(),
        systemPrompt=PROMPT,
        task="tourne en rond",
        maxIterations=3,
    )

    assert "limite" in trace.finalText.lower()
    assert "3" in trace.finalText


def test_sensitiveToolNeedsApproval(
    registryWithSensitiveTool: ToolRegistry, sentDrafts: list[str]
) -> None:
    # L'agent n'a aucun outil sensible ; le mécanisme se teste avec l'outil
    # fictif `sendDraft` de conftest.py.
    client = ScriptedClient(
        [
            toolTurn(("c1", "sendDraft", {"destinataires": "toute l'équipe"})),
            textTurn("L'envoi a été refusé faute de validation."),
        ]
    )

    trace = runAgent(
        client=client,
        registry=registryWithSensitiveTool,
        approval=DenyAll(),
        systemPrompt=PROMPT,
        task="envoie le brouillon",
    )

    assert trace.refusedTools() == ["sendDraft"]
    # Rien n'est parti : le refus a bien empêché l'action.
    assert sentDrafts == []


def test_approvedSensitiveToolRuns(
    registryWithSensitiveTool: ToolRegistry, sentDrafts: list[str]
) -> None:
    client = ScriptedClient(
        [
            toolTurn(("c1", "sendDraft", {"destinataires": "toute l'équipe"})),
            textTurn("Brouillon envoyé."),
        ]
    )

    trace = runAgent(
        client=client,
        registry=registryWithSensitiveTool,
        approval=AllowAll(),
        systemPrompt=PROMPT,
        task="envoie le brouillon",
    )

    assert trace.refusedTools() == []
    assert sentDrafts == ["toute l'équipe"]


def test_nonSensitiveToolNeedsNoApproval(registry: ToolRegistry) -> None:
    # DenyAll refuse les outils sensibles, pas les autres : sinon l'agent ne
    # pourrait plus rien faire du tout en mode refus.
    client = ScriptedClient(
        [toolTurn(("c1", "readDocument", {"nom": "point-hebdo"})), textTurn("Voilà.")]
    )

    trace = runAgent(
        client=client,
        registry=registry,
        approval=DenyAll(),
        systemPrompt=PROMPT,
        task="résume le point hebdo",
    )

    assert trace.refusedTools() == []
    assert trace.toolNames() == ["readDocument"]


def test_loopStopsWhenTheModelStopsCallingTools(registry: ToolRegistry) -> None:
    client = ScriptedClient(
        [
            toolTurn(("c1", "readDocument", {"nom": "document-inconnu"})),
            toolTurn(("c2", "readDocument", {"nom": "point-hebdo"})),
            textTurn("Zéphyrin livre la maquette le 9 mars."),
        ]
    )

    trace = runAgent(
        client=client,
        registry=registry,
        approval=DenyAll(),
        systemPrompt=PROMPT,
        task="résume le point hebdo",
    )

    assert trace.stoppedReason == STOP_COMPLETED
    assert trace.stepCount == 3
    assert trace.finalText == "Zéphyrin livre la maquette le 9 mars."


def test_parallelToolResultsShareOneRoundTrip(registry: ToolRegistry) -> None:
    # Format OpenAI : un message « tool » par appel. Ce qui compte, c'est qu'ils
    # suivent tous le message de l'assistant et partent dans le même
    # aller-retour. Les étaler sur plusieurs tours apprend au modèle à ne plus
    # grouper ses appels, et coûte un tour complet à chaque fois.
    client = ScriptedClient(
        [
            toolTurn(
                ("c1", "readDocument", {"nom": "point-hebdo"}),
                ("c2", "readDocument", {"nom": "atelier-budget"}),
            ),
            textTurn("Fini."),
        ]
    )

    runAgent(
        client=client,
        registry=registry,
        approval=DenyAll(),
        systemPrompt=PROMPT,
        task="résume les deux réunions",
    )

    assert len(client.calls) == 2
    roles = [message["role"] for message in client.calls[1]]
    assert roles == ["user", "assistant", "tool", "tool"]
    toolCallIds = [message["tool_call_id"] for message in client.calls[1][2:]]
    assert toolCallIds == ["c1", "c2"]


def test_unknownToolBecomesAnErrorResult(registry: ToolRegistry) -> None:
    # Une exception qui remonte tue la boucle ; un résultat d'erreur permet à
    # l'agent de se rattraper.
    client = ScriptedClient(
        [toolTurn(("c1", "sendEmail", {})), textTurn("Cet outil n'existe pas.")]
    )

    trace = runAgent(
        client=client,
        registry=registry,
        approval=DenyAll(),
        systemPrompt=PROMPT,
        task="envoie un courriel",
    )

    outcome = trace.steps[0].outcomes[0]
    assert outcome.isError is True
    assert "sendEmail" in outcome.content
    assert trace.stoppedReason == STOP_COMPLETED


def test_toolFailureBecomesAnErrorResult(registry: ToolRegistry) -> None:
    client = ScriptedClient(
        [
            toolTurn(("c1", "readDocument", {"nom": "document-inexistant"})),
            textTurn("Ce document n'existe pas."),
        ]
    )

    trace = runAgent(
        client=client,
        registry=registry,
        approval=DenyAll(),
        systemPrompt=PROMPT,
        task="résume un document",
    )

    assert trace.steps[0].outcomes[0].isError is True


def test_traceSummaryLeaksNoContent(registry: ToolRegistry) -> None:
    # Une trace complète contient le contenu métier, intégralement. Le résumé
    # affiché et journalisé ne doit porter que des noms et des compteurs.
    client = ScriptedClient(
        [
            toolTurn(("c1", "readDocument", {"nom": "point-hebdo"})),
            textTurn("Zéphyrin livre la maquette le 9 mars."),
        ]
    )

    trace = runAgent(
        client=client,
        registry=registry,
        approval=DenyAll(),
        systemPrompt=PROMPT,
        task="résume le point hebdo",
    )
    summary = summarizeTrace(trace)

    assert "readDocument" in summary
    assert "Zéphyrin" not in summary
    assert "maquette" not in summary


def test_usageIsAccumulatedAcrossTurns(registry: ToolRegistry) -> None:
    client = ScriptedClient(
        [
            toolTurn(("c1", "readDocument", {"nom": "point-hebdo"})),
            textTurn("Une action."),
        ]
    )

    trace = runAgent(
        client=client,
        registry=registry,
        approval=DenyAll(),
        systemPrompt=PROMPT,
        task="résume",
    )

    assert trace.usage.inputTokens == 200
    assert trace.usage.outputTokens == 40
