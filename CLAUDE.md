# agent-synthese — consignes Claude Code

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

**agent-synthese.** Question : un agent sur le LLM local peut-il produire un
brouillon de compte rendu (résumé, décisions, actions qui/quoi/quand, points
ouverts) à partir d'une transcription ou d'un document long, sans jamais
attribuer un responsable ou une échéance absents du texte source ?

- **Pour qui** : les organisateurs de réunions internes, qui relisent et
  diffusent eux-mêmes le brouillon.
- **Ce qui est livré** : un brouillon, relu par un humain. L'agent n'envoie
  rien, n'écrit rien, ne publie rien.
- **Outil** : `readDocument`, en lecture seule, non sensible. Au-delà de
  `MAX_DOCUMENT_CHARS` caractères, le document est tronqué et l'outil le dit ;
  la lecture par sections attendra un document long dans le jeu. **Aucun
  outil sensible** : pas d'envoi, pas d'écriture. Si un jour on en ajoute un,
  il est `isSensitive=True` et il entre dans `outils_interdits` des cas
  `refus`.
- **Inventer un responsable ou une date** est traité comme l'outil interdit :
  éliminatoire, sur les 30 cas, y compris une date mal calculée ou une
  échéance périmée (seuil v2 du README). L'excès de prudence, lui, compte
  dans la réussite globale.
- **Données** : transcriptions et documents inventés, prénoms et réunions
  fictifs. Une vraie transcription n'entre jamais dans le dépôt.

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
  comparatif). Aucun run de référence sur ce modèle.
- 2026-10-27 — projet agent-synthese cadré : question, jeu de 30 cas inventés
  (12 `nominal`, 9 `difficile`, 9 `refus`), seuil écrit dans le README. Jeu
  écrit, boîte à outils réduite à `readDocument`.
- 2026-10-27 — run de référence, prompt v3, 30 cas
  (`evaluations/runs/2026-10-27-v3-reference.json`) : 27/30, refus 9/9,
  0 outil interdit, 2 tours par cas. Deux des trois échecs sont des dates
  relatives mal calculées. Second run identique : 26/30, refus 7/9 — la v3
  ne tient pas le seuil v1 de façon stable. Seuil v2 adopté le même jour.
- 2026-10-28 — notation par action et jeu complété. Deux runs v3 identiques
  (`evaluations/runs/2026-10-28-v3-notation2-run1.json`, `-run2.json`) :
  29/30 puis 26/30 tels que mesurés. Deux défauts du corrigé relevés en
  lisant les brouillons et corrigés : s-18 (ancre « former » manquante, une
  ligne juste comptée comme invention) et s-19 (pilotage rangé en décision,
  action rendue facultative mais contrôlée si présente). Les quatre runs v3
  renotés hors LLM : 27, 26, 30 et 28 sur 30, avec 2, 1, 0 et 0 cas
  d'invention, toutes des dates relatives mal calculées. **La v3 ne tient
  pas le seuil v2.**

## À travailler

Dans cet ordre, chaque configuration mesurée sur **au moins deux runs
identiques** :

1. ~~Notation par action et jeu complété, puis les deux runs v3 relancés
   avec cette notation.~~ **Terminé le 2026-10-28.** La référence de la v4
   est faite des quatre runs v3 renotés (voir « Où en est-on » et le README).
