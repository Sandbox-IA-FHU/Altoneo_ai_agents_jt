"""Ce que le code fait de l'extraction rendue par l'agent.

L'agent rend un objet JSON unique, qui recopie le PV, chaque valeur avec le
passage qui la justifie :

    {
      "distribution": "oui" | "non",
      "montant_total": {"valeur": "…", "citation": "…"} | "non indiqué",
      "montant_par_part": … ,
      "date_mise_en_paiement": … ,
      "associes": [{"nom": "…", "nombre_parts": … , "montant": … }],
      "acompte_hors_ag": null | {"montant": … , "montant_par_part": … ,
                                 "date": … },
      "solde": null | {"montant": … , "montant_par_part": … },
      "remarques": ["…"]
    }

Une clôture Markdown (```json … ```) autour de l'objet est tolérée ; tout
autre texte autour le rend illisible. Une sortie illisible n'est jamais
réparée : elle ne peut pas être vérifiée.

Tout ce qui est calcul est fait ici, jamais par le modèle : montant de chaque
associé, incohérences (somme, montant d'un associé, solde après acompte) et
échéance de la déclaration 2777, une par paiement. Ces résultats sont à
valider par un collaborateur avant tout usage.
"""

import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from agent.amounts import parseAmount, parseDate
from agent.errors import UnreadableExtractionError

NOT_GIVEN = "non indiqué"
INCOHERENCE_TOTAL = "somme"
INCOHERENCE_PARTNER = "associe"
INCOHERENCE_BALANCE = "solde"

_FENCE = re.compile(r"^```(?:json)?\s*\n(.*)\n```$", re.DOTALL)
_REQUIRED = (
    "distribution",
    "montant_total",
    "montant_par_part",
    "date_mise_en_paiement",
    "associes",
)


@dataclass(frozen=True)
class Quoted:
    """Une valeur recopiée du PV, avec le passage qui la justifie."""

    text: str
    citation: str


@dataclass(frozen=True)
class Partner:
    name: str
    parts: Quoted | None
    amount: Quoted | None


@dataclass(frozen=True)
class Interim:
    """Un acompte sur dividendes décidé hors AG."""

    amount: Quoted | None
    perPart: Quoted | None
    paidOn: Quoted | None


@dataclass(frozen=True)
class Balance:
    """Le solde à verser après un acompte, s'il est écrit."""

    amount: Quoted | None
    perPart: Quoted | None


@dataclass(frozen=True)
class Extraction:
    """L'extraction rendue par l'agent. `None` dans un champ : « non indiqué »."""

    distribution: bool
    total: Quoted | None
    perPart: Quoted | None
    paidOn: Quoted | None
    partners: tuple[Partner, ...]
    interim: Interim | None
    balance: Balance | None
    remarks: tuple[str, ...]


@dataclass(frozen=True)
class Deadline:
    """Une échéance 2777 calculée par le code, à valider."""

    payment: str
    paidOn: date
    due: date


def _quoted(value: object) -> Quoted | None:
    if isinstance(value, str) and value.strip().lower() == NOT_GIVEN:
        return None
    if not isinstance(value, dict):
        raise UnreadableExtractionError(
            "valeur ni « non indiqué » ni {valeur, citation}"
        )
    text, citation = value.get("valeur"), value.get("citation")
    if isinstance(text, int | float) and not isinstance(text, bool):
        text = str(text)
    if not isinstance(text, str) or not isinstance(citation, str):
        raise UnreadableExtractionError("valeur ou citation absente")
    return Quoted(text=text, citation=citation)


def _optional(record: dict[str, object], key: str) -> Quoted | None:
    return _quoted(record[key]) if key in record else None


def _parse(record: object) -> Extraction:
    if not isinstance(record, dict):
        raise UnreadableExtractionError("la sortie n'est pas un objet JSON")
    missing = [key for key in _REQUIRED if key not in record]
    if missing:
        raise UnreadableExtractionError(f"champs manquants : {missing}")
    if record["distribution"] not in ("oui", "non"):
        raise UnreadableExtractionError("distribution ni « oui » ni « non »")
    if not isinstance(record["associes"], list):
        raise UnreadableExtractionError("associes n'est pas une liste")

    partners = []
    for partner in record["associes"]:
        if not isinstance(partner, dict) or not isinstance(partner.get("nom"), str):
            raise UnreadableExtractionError("associé sans nom")
        partners.append(
            Partner(
                name=partner["nom"],
                parts=_optional(partner, "nombre_parts"),
                amount=_optional(partner, "montant"),
            )
        )

    interim = record.get("acompte_hors_ag")
    balance = record.get("solde")
    for block in (interim, balance):
        if block is not None and not isinstance(block, dict):
            raise UnreadableExtractionError("acompte ou solde ni null ni objet")
    remarks = record.get("remarques", [])
    if not isinstance(remarks, list) or not all(isinstance(r, str) for r in remarks):
        raise UnreadableExtractionError("remarques n'est pas une liste de textes")

    return Extraction(
        distribution=record["distribution"] == "oui",
        total=_quoted(record["montant_total"]),
        perPart=_quoted(record["montant_par_part"]),
        paidOn=_quoted(record["date_mise_en_paiement"]),
        partners=tuple(partners),
        interim=(
            Interim(
                amount=_optional(interim, "montant"),
                perPart=_optional(interim, "montant_par_part"),
                paidOn=_optional(interim, "date"),
            )
            if interim
            else None
        ),
        balance=(
            Balance(
                amount=_optional(balance, "montant"),
                perPart=_optional(balance, "montant_par_part"),
            )
            if balance
            else None
        ),
        remarks=tuple(remarks),
    )


