# agent-dividendes — consignes Claude Code

Les règles communes de l'organisation (`CLAUDE.md` du dépôt `.github`)
s'appliquent : français, aucune donnée réelle, aucune clé, aucun nom de
client, `uv` uniquement, chiffres datés. Ce fichier les complète pour ce
dépôt. Les conventions d'écriture Python sont dans
[CONVENTIONS-PYTHON.md](CONVENTIONS-PYTHON.md) — à lire avant toute
modification de code.

**Ce dépôt est public.** Tout ce que tu écris dans un fichier, un commit, une
branche ou une PR est lisible par n'importe qui, pour toujours. Aucune donnée
réelle, aucune clé, aucun nom de client, aucune adresse ni nom de serveur.

## Horaires du serveur de staging : à vérifier AVANT chaque tâche

Ne s'applique que si la session tourne **sur le serveur de staging**.

Le serveur est allumé **en continu du lundi 7h00 au vendredi 20h00**. Ces
horaires sont **provisoires** : Florian (responsable) communique tout
changement. À 20h00 le vendredi, il s'arrête d'un coup : une commande en
cours est tuée, et ce qui n'est pas poussé reste inaccessible jusqu'au lundi
7h00.

Avant toute tâche (commandes, build d'image, tests, évaluation, série de
modifications), et de nouveau avant chaque étape longue :

1. Lancer `date` pour connaître le jour et l'heure réels (heure de Paris).
   Ne jamais se fier à une heure supposée.
2. Estimer la durée de la tâche entière, **commit et push compris**, en
   prenant l'estimation haute.
3. Comparer l'heure de fin estimée à la prochaine coupure, le vendredi
   20h00 :
   - **fin avant vendredi 19h30** : on y va, sans prévenir. Du lundi au
     jeudi, c'est le cas de toute tâche normale ;
   - **fin entre vendredi 19h30 et 19h50** : ne rien lancer. Donner l'heure,
     la durée estimée et la fin prévue, et demander s'il faut y aller ou
     attendre lundi ;
   - **fin après vendredi 19h50** : bloquer, sans rien lancer. Expliquer
     pourquoi et proposer de reprendre lundi.

Jamais de tâche en arrière-plan qui finirait après vendredi 19h50. Si une
tâche est reportée, commiter et pousser d'abord ce qui est stable. Le
vendredi, tout ce qui est stable est poussé avant de s'arrêter. Jour férié ou
horaire inhabituel : demander avant de supposer que le serveur est allumé.

## Le serveur : ce qui est permis

- Pas de `sudo`, pas d'accès au Docker du serveur : on utilise **son propre
  Docker rootless**. Tout tourne en conteneur, rien ne s'installe au niveau du
  système (`uv` n'y est pas : passer par `docker compose run`).
- **Jamais d'accès direct au GPU**, jamais de bibliothèque de modèle locale
  (PyTorch, transformers…) pour contourner l'API. L'agent appelle le LLM, point.
- Ne pas toucher aux conteneurs des autres.
- **Le dépôt de production est hors d'atteinte** : pas d'accès, pas de
  tentative d'accès. L'import est fait par Florian.

## Périmètre et Git

- Le dépôt est créé par Florian, qui y pose les protections et crée
  `staging`. Tu ne crées pas de dépôt et tu ne touches ni aux réglages ni aux
  protections du dépôt (rôle Write).
- Travail sur la branche **`staging`** : commits et push directs, jamais de
  force-push, jamais de suppression de branche.
- Projet à deux : chacun sur sa branche personnelle, mise à jour par
  `git rebase origin/staging` avant d'être intégrée dans `staging` (voir le
  README, « Projet à deux »).
- `main` ne reçoit que des PR `staging` → `main`, **approuvées et fusionnées
  par Florian**, en merge commit. Ne jamais fusionner toi-même.
- Pousser au fil de l'eau, et toujours avant de s'arrêter un vendredi.
- Commits en français, à l'impératif, sans préfixe.

## Le projet

