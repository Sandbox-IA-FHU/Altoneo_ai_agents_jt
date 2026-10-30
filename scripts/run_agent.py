"""Fait tourner l'agent sur une tâche, en ligne de commande.

    uv run --env-file .env python scripts/run_agent.py "<tâche>" \
        --prompt prompts/<prompt>.md --documents evaluations/jeux/<documents>.jsonl

La tâche nomme le document à lire, tel qu'il est nommé dans le magasin.

Par défaut, toute action sensible est **refusée** sans rien demander. Pour être
interrogé à la place, mettre `APPROBATION=console` dans `.env` ou passer
`--approbation console`.

Ce script affiche un résumé de trace : noms d'outils, compteurs, jetons,
latence. Jamais le contenu des documents lus ni la réflexion du modèle — une
trace complète contient le contenu métier, intégralement.
"""

import argparse
import logging
import sys
from pathlib import Path

from agent.approval import ConsoleApproval, DenyAll
from agent.client import REASONING_EFFORT, OpenAICompatibleClient
from agent.config import APPROVAL_CONSOLE, VALID_APPROVAL_MODES, loadConfig
from agent.errors import ConfigError, DocumentStoreError, ModelCallError
from agent.loop import MAX_ITERATIONS, runAgent, summarizeTrace
from agent.models import STOP_ITERATION_LIMIT
from agent.toolbox import DocumentStore, buildToolbox
from agent.tools import ToolRegistry


def buildParser() -> argparse.ArgumentParser:
    """Décrit les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(description="Fait tourner l'agent.")
    parser.add_argument("tache", help="La tâche, entre guillemets.")
    parser.add_argument(
        "--prompt", type=Path, required=True, help="Prompt système (fichier)."
    )
    parser.add_argument(
        "--documents",
        type=Path,
        required=True,
        help="Magasin de documents JSONL.",
    )
    parser.add_argument(
        "--approbation",
        choices=VALID_APPROVAL_MODES,
        default=None,
        help="Remplace APPROBATION pour cette exécution.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=MAX_ITERATIONS,
        dest="maxIterations",
        help=f"Plafond d'itérations (défaut : {MAX_ITERATIONS}).",
    )
    return parser


def main() -> int:
    """Point d'entrée. Rend 0 en succès, 1 sur une erreur attendue."""
    args = buildParser().parse_args()

    try:
        config = loadConfig()
    except ConfigError as error:
        print(f"Configuration : {error}", file=sys.stderr)
        return 1

    logging.basicConfig(level=config.logLevel, format="%(levelname)s %(message)s")

    try:
        store = DocumentStore.fromFile(args.documents)
    except DocumentStoreError as error:
        print(f"Documents : {error}", file=sys.stderr)
        return 1

    try:
        systemPrompt = args.prompt.read_text(encoding="utf-8")
    except OSError as error:
        print(f"Prompt : {error}", file=sys.stderr)
        return 1

    registry = ToolRegistry(buildToolbox(store))
    mode = args.approbation or config.approvalMode
    approval = ConsoleApproval() if mode == APPROVAL_CONSOLE else DenyAll()

    print(
        f"Modèle {config.model}, réflexion {REASONING_EFFORT}, "
        f"plafond {args.maxIterations} itérations."
    )
    print(f"Outils : {registry.names()}")
    print(f"Sensibles : {registry.sensitiveNames()} — validation : {mode}")
    print()

    try:
        trace = runAgent(
            client=OpenAICompatibleClient(
                baseUrl=config.baseUrl, model=config.model, apiKey=config.apiKey
            ),
            registry=registry,
            approval=approval,
            systemPrompt=systemPrompt,
            task=args.tache,
            maxIterations=args.maxIterations,
        )
    except ModelCallError as error:
        print(f"Appel modèle : {error}", file=sys.stderr)
        return 1

    print(trace.finalText)
    print()
    print(summarizeTrace(trace))
    print(f"latence : {trace.latencySeconds:.1f} s")

    if trace.stoppedReason == STOP_ITERATION_LIMIT:
        print()
        print("ATTENTION : plafond d'itérations atteint, la réponse est tronquée.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