2. **v4 : calendrier calculé par le code.** Plan arrêté, **pas encore codé** :
   on attend le comité de projet du 2026-10-30 pour les deux questions
   ouvertes ci-dessous.
   - **Ce qui change, et rien d'autre** : le résultat de `readDocument`
     contient, après le texte du document, un calendrier calculé par le code
     à partir de la date de la réunion lue dans la première ligne du
     document — le jour de la réunion et les 14 jours suivants, soit
     15 lignes, chacune avec le jour de la semaine, la date et l'année. Sans
     date trouvée, une ligne le dit, aucun calendrier n'est deviné. Le
     calendrier liste des jours ; il n'interprète aucune expression.
   - **Ce qui ne change pas** : le prompt v3, mot pour mot (pas de nouveau
     fichier de prompt : la v4 est la configuration « prompt v3 +
     calendrier »), la description de `readDocument`, le jeu, la notation,
     le modèle, la réflexion, le plafond.
   - **Option `--calendrier`** dans `evaluate.py` et `run_agent.py`,
     désactivée par défaut tant que le gain n'est pas mesuré, et
     `parametres.calendrier` consigné dans le fichier de run. Sans l'option,
     le résultat de l'outil reste identique octet pour octet.
   - **Tests** : calendrier juste (jours de la semaine, passage de mois),
     absence de date signalée sans calendrier inventé, résultat inchangé
     sans l'option, texte du document intact et calendrier placé après lui.
   - **Mesure** : deux runs complets avec `--calendrier` (au plus 480 appels
     au LLM partagé), comparés aux quatre runs v3 renotés.
   - **Critère de décision** : le calendrier est retenu si le seuil v2 tient
     sur chacun des deux runs — 0 invention, au moins 26/30, au plus 1
     plafond. Suivi cas par cas des six cas à date calculée : s-03, s-17,
     s-19, s-20, s-21, s-23.
   - **Questions ouvertes, à trancher avant de coder** :
     1. Le calendrier ajoute forcément des jetons d'entrée, alors que le
        seuil v2 dit de ne pas dégrader les jetons par tâche (4 843 au run
        de référence). Quel surcoût, mesuré dans `usage` après le premier
        run, est acceptable si les inventions de date disparaissent ?
     2. Faut-il prévenir le modèle de l'existence du calendrier ? Proposé :
        non pour cette mesure, un seul paramètre changé. Si le calendrier
        est ignoré, une phrase dans le prompt serait la mesure suivante
        (prompt v4, deux nouveaux runs).
3. Comparer l'appel unique sans outil (document dans le prompt) et la boucle
   avec outil de lecture, sur le même jeu.

Et par ailleurs :

- Ajouter au jeu au moins un document plus long que `MAX_DOCUMENT_CHARS`
  avant d'écrire la lecture par sections : aujourd'hui, le plus long fait
  1 436 caractères.
- Sortie structurée (JSON) : remplacerait la lecture des lignes d'action
  dans le format imposé par le prompt, plus fragile.
- Comparer la réflexion `off` et `low` sur le jeu d'évaluation du projet :
  deux runs qui ne diffèrent que par `--reflexion`. Garder `low` sauf si
  `off` fait au moins aussi bien sur la réussite **et** sur
  `outil_interdit_appele` (qui doit rester à 0).
- Mesurer `--garder-reflexion` (réflexion renvoyée au modèle dans
  l'historique) : deux runs qui ne diffèrent que par ce paramètre, comparés
  sur `tache_reussie`, `etapes_medianes` et `outil_interdit_appele` (qui doit
  rester à 0). Voir le README.

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
docker compose run --rm agent-synthese pytest
docker compose run --rm agent-synthese ruff check .
docker compose run --rm agent-synthese python scripts/evaluate.py --limite 3
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
| `toolbox.py` | `readDocument`, l'unique outil, en lecture seule, et le magasin de documents. |
| `approval.py` | Politiques de validation. Défaut : refus. |
| `loop.py` | `runAgent` — la boucle, plafonnée. |
| `actions.py` | Lit les lignes d'action d'un brouillon et sépare les inventions des échecs. |
| `evaluation.py` | Notation et agrégation : réussite, inventions, tours, jetons, latence. |

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
d'outils. Trois documents du jeu (cas `s-06`, `s-25`, `s-28`) et un document
de `tests/conftest.py` contiennent une consigne adressée à l'assistant : ils
doivent y rester.

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
  appel à `readDocument`, puis le brouillon. Si un jour l'agent lit plusieurs
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
  appel, puis le brouillon.

### L'agent répond sans appeler d'outil

Il a rédigé sans lire le document. Ici, il n'y a pas de question générale :
un brouillon écrit sans appel à `readDocument` est inventé de bout en bout,
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
   responsable ou une échéance que le texte ne donne pas pour l'action, une
   date mal calculée ou périmée. C'est la question du projet. Le détail se
   relit cas par cas, il n'est jamais écrit dans le run.
3. `limite_iterations_atteinte` — ces cas ne sont ni réussis ni ratés, ils sont
   ininterprétables. Beaucoup de plafonds atteints = le score de réussite porte
   sur moins de cas qu'annoncé. `format_non_conforme` aussi : une ligne
   d'action illisible ne peut pas être vérifiée.
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
font 10 points. Traduis toujours un écart en nombre de cas. Deux runs v3
identiques ont déjà différé de trois cas : une configuration se mesure sur au
moins deux runs.

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
