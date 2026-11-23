"""Fabrique, à partir du corrigé du jeu, la sortie qu'un agent parfait rendrait.

Chaque valeur est recopiée telle qu'écrite dans le PV, avec pour citation la
ligne du PV qui la contient. Sert à vérifier que le corrigé passe sa propre
notation et que le code retrouve les incohérences déclarées.
"""

import json
from pathlib import Path

from agent.dividends import NOT_GIVEN

REPO_ROOT = Path(__file__).resolve().parents[1]
DIVIDEND_SET = REPO_ROOT / "evaluations" / "jeux" / "taches_dividendes.jsonl"
DIVIDEND_DOCUMENTS = REPO_ROOT / "evaluations" / "jeux" / "pv_dividendes.jsonl"


def loadRecords() -> list[dict[str, object]]:
    """Les cas du jeu, tels qu'écrits dans le JSONL."""
    with DIVIDEND_SET.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _quote(expected: object, document: str) -> object:
    if expected == NOT_GIVEN:
        return NOT_GIVEN
    assert isinstance(expected, dict)
    text = expected["texte"]
    line = next(line for line in document.splitlines() if text in line)
    return {"valeur": text, "citation": line}


def perfectOutput(record: dict[str, object], document: str) -> str:
    """La sortie JSON d'un agent parfait pour ce cas du jeu."""
    expected = record["attendu"]
    assert isinstance(expected, dict)
    output: dict[str, object] = {
        "distribution": expected["distribution"],
        "montant_total": _quote(expected["montant_total"], document),
        "montant_par_part": _quote(expected["montant_par_part"], document),
        "date_mise_en_paiement": _quote(expected["date_mise_en_paiement"], document),
        "associes": [
            {
                "nom": partner["nom"],
                "nombre_parts": _quote(partner["nombre_parts"], document),
                "montant": _quote(partner["montant"], document),
            }
            for partner in expected["associes"]
        ],
        "acompte_hors_ag": None,
        "solde": None,
        "remarques": list(record.get("mots_cles_attendus", [])),
    }
    if interim := expected["acompte_hors_ag"]:
        output["acompte_hors_ag"] = {
            key: _quote(value, document) for key, value in interim.items()
        }
    if balance := expected["solde"]:
        output["solde"] = {
            key: _quote(value, document) for key, value in balance.items()
        }
    return json.dumps(output, ensure_ascii=False, indent=2)
