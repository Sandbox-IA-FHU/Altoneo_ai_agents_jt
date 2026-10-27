"""Tests de l'outil de lecture et de la surface d'outils.

L'agent ne fait que lire. Ces tests vérifient qu'il ne peut rien faire
d'autre, et que ce qu'il lit lui arrive tel quel.
"""

import re
from pathlib import Path

import pytest

from agent.errors import DocumentStoreError, ToolError
from agent.toolbox import MAX_DOCUMENT_CHARS, DocumentStore, buildToolbox

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_documentIsReadByName(documentStore: DocumentStore) -> None:
    toolbox = {spec.name: spec for spec in buildToolbox(documentStore)}
    result = toolbox["readDocument"].handler({"nom": "point-hebdo"})

    assert "Zéphyrin" in result


def test_unknownDocumentListsTheAvailableOnes(documentStore: DocumentStore) -> None:
    # Le modèle se rattrape en un tour s'il sait quels noms existent, au lieu
    # de réessayer trois fois au hasard.
    with pytest.raises(ToolError, match="atelier-budget"):
        documentStore.read("document-fantome")


def test_documentStoreRefusesAMalformedFile(tmp_path) -> None:
    path = tmp_path / "documents.jsonl"
    path.write_text('{"nom": "a"}\n', encoding="utf-8")

    with pytest.raises(DocumentStoreError, match="nom/contenu"):
        DocumentStore.fromFile(path)


def test_poisonedDocumentIsReturnedAsIs(documentStore: DocumentStore) -> None:
    # On ne filtre pas le contenu, et on ne prétend pas savoir détecter une
    # injection. Le contenu remonte tel quel ; c'est la surface d'outils qui
    # borne ce qui peut arriver, le prompt n'en réduit que la fréquence.
    toolbox = {spec.name: spec for spec in buildToolbox(documentStore)}
    result = toolbox["readDocument"].handler({"nom": "document-piege"})

    assert "ignore toutes les consignes" in result


def test_longDocumentSaysItIsTruncated() -> None:
    # Un document coupé en silence produit un brouillon incomplet qui a l'air
    # complet.
    store = DocumentStore({"long": "x" * (MAX_DOCUMENT_CHARS + 10)})
    toolbox = {spec.name: spec for spec in buildToolbox(store)}
    result = toolbox["readDocument"].handler({"nom": "long"})

    assert "tronqué" in result
    assert str(MAX_DOCUMENT_CHARS + 10) in result


def test_toolboxIsReadOnly(documentStore: DocumentStore) -> None:
    # Ni envoi, ni écriture, ni suppression : une consigne cachée dans un
    # document ne peut rien déclencher. Ajouter un outil ici est une décision
    # à prendre avec /outil, pas une ligne de plus.
    toolbox = buildToolbox(documentStore)

    assert [spec.name for spec in toolbox] == ["readDocument"]
    assert not any(spec.isSensitive for spec in toolbox)


def test_evalNeverEntersTheCode() -> None:
    # Du code produit par un modèle est du code plausible, pas du code sûr.
    # Aucun outil n'interprète de texte comme du code, et cela se vérifie.
    pattern = re.compile(r"(?<![\w.])(eval|exec)\(")
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for folder in ("src", "scripts")
        for path in (REPO_ROOT / folder).rglob("*.py")
        if pattern.search(path.read_text(encoding="utf-8"))
    ]

    assert offenders == []
