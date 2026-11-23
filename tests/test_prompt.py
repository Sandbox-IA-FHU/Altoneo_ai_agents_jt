"""Le prompt ne contient aucun cas du jeu : sinon le score ne veut rien dire."""

import json
import re
from pathlib import Path

import pytest

from agent.toolbox import DocumentStore, buildToolbox
from tests.expected_outputs import DIVIDEND_DOCUMENTS, DIVIDEND_SET, REPO_ROOT

PROMPTS = sorted((REPO_ROOT / "prompts").glob("agent_v*.md"))
RESERVE_SET = REPO_ROOT / "evaluations" / "jeux" / "reserve_taches_dividendes.jsonl"
RESERVE_DOCUMENTS = REPO_ROOT / "evaluations" / "jeux" / "reserve_pv_dividendes.jsonl"
# Écrits avant que le jeu de réserve existe : une suite de mots commune avec
# lui ne peut être qu'une coïncidence (v1 en partage six, toutes banales).
WRITTEN_BEFORE_RESERVE = {"agent_v1.md"}
MARKERS = ("non indiqué", "consigne ignorée")


def fourWordSequences(text: str) -> set[str]:
    words = re.findall(r"\w+", text.lower())
    return {" ".join(words[i : i + 4]) for i in range(len(words) - 3)}


def setTexts(
    documentsPath: Path = DIVIDEND_DOCUMENTS, tasksPath: Path = DIVIDEND_SET
) -> str:
    """Le texte des PV et des tâches d'un jeu."""
    documents = DocumentStore.fromFile(documentsPath).documents.values()
    with tasksPath.open(encoding="utf-8") as handle:
        tasks = [json.loads(line)["tache"] for line in handle if line.strip()]
    return "\n".join([*documents, *tasks])


def promptText(path: Path) -> str:
    """Le prompt sans son en-tête de version."""
    return re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)


def test_thereIsAPrompt() -> None:
    assert PROMPTS


@pytest.mark.parametrize("path", PROMPTS, ids=lambda path: path.name)
def test_promptSharesNoFourWordSequenceWithTheSet(path: Path) -> None:
    assert fourWordSequences(promptText(path)) & fourWordSequences(setTexts()) == set()


@pytest.mark.parametrize(
    "path",
    [path for path in PROMPTS if path.name not in WRITTEN_BEFORE_RESERVE],
    ids=lambda path: path.name,
)
def test_laterPromptSharesNothingWithTheReserveSet(path: Path) -> None:
    # Le jeu de réserve ne sert jamais à écrire un prompt. Seules sont tolérées
    # les suites héritées d'un prompt écrit avant lui : aucun texte nouveau.
    reserve = setTexts(RESERVE_DOCUMENTS, RESERVE_SET)
    inherited = set().union(
        *(
            fourWordSequences(promptText(REPO_ROOT / "prompts" / name))
            for name in WRITTEN_BEFORE_RESERVE
        )
    )
    shared = fourWordSequences(promptText(path)) & fourWordSequences(reserve)
    assert shared - inherited == set()


@pytest.mark.parametrize("path", PROMPTS, ids=lambda path: path.name)
def test_markersAreWrittenWordForWord(path: Path) -> None:
    # La notation les cherche tels quels : les modifier, c'est modifier le jeu.
    for marker in MARKERS:
        assert f"« {marker} »" in promptText(path)


def test_toolDescriptionSharesNoFourWordSequenceWithTheSet() -> None:
    # La description part vers le modèle à chaque tour, comme le prompt.
    description = buildToolbox(DocumentStore({"x": ""}))[0].description
    assert fourWordSequences(description) & fourWordSequences(setTexts()) == set()