def readExtraction(output: str) -> Extraction | None:
    """Lit la sortie de l'agent. `None` si elle ne suit pas le format."""
    text = output.strip()
    if fenced := _FENCE.match(text):
        text = fenced.group(1).strip()
    try:
        return _parse(json.loads(text))
    except (json.JSONDecodeError, UnreadableExtractionError):
        return None


def amountOf(value: Quoted | None) -> Decimal | None:
    return parseAmount(value.text) if value else None


def partnerAmounts(extraction: Extraction) -> dict[str, Decimal | None]:
    """Montant de chaque associé : nombre de parts × montant par part.

    `None` pour un associé dont le nombre de parts n'est pas écrit.
    """
    perPart = amountOf(extraction.perPart)
    amounts: dict[str, Decimal | None] = {}
    for partner in extraction.partners:
        parts = amountOf(partner.parts)
        amounts[partner.name] = parts * perPart if parts and perPart else None
    return amounts


def incoherences(extraction: Extraction) -> set[str]:
    """Les écarts entre les montants recopiés, calculés par le code.

    Le contrôle de la somme ne conclut que si la répartition des parts est
    écrite pour tous les associés.
    """
    found: set[str] = set()
    total, perPart = amountOf(extraction.total), amountOf(extraction.perPart)

    parts = [amountOf(partner.parts) for partner in extraction.partners]
    allParts = bool(parts) and all(parts)
    if total and perPart and allParts and sum(p for p in parts if p) * perPart != total:
        found.add(INCOHERENCE_TOTAL)

    computed = partnerAmounts(extraction)
    for partner in extraction.partners:
        written = amountOf(partner.amount)
        expected = computed[partner.name]
        if written is not None and expected is not None and written != expected:
            found.add(INCOHERENCE_PARTNER)

    if extraction.interim and extraction.balance:
        interim = amountOf(extraction.interim.amount)
        balance = amountOf(extraction.balance.amount)
        if total and interim and balance and total - interim != balance:
            found.add(INCOHERENCE_BALANCE)
    return found


def deadline2777(paidOn: date) -> date:
    """Échéance de la déclaration 2777 : le 15 du mois suivant la mise en paiement.

    Règle donnée par le métier, à valider par un collaborateur.
    """
    if paidOn.month == 12:
        return date(paidOn.year + 1, 1, 15)
    return date(paidOn.year, paidOn.month + 1, 15)


def deadlines2777(extraction: Extraction) -> list[Deadline]:
    """Une échéance par paiement dont la date est écrite : acompte, puis solde.

    Point ouvert, à faire confirmer : une échéance par paiement plutôt qu'une
    seule pour le dividende.
    """
    payments = []
    if extraction.interim and extraction.interim.paidOn:
        payments.append(("acompte", extraction.interim.paidOn))
    if extraction.paidOn:
        label = "solde" if extraction.interim else "dividende"
        payments.append((label, extraction.paidOn))

    deadlines = []
    for label, quoted in payments:
        paidOn = parseDate(quoted.text)
        if paidOn is not None:
            deadlines.append(Deadline(label, paidOn, deadline2777(paidOn)))
    return deadlines


def describeChecks(extraction: Extraction | None) -> list[str]:
    """Ce que le code a calculé, en lignes lisibles, toutes à valider.

    Aucune ligne ne vient du modèle : montants par associé, incohérences et
    échéances 2777 sont calculés ici à partir des valeurs recopiées.
    """
    if extraction is None:
        return ["Sortie hors format : rien n'est calculé, rien n'est vérifiable."]
    lines = ["Calculé par le code, à valider par un collaborateur :"]
    for name, amount in partnerAmounts(extraction).items():
        shown = f"{amount} euros" if amount is not None else "répartition non écrite"
        lines.append(f"  montant de {name} : {shown}")
    labels = {
        INCOHERENCE_TOTAL: "le total diffère du montant par part × le nombre de parts",
        INCOHERENCE_PARTNER: "un montant écrit pour un associé diffère de son calcul",
        INCOHERENCE_BALANCE: "le solde écrit diffère du dividende moins l'acompte",
    }
    found = incoherences(extraction)
    lines += [f"  INCOHÉRENCE : {labels[key]}" for key in sorted(found)]
    if not found:
        lines.append("  aucune incohérence trouvée")
    deadlines = deadlines2777(extraction)
    lines += [
        f"  échéance 2777 ({d.payment}, payé le {d.paidOn.isoformat()}) : "
        f"{d.due.isoformat()}"
        for d in deadlines
    ]
    if not deadlines:
        lines.append("  échéance 2777 : aucune date de mise en paiement écrite")
    return lines
