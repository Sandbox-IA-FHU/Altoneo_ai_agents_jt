"""Le détail d'un run cite les PV : il ne doit jamais pouvoir entrer dans le dépôt."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from evaluate_detail import isInsideRepository, isSafeLabel  # noqa: E402


def test_detailFolderInsideTheRepositoryIsRefused() -> None:
    assert isInsideRepository(REPO_ROOT)
    assert isInsideRepository(REPO_ROOT / "evaluations" / "runs")


def test_detailFolderOutsideTheRepositoryIsAccepted() -> None:
    assert not isInsideRepository(REPO_ROOT.parent / "sorties-runs")


def test_labelCannotLeaveTheOutputFolder() -> None:
    assert isSafeLabel("essai-lecture")
    assert not isSafeLabel("../evaluations/runs/x")
    assert not isSafeLabel("sous/dossier")
    assert not isSafeLabel("")
