"""Le prompt ne contient aucun cas du jeu : sinon le score ne veut rien dire."""

import json
import re
from pathlib import Path

import pytest

from agent.toolbox import DocumentStore, buildToolbox
from tests.expected_outputs import DIVIDEND_DOCUMENTS, DIVIDEND_SET, REPO_ROOT

PROMPTS = sorted((REPO_ROOT / "prompts").glob("agent_v*.md"))
MARKERS = ("non indiqué", "consigne ignorée")


def fourWordSequences(text: str) -> set[str]:
    words = re.findall(r"\w+", text.lower())
    return {" ".join(words[i : i + 4]) for i in range(len(words) - 3)}


def setTexts() -> str:
    """Le texte des PV et des tâches du jeu."""
    documents = DocumentStore.fromFile(DIVIDEND_DOCUMENTS).documents.values()
    with DIVIDEND_SET.open(encoding="utf-8") as handle:
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


@pytest.mark.parametrize("path", PROMPTS, ids=lambda path: path.name)
def test_markersAreWrittenWordForWord(path: Path) -> None:
    # La notation les cherche tels quels : les modifier, c'est modifier le jeu.
    for marker in MARKERS:
        assert f"« {marker} »" in promptText(path)


def test_toolDescriptionSharesNoFourWordSequenceWithTheSet() -> None:
    # La description part vers le modèle à chaque tour, comme le prompt.
    description = buildToolbox(DocumentStore({"x": ""}))[0].description
    assert fourWordSequences(description) & fourWordSequences(setTexts()) == set()
