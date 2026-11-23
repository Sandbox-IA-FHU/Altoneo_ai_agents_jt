"""Re-note hors LLM les sorties gardées par evaluate_detail.py.

    docker compose run --rm -T -v ~/sorties-runs:/sorties agent-dividendes \\
        python scripts/regrade_details.py /sorties/detail-v1-lecture-principal.txt

Après une correction du corrigé ou de la notation, rejoue la notation
actuelle sur les sorties de l'agent gardées hors du dépôt, sans appeler le
LLM. `--jeu` et `--documents` désignent le jeu des sorties (jeu principal par
défaut).

N'affiche que des compteurs et des identifiants de cas, jamais le contenu des
PV ni des sorties.
"""

import argparse
import re
import sys
from pathlib import Path

from agent.evaluation import gradeCase, loadTaskSet
from agent.models import STOP_COMPLETED, Trace, Usage
from agent.toolbox import DocumentStore

DEFAULT_DOCUMENTS = Path("evaluations/jeux/pv_dividendes.jsonl")
DEFAULT_TASK_SET = Path("evaluations/jeux/taches_dividendes.jsonl")
_CASE_HEADER = re.compile(r"^===== (\S+) ", re.MULTILINE)
_OUTPUT_MARKER = "--- sortie de l'agent ---\n"


def buildParser() -> argparse.ArgumentParser:
    """Décrit les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(description="Re-note des sorties gardées.")
    parser.add_argument("details", type=Path, nargs="+", help="Fichiers de détail.")
    parser.add_argument("--documents", type=Path, default=DEFAULT_DOCUMENTS)
    parser.add_argument("--jeu", type=Path, default=DEFAULT_TASK_SET)
    return parser


def readOutputs(path: Path) -> dict[str, str]:
    """Les sorties de l'agent d'un fichier de détail, par identifiant de cas."""
    text = path.read_text(encoding="utf-8")
    starts = [match.start() for match in _CASE_HEADER.finditer(text)]
    outputs = {}
    for start, end in zip(starts, [*starts[1:], len(text)], strict=True):
        block = text[start:end]
        caseId = _CASE_HEADER.match(block).group(1)
        outputs[caseId] = block.split(_OUTPUT_MARKER, 1)[1].strip()
    return outputs


def main() -> int:
    """Point d'entrée. Rend 0 en succès."""
    args = buildParser().parse_args()
    cases = {case.caseId: case for case in loadTaskSet(args.jeu)}
    documents = DocumentStore.fromFile(args.documents).documents

    for path in args.details:
        outputs = readOutputs(path)
        failed, invented, unreadable = [], [], []
        for caseId, output in outputs.items():
            case = cases[caseId]
            trace = Trace(
                task=case.task,
                steps=(),
                finalText=output,
                stoppedReason=STOP_COMPLETED,
                usage=Usage(0, 0),
                latencySeconds=0.0,
            )
            result = gradeCase(case, trace, documents.get(case.document, ""))
            if not result.succeeded:
                failed.append(caseId)
            if result.inventionDetected:
                invented.append(caseId)
            if result.unreadableOutput:
                unreadable.append(caseId)
        print(
            f"{path.name} : {len(outputs) - len(failed)}/{len(outputs)} réussis ; "
            f"ratés {', '.join(failed) or '—'} ; "
            f"invention {', '.join(invented) or '—'} ; "
            f"format {', '.join(unreadable) or '—'}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