**agent-dividendes.** Question : un agent sur le LLM local peut-il extraire
d'un PV d'assemblée générale d'approbation des comptes la décision de
distribution, le montant total, les montants par associé et la date de mise
en paiement, chacun avec le passage cité, sans jamais écrire un montant, un
associé ou une date absents du PV ?

- **Pour qui** : les collaborateurs qui suivent les dossiers récurrents
  d'approbation des comptes. Ils valident tout avant usage.
- **Ce qui est livré** : une extraction, relue par un collaborateur. L'agent
  ne crée rien, n'envoie rien, n'écrit rien.
- **Partage du travail entre le modèle et le code** :
  - le modèle **recopie** ce que le PV écrit, chaque valeur avec le passage
    qui la justifie : distribution oui ou non, montant total, montant par
    part et nombre de parts (ou montant par associé s'il est écrit), date de
    mise en paiement, et un acompte décidé hors AG **à part** ;
    « non indiqué » quand le PV ne donne pas la valeur ;
  - le **code** fait tout ce qui est calcul ou vérification : normaliser les
    montants (espaces, virgule, `€`/`EUR`, montants en lettres) et les
    comparer comme des nombres, multiplier montant par part et nombre de
    parts, signaler un total différent de la somme, vérifier qu'un solde
    écrit après acompte égale le dividende moins l'acompte, vérifier que
    chaque citation figure dans le PV (mot pour mot), calculer l'échéance de
    la déclaration 2777 (le 15 du mois suivant la mise en paiement), une par
    paiement : l'acompte et le solde.
- **L'échéance 2777 n'est jamais écrite par le modèle.** La règle est prise
  telle que donnée par le métier et testée comme du code ; sa justesse
  fiscale se valide auprès d'un collaborateur, pas par le jeu. **Point
  ouvert, à faire confirmer par le pôle** : une échéance 2777 par paiement
  (acompte et solde), plutôt qu'une seule pour le dividende.
- **Outil** : `readDocument`, en lecture seule, non sensible. **Aucun outil
  sensible** : l'agent ne peut pas créer d'échéance, quelle que soit la
  consigne lue — c'est l'outillage qui le garantit, pas le prompt. Si un jour
  on en ajoute un, il est `isSensitive=True` et il entre dans
  `outils_interdits` des cas `refus`.
- **Inventer un montant, un associé ou une date** est traité comme l'outil
  interdit : éliminatoire, sur les 30 cas (seuil du README). Une valeur dont
  la citation est introuvable dans le PV ne compte pas : elle est
  invérifiable.
- **Jeu de réserve** (`evaluations/jeux/reserve_*.jsonl`) : 15 PV écrits par
  un sous-agent isolé, pour mesurer le prompt hors des cas qui ont servi à
  l'écrire. **Il ne sert jamais à écrire ou retoucher un prompt** : ne le lis
  pas pour ça, ni ses sorties détaillées. **Le prompt v2 devra être écrit par
  une session qui n'a jamais lu le jeu de réserve** — la session du
  2026-11-23 l'a lu en l'intégrant.
- **Données** : PV **entièrement inventés** — raisons sociales visiblement
  fictives, montants et nombres de parts sans ressemblance avec de vrais
  clients. Un vrai PV n'entre jamais dans le dépôt. Le prompt ne reprend
  aucune expression du jeu (vérifié par `grep`).

Le code reste volontairement minuscule. Une modification qui rend l'agent
plus capable mais moins lisible est une régression.

## Contraintes techniques

- LLM local, API compatible OpenAI. Adresse dans `LLM_BASE_URL` (fournie par
  Florian), jamais en dur. Nom exposé stable : `LLM_MODEL=altoneo-llm`.
- Révision du modèle dans `LLM_MODEL_REVISION`, jamais dans le dépôt :
  obligatoire pour une évaluation.
- Appels d'outils au format `tools` / `tool_calls`. S'ils sont refusés par le
  serveur, le signaler à Florian ; **ne jamais** les remplacer par une analyse
  du texte libre.
- Réflexion : `REASONING_EFFORT = "low"` dans `client.py`. Elle n'entre
  jamais dans la trace, son résumé ou un fichier commité (`test_client.py`).
  Par défaut, elle ne repart pas dans l'historique
  (`KEEP_REASONING_IN_HISTORY = False`) ; l'activer est une mesure à faire,
  pas un réglage à changer sans run.
- `compose.yaml` : service préfixé par le projet, `TZ: Europe/Paris`, image
  figée par tag et empreinte, pas de GPU, pas de port, utilisateur réglé par
  `AGENT_UID` / `AGENT_GID`.

## Où en est-on

- 2026-10-23 — modèle branché sur le LLM local (client compatible OpenAI),
  voie conteneur ajoutée. Réflexion `low` par défaut (décidé le 22/10 sur
  comparatif).
- 2026-10-27 au 2026-10-30 — ce dépôt a porté un agent de synthèse de
  comptes rendus, arrêté le 2026-10-30. Tout est au tag `synthese-arretee`
  (voir le README). Leçon reprise ici : deux runs identiques ont différé de
  trois cas, une configuration se mesure sur au moins deux runs.
- 2026-11-23 — projet renommé `agent-dividendes`. Cadrage validé : question
  et seuil dans le README. Jeu de 30 PV inventés écrit
  (`scripts/generate_dividend_set.py`). Code hors modèle et notation par
  champ écrits ; le corrigé passe sa propre notation sur les 30 cas. Prompt
  v1 écrit (`prompts/agent_v1.md`) et description de `readDocument`
  adaptée, avant tout run.
- 2026-11-23 — deux runs de référence, prompt v1
  (`evaluations/runs/2026-11-23-v1-reference.json`, `-reference-2.json`) :
  30/30 puis 29/30, 0 invention, 0 outil interdit, 0 plafond, 2 tours par
  cas, environ 4 950 jetons par tâche. **Le prompt v1 tient le seuil.** Seul
  échec : d-28 au second run, JSON invalide (virgule de trop), contenu juste.
  Réserves du README : troncature non testée, pas de jeu de réserve, jeu au
  plafond.
- 2026-11-23 — jeu de réserve de 15 PV ajouté (4 `nominal`, 6 `difficile`,
  5 `refus`), écrit par un sous-agent isolé ; seuil écrit avant toute
  mesure : au moins 13/15, autres critères inchangés, sur deux runs. Notation
  désormais contre la partie lue du PV, remarques contrôlées. Aucun run sur
  la réserve.
- 2026-11-23 — deux runs du prompt v1 sur la réserve
  (`evaluations/runs/2026-11-23-v1-reserve.json`, `-reserve-2.json`) :
  12/15 puis 12/15, 0 puis 1 cas d'invention : **le seuil de la réserve ne
  tient pas tel que mesuré.** Deux défauts de mesure trouvés en relisant les
  sorties, corrigés le jour même : la boucle recoupait tout résultat d'outil
  à 4 000 caractères sans le dire (l'agent lisait la moitié des PV longs) ;
  le contrôle des remarques ne voyait pas les montants en « € ». Tous les
  runs commités ont été faits avec la lecture à 4 000 caractères ; ils ne
  sont pas re-notés, les nouveaux runs feront foi. Seul vrai défaut de
  comportement observé : un calcul écrit dans les remarques, plus un écart
  de format (« non indiqué » placé dans l'objet valeur/citation).
- 2026-11-23 — mesures refaites avec la lecture corrigée (commit `e0ba239`,
  notation `c38bec6`), deux runs par jeu
  (`evaluations/runs/2026-11-23-v1-lecture-*.json`). **Jeu principal : le
  seuil tient** — 29/30 et 29/30, 30/30 et 30/30 après correction du corrigé
  de d-08 (associé unique), re-noté hors LLM par
  `scripts/regrade_details.py` ; 0 invention. Nouvelle référence de charge :
  4 986 jetons par tâche, 2 tours médians. **Jeu de réserve : le seuil ne
  tient pas** — 14/15 avec une invention, puis 15/15. Catégorie du défaut,
  récurrent (trois runs de la réserve sur quatre) : un calcul écrit dans les
  remarques. Le détail des sorties est gardé hors du dépôt
  (`scripts/evaluate_detail.py`).

## À travailler

Dans cet ordre :

1. ~~**Le jeu**~~ : écrit le 2026-11-23, 30 PV inventés, voir
   `evaluations/jeux/LISEZ-MOI.md`. Le PV long (d-21) dépasse
   `MAX_DOCUMENT_CHARS`, mais toutes ses valeurs sont avant la coupure : un
   cas dont une valeur serait au-delà attendra la lecture par sections.
2. ~~**La sortie et la notation**~~ (fait le 2026-11-23) : sortie JSON,
   notation champ par champ qui sépare les inventions des échecs et vérifie
   les citations, montants normalisés et comparés comme des nombres. Dans le
   code, hors du modèle : multiplication par part, contrôle de la somme et
   du solde après acompte, échéance 2777 par paiement, avec leurs tests.
   `invention_detectee`, `cas_avec_invention` et `format_non_conforme`
   reviennent dans le fichier de run.
3. ~~**Le prompt v1**~~ (fait le 2026-11-23), sans aucune suite de quatre
   mots commune avec le jeu (`tests/test_prompt.py`, qui contrôle aussi la
   description de `readDocument`).
4. ~~**Deux runs de référence**~~ (faits le 2026-11-23) : le prompt v1 tient
   le seuil, voir « Où en est-on » et le README.
5. ~~**Refaire les mesures du prompt v1 avec la lecture corrigée**~~ (fait
   le 2026-11-23) : voir « Où en est-on » et le README.
6. **Le prompt v2**, pour deux défauts, décrits ici par catégorie seulement :
   l'agent écrit parfois un calcul dans les remarques (le code signale déjà
   les incohérences) ; il écrit parfois « non indiqué » comme objet
   valeur/citation au lieu d'une chaîne. **Il sera écrit par une nouvelle
   session qui n'a jamais lu le jeu de réserve**, ni ses sorties, ni ses
   fichiers de détail ; la session du 2026-11-23 l'a lu. Mesure : deux runs
   par jeu, comparés aux deux seuils et aux runs à lecture corrigée.
   Point à surveiller aussi : un cas du jeu principal a lu deux fois le
   document (3 tours) au lieu d'une.
7. **L'appel unique sans outil** (PV dans le prompt), comparé à la boucle sur
   deux runs. S'il fait aussi bien, c'est lui qu'on garde. Attention : le jeu
   est au plafond (30/30, 29/30), la comparaison ne peut montrer qu'une
   dégradation ; un écart d'un cas reste dans le bruit.

Et par ailleurs :

- Les réserves des runs de référence, à traiter avant de conclure plus loin :
  un **jeu de réserve**, écrit sans regarder le prompt, pour mesurer hors des
  cas qui ont servi à l'écrire ; un **cas dont une valeur est après la
  coupure** de `MAX_DOCUMENT_CHARS`, pour tester la troncature ; des cas plus
  difficiles pour sortir du plafond. Le contrôle d'invention dans les
  `remarques` (dates et montants en euros) et la notation contre la partie
  lue du PV sont faits ; les deux références, re-notées, ne changent pas.
- Le format : une virgule de trop a suffi à faire échouer d-28. Mesurer la
  sortie structurée imposée par le serveur, sur deux runs. Ne pas rendre
  `readExtraction` tolérant sans nouveau run : ce serait changer la mesure.

- Mettre à jour `.claude/commands/` (`outil.md`, `evaluer.md`,
  `avant-pr.md`), qui parlent encore du jeu de synthèse ; `prompt.md` est à
  jour.
- Comparer la réflexion `off` et `low` : deux runs qui ne diffèrent que par
  `--reflexion`. Garder `low` sauf si `off` fait au moins aussi bien sur la
  réussite **et** sur `outil_interdit_appele` (qui doit rester à 0).
- Mesurer `--garder-reflexion` : deux runs qui ne diffèrent que par ce
  paramètre, comparés sur `tache_reussie`, `etapes_medianes` et
  `outil_interdit_appele` (qui doit rester à 0). Voir le README.
- Hors périmètre de la mesure : la conversion d'un PDF en texte. L'agent lit
  du texte.
- Piste v2 : un champ « nombre total de parts », recopié du capital, pour que
  le contrôle de la somme conclue aussi quand la répartition des parts n'est
  pas écrite (aujourd'hui, il ne conclut pas : d-23, d-27).
- Les centimes écrits en lettres ne sont pas lus : une telle valeur est
  illisible, donc un échec, jamais une invention.

---

## Commandes

Sur un poste :

```bash
uv sync                      # installation
uv run ruff format .         # formatage
uv run ruff check .          # lint
uv run pytest                # tests, sans réseau ni serveur
uv run --env-file .env python scripts/run_agent.py "une tâche"
uv run --env-file .env python scripts/evaluate.py --limite 3
```

Sur le serveur (rootless) ou après import :

```bash
docker compose run --rm agent-dividendes pytest
docker compose run --rm agent-dividendes ruff check .
docker compose run --rm agent-dividendes python scripts/evaluate.py --limite 3
```

Aucun test n'appelle le LLM. Les scénarios d'agent sont rejoués par
`ScriptedClient` dans `tests/conftest.py` : une liste de réponses préparées au
format OpenAI, rendues dans l'ordre et lues par le même analyseur que le vrai
client. C'est ce qui permet de tester des boucles entières — plafond atteint,
action refusée, outil en erreur — hors ligne.

## Architecture, en une phrase par module

| Module | Rôle |
|---|---|
| `models.py` | Structures, dont `Trace` — ce qu'on relit et ce qu'on mesure. |
| `config.py` | Seul endroit qui lit `os.environ`. Valide et échoue au démarrage. |
| `client.py` | Seul module qui connaît le SDK. Protocole `AgentClient`. Écarte la réflexion. |
| `tools.py` | Registre : le schéma envoyé au modèle et la fonction exécutée viennent du même objet. |
| `toolbox.py` | `readDocument`, l'unique outil, en lecture seule, et le magasin de documents (les PV). |
| `approval.py` | Politiques de validation. Défaut : refus. |
| `loop.py` | `runAgent` — la boucle, plafonnée. |
| `amounts.py` | Lit montants et dates comme des nombres et des dates ; rien d'ambigu n'est deviné. |
| `dividends.py` | Lit la sortie JSON de l'agent ; calcule hors modèle montants par associé, incohérences et échéances 2777. |
| `grading.py` | Note une extraction champ par champ : inventions, échecs, citations. |
| `evaluation.py` | Agrégation : réussite, outils interdits, inventions, format, plafond, tours, jetons, latence. |

## Les quatre choses à ne pas casser

**1. Le plafond d'itérations.** `MAX_ITERATIONS` dans `loop.py`, en dur, en
majuscules. Il ne devient jamais un paramètre sans valeur par défaut, il ne
disparaît pas, et l'atteindre reste visible dans la trace. Tests :
`test_iterationLimitStopsTheLoop`, `test_iterationLimitIsNotSilent`.

**2. Le passage obligatoire par la validation.** Tout outil `isSensitive`
traverse `approval.approve` dans `executeCall`. Aucun chemin de contournement,
quelle que soit la justification écrite par le modèle. Test :
`test_sensitiveToolNeedsApproval`. L'agent n'a aucun outil sensible : le test
utilise `sendDraft`, un outil fictif défini dans `tests/conftest.py`.

**3. `eval` n'entre jamais dans ce dépôt.** Aucun outil n'interprète du texte
comme du code. Du code produit par un modèle est du code plausible, pas du
code sûr. Test : `test_evalNeverEntersTheCode`, qui cherche `eval(` et
`exec(` dans `src/` et `scripts/`.

**4. Le contenu d'outil reste de la donnée.** On ne filtre pas les résultats
d'outils, on ne prétend pas détecter une injection : on limite la surface
d'outils. Au moins deux PV du jeu et un document de `tests/conftest.py`
contiennent une consigne adressée à l'assistant : ils doivent y rester.

---

## La charge d'un agent n'est pas linéaire

C'est le point le plus mal anticipé sur ce type de projet, et c'est de
l'arithmétique, pas une opinion.

L'API est **sans état** : à chaque tour, la boucle renvoie tout l'historique.
Si `B` est la partie fixe (prompt système + schémas d'outils + tâche) et `C` ce
qu'un tour ajoute (réponse du modèle + résultats d'outils), le total de jetons
d'entrée sur `N` tours vaut :

```
N × B  +  C × N(N−1)/2
```

Pour `N = 8` : la partie fixe est envoyée **8 fois**, et le terme variable
vaut **28 fois** le contenu d'un tour, pas 8. Un agent qui met six tours au
lieu de deux ne consomme pas trois fois plus : il consomme nettement plus.

Le LLM tourne sur un GPU déjà payé : il n'y a pas de facture à l'appel. Mais
il est **partagé** entre plusieurs projets, et chaque jeton qu'un agent lui
fait traiter est du temps pris aux autres. Trois conséquences pratiques :

- **Le nombre de tours est une métrique de premier ordre**, pas une
  curiosité. `etapes_medianes`, `etapes_max` et `jetons_par_tache` sont dans
  le fichier de run pour ça. Faire passer la médiane de 4 à 3 vaut souvent
  mieux que n'importe quelle optimisation de prompt.
- **Faire regrouper les appels d'outils indépendants** est le gain le plus
  simple : deux documents lus dans le même tour, c'est un aller-retour au lieu
  de deux. Ici, un cas ne lit qu'un document : le prompt demande un seul
  appel à `readDocument`, puis l'extraction. Si un jour l'agent lit plusieurs
  documents, `test_parallelToolResultsShareOneRoundTrip` vérifie déjà que la
  boucle ne casse pas le regroupement en étalant les résultats sur plusieurs
  tours.
- **La réflexion se paie en jetons de sortie et en latence.** Elle est
  comptée dans `jetons_sortie`. Un niveau plus élevé n'est justifié que par
  une mesure qui montre un gain de réussite.

Ne convertis jamais un nombre de mots en jetons avec un ratio de tête. Le
comptage se lit dans `usage` après un vrai appel, et il est déjà accumulé sur
toute la boucle dans `trace.usage`.

---

## Diagnostiquer un agent qui se comporte mal

« L'agent est bête » n'est pas un diagnostic. Six symptômes distincts, six
causes différentes, et dans quatre cas sur six la correction **n'est pas dans
le prompt**.

Commence toujours par lire la trace : `summarizeTrace(trace)` donne la
séquence d'outils et les compteurs, `trace.steps` donne le détail.

### L'agent redemande le même outil avec les mêmes arguments

C'est le symptôme le plus fréquent, et le prompt n'y est pour rien. Le modèle
boucle parce que le **résultat d'outil ne lui apprend rien** : chaîne vide,
message d'erreur sans indication de correction, format ambigu.

Correction : dans `toolbox.py`, faire que l'outil dise ce qu'il faut faire.
`readDocument` liste les documents disponibles quand le nom est inconnu — c'est
délibéré, et c'est ce qui permet au modèle de se rattraper en un tour au lieu
de réessayer trois fois.

### L'agent appelle le mauvais outil

Problème de **description**, pas de prompt système. Une description qui dit ce
que l'outil fait sans dire quand l'utiliser laisse le modèle deviner.

Relis la description avec cette question : quelqu'un qui ne connaît pas le
projet saurait-il choisir entre cet outil et son voisin ?

### L'agent atteint le plafond

Trois causes à distinguer avant de toucher à `MAX_ITERATIONS` — l'augmenter est
la mauvaise réponse dans deux cas sur trois :

- **Il boucle** — voir plus haut, c'est le résultat d'outil qu'il faut corriger.
- **La tâche demande plus d'étapes que le plafond** — légitime. C'est alors une
  décision explicite, avec la charge recalculée selon la formule ci-dessus, pas
  un chiffre qu'on monte parce que ça bloque.
- **Il explore sans but** — il relit le document ou cherche ailleurs par
  précaution. C'est le prompt, section « Comment tu travailles » : un seul
  appel, puis l'extraction.

### L'agent répond sans appeler d'outil

Il a rédigé sans lire le document. Ici, il n'y a pas de question générale :
une extraction écrite sans appel à `readDocument` est inventée de bout en bout,
même s'il a l'air plausible. À traiter comme un échec, jamais comme une
réussite rapide.

### L'agent obéit à ce qu'il a lu

Injection réussie. La réaction correcte **n'est pas** d'ajouter une
interdiction au prompt : c'est de regarder ce que l'agent a pu faire à cause
d'elle. Si la réponse est « rien de grave, la validation a bloqué », le
dispositif a fonctionné comme prévu. Si la réponse est « il aurait pu faire X »,
c'est X qu'il faut retirer ou marquer sensible.

Le prompt réduit la fréquence ; il ne borne pas les dégâts. Seule la surface
d'outils les borne.

### L'agent réessaie après un refus de validation

C'est le prompt, et c'est un vrai problème de charge : chaque nouvelle
tentative est un tour complet. `REFUSAL_MESSAGE` dans `approval.py` le lui dit
déjà — si le comportement persiste, c'est là qu'il faut renforcer, pas
ailleurs.

---

## La description d'un outil fait partie du prompt

Point systématiquement oublié en revue.

Le schéma de chaque outil, description comprise, part vers le LLM à **chaque
tour**, au même titre que le prompt système. Trois conséquences :

1. **Modifier une description invalide les runs passés**, exactement comme
   modifier le prompt. Il faut un nouveau run de référence, et le dire.
2. Une description bavarde est envoyée à chaque tour de chaque tâche. La
   formule de charge plus haut s'applique aussi à elle.
3. Une description est le bon endroit pour dire qu'une action est irréversible
   et soumise à validation — le modèle peut alors en tenir compte **avant** de
   demander l'action, pas seulement après un refus. C'est ce que vérifie
   `test_sensitiveToolDescriptionWarnsTheModel`.

## Ce qui se règle par le prompt, et ce qui ne s'y règle pas

| Objectif | Prompt | Code |
|---|---|---|
| Que l'agent soit plus concis | oui | — |
| Qu'il regroupe ses appels | oui | — |
| Qu'il cesse de réessayer après un refus | oui | — |
| Qu'il n'obéisse pas à une consigne cachée dans un document | réduit la fréquence | **ne garantit rien** |
| Qu'aucune action irréversible n'ait lieu sans accord | non | `isSensitive` + `approval` |
| Que la charge du serveur soit bornée | non | `MAX_ITERATIONS` |
| Qu'aucun code arbitraire ne s'exécute | non | aucun outil n'interprète de code |

La ligne à retenir : **une garantie qui repose sur une phrase de prompt n'en
est pas une.** Si on te demande d'empêcher un comportement dangereux en
ajoutant une interdiction au prompt, pose d'abord la question de l'outil
correspondant.

## Si on te demande d'ajouter un outil

Trois questions, dans cet ordre, avant d'écrire la ligne :

1. **Est-il sensible ?** Irréversible, coûteux, ou visible à l'extérieur
   (envoi, publication, suppression, écriture, paiement) → `isSensitive=True`.
   Dans le doute, oui : le coût d'une validation inutile est une question posée
   à un humain ; le coût d'une action irréversible non validée est un incident.
2. **Que peut-il faire si un contenu récupéré le déclenche ?** C'est la bonne
   façon de raisonner sur l'injection : pas « le prompt tiendra-t-il » mais
   « que se passe-t-il s'il ne tient pas ».
3. **Sa description dit-elle quand l'utiliser, et pas seulement ce qu'il
   fait ?**

Un outil ajouté demande deux cas dans le jeu d'évaluation : un où il **doit**
être appelé, un où il ne doit **pas** l'être. Sans le second, on ne mesure que
la capacité, jamais la retenue. Voir `/outil`.

## Lire un fichier de run

Dans cet ordre, et les deux premiers sont éliminatoires :

1. `outil_interdit_appele` — doit être à **0**. Un agent qui tente une action
   interdite une fois sur vingt la tentera en production. Si ce n'est pas 0, le
   reste du run n'a pas d'intérêt.
2. `invention_detectee` et `cas_avec_invention` — doivent être à **0** : un
   montant, un associé ou une date absents du PV, une date de paiement
   déduite, une échéance 2777 écrite par le modèle. C'est la question du
   projet. Le détail se relit cas par cas, il n'est jamais écrit dans le run.
3. `limite_iterations_atteinte` — ces cas ne sont ni réussis ni ratés, ils sont
   ininterprétables. Beaucoup de plafonds atteints = le score de réussite porte
   sur moins de cas qu'annoncé. `format_non_conforme` aussi : une sortie
   JSON illisible ne peut pas être vérifiée.
4. `tache_reussie`, **et son découpage par type**. Des échecs concentrés sur
   les cas de refus décrivent un système dangereux affiché comme correct.
5. `etapes_medianes` / `etapes_max` / `jetons_par_tache` — la charge, et le
   meilleur gisement d'économies.
6. Latence médiane et p95, et le bloc `modele` : nom exposé, modèle réel,
   révision. Deux runs ne se comparent que si ce bloc, la `reflexion` et
   `garder_reflexion` sont identiques (sauf si c'est justement le paramètre étudié).

## Ce qu'on attend d'une session ici

**Avant de coder, cadrer.** Quelle question, quelle mesure, quel seuil. La
commande `/cadrer` sert à ça.

**Diagnostiquer avant de corriger.** Lire la trace d'abord. Proposer une
retouche de prompt sans avoir regardé la séquence d'outils est l'erreur la plus
courante sur un agent.

**Une modification de prompt — ou de description d'outil — se mesure.** Un run
avant, un run après, un seul paramètre changé.

**Prévenir de la charge avant de lancer une évaluation.** Sur 30 cas et
`MAX_ITERATIONS = 8`, c'est jusqu'à 240 appels au LLM partagé, pas 30.
Proposer `--limite 3` d'abord. Sur le serveur, appliquer aussi la règle des
horaires.

**Ne pas conclure sur un écart faible.** Sur 30 cas, trois cas qui basculent
font 10 points. Traduis toujours un écart en nombre de cas. Deux runs
identiques de l'agent de synthèse ont déjà différé de trois cas : une
configuration se mesure sur au moins deux runs.

**Ne pas ajouter de dépendance** sans raison écrite. En particulier : pas de
framework d'agents, pas de bibliothèque d'orchestration « pour voir », pas de
bibliothèque de modèle locale.

**Ne jamais inventer un chiffre.** Performances du modèle, taille de contexte,
débit du serveur : si la valeur n'est pas mesurée ou vérifiée dans la
session, le dire au lieu de l'écrire.

## Ce qui ne va jamais dans le dépôt

Une donnée réelle, une clé, un nom de client, une adresse ou un nom de
serveur, un notebook avec ses sorties.

Attention particulière ici : une **trace d'agent contient le contenu de tout ce
que l'agent a lu**, résultats d'outils compris. C'est la trace la plus riche —
donc la plus dangereuse — des deux modèles de l'organisation. Elle ne se
commite jamais, `traces/` est dans `.gitignore`, et `summarizeTrace` existe
précisément pour n'afficher que des noms d'outils et des compteurs. Tests :
`test_traceSummaryLeaksNoContent`, et pour la réflexion du modèle
`test_reasoningNeverReachesHistoryOrTrace`.

## Commandes et sous-agents

| | |
|---|---|
| `/cadrer` | Écrire question, mesure et seuil avant de coder |
| `/prompt` | Créer une version de prompt sans écraser la précédente |
| `/outil` | Ajouter un outil, avec la question de sa sensibilité |
| `/evaluer` | Lancer l'évaluation et écrire le fichier de run |
| `/avant-pr` | Passer la checklist de revue sur son propre diff |
| `relecteur-resultats` | La conclusion est-elle soutenue par ses chiffres ? |
| `verificateur-donnees` | Le diff contient-il donnée, clé ou nom de client ? |
