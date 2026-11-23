"""Lance l'évaluation en gardant le détail de chaque cas, hors du dépôt.

    docker compose run --rm -T -v ~/sorties-runs:/sorties agent-dividendes \\
        python scripts/evaluate_detail.py --sortie /sorties --cas d-21 \\
        --etiquette essai-lecture

Toutes les autres options sont celles de `scripts/evaluate.py`, qui fait le
run et écrit le fichier de run, avec ses seuls compteurs.

Ce script ajoute, pour relire les cas ratés, un fichier
`<sortie>/detail-<etiquette>.txt` : pour chaque cas, les inventions, les
échecs et la sortie complète de l'agent. Cette sortie cite le PV : le
fichier **n'entre jamais dans le dépôt** : le script refuse un fichier de
détail situé dans le dépôt. En conteneur, il ne voit pas ce qui est monté :
le dossier de l'hôte monté sur `/sorties` doit lui-même être hors du dépôt.
`detail-*.txt` est aussi dans `.gitignore`, comme second filet.

`--cas` limite le run à quelques cas, par identifiant.
"""

import argparse
import sys
from pathlib import Path

import evaluate

REPO_ROOT = Path(__file__).resolve().parents[1]


def buildParser() -> argparse.ArgumentParser:
    """Les options propres à ce script ; les autres vont à evaluate.py."""
    parser = argparse.ArgumentParser(
        description="Évalue l'agent et garde le détail par cas, hors du dépôt."
    )
    parser.add_argument(
        "--sortie",
        type=Path,
        required=True,
        help="Dossier du détail, hors du dépôt.",
    )
    parser.add_argument(
        "--cas",
        default="",
        help="Identifiants des cas à évaluer, séparés par des virgules.",
    )
    return parser


def isInsideRepository(path: Path) -> bool:
    """Vrai si `path` est dans le dépôt, ou est le dépôt lui-même."""
    resolved = path.resolve()
    return resolved == REPO_ROOT or REPO_ROOT in resolved.parents


def isSafeLabel(label: str) -> bool:
    """Une étiquette qui ne peut désigner qu'un fichier, dans le dossier donné."""
    return bool(label) and "/" not in label and "\\" not in label and ".." not in label


def main() -> int:
    """Point d'entrée. Rend le code de sortie de l'évaluation."""
    args, rest = buildParser().parse_known_args()
    if isInsideRepository(args.sortie):
        print(
            f"Dossier de sortie refusé : {args.sortie} est dans le dépôt, et le "
            "détail cite les PV. Choisir un dossier hors du dépôt.",
            file=sys.stderr,
        )
        return 1
    wanted = {caseId for caseId in args.cas.split(",") if caseId}
    label = evaluate.buildParser().parse_args(rest).etiquette
    detailPath = args.sortie / f"detail-{label}.txt"
    if not isSafeLabel(label) or isInsideRepository(detailPath):
        print(f"Étiquette refusée : {label!r}.", file=sys.stderr)
        return 1

    details = []
    loadTaskSet, gradeCase = evaluate.loadTaskSet, evaluate.gradeCase

    def loadWanted(path: Path):
        cases = loadTaskSet(path)
        return [case for case in cases if case.caseId in wanted] if wanted else cases

    def gradeAndKeep(case, trace, document=None):
        result = gradeCase(case, trace, document)
        details.append((case, trace, result))
        return result

    evaluate.loadTaskSet, evaluate.gradeCase = loadWanted, gradeAndKeep
    sys.argv = [sys.argv[0], *rest]
    code = evaluate.main()

    args.sortie.mkdir(parents=True, exist_ok=True)
    with detailPath.open("w", encoding="utf-8") as handle:
        for case, trace, result in details:
            handle.write(
                f"===== {case.caseId} [{case.caseType}] "
                f"{'ok' if result.succeeded else 'ECHEC'} — {trace.stepCount} "
                f"tour(s), outils {trace.toolNames()}\n"
            )
            for item in result.inventions:
                handle.write(f"  INVENTION : {item}\n")
            for item in result.failures:
                handle.write(f"  échec : {item}\n")
            if result.unreadableOutput:
                handle.write("  FORMAT : sortie illisible\n")
            handle.write(f"--- sortie de l'agent ---\n{trace.finalText}\n\n")
    print(f"Détail par cas écrit dans {detailPath} (hors du dépôt).")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
