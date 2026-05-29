# Méthodologie des Field Trials — objectif, phases et terminus

Ce document explique **pourquoi** la boucle Field Trial (FT) existe, **comment son objectif
a évolué au fil du temps**, et **ce qui constitue "terminé"**. Pour le processus opérationnel
(cadence, modèle de rapport, personas DX review), consultez le §12 de CLAUDE.md et
[`docs/templates/field-trial-report.md`](../templates/field-trial-report.md).

---

## Pourquoi la boucle FT existe

Un Field Trial implémente une charge de travail réelle sur nene2-python dans un **bac à sable
isolé** (`/home/xi/docker/nene2-python-FT/ftNNN-*/`), exécute la suite de vérifications
complète, et enregistre les points de friction que rencontre réellement un implémenteur.
L'objectif est de laisser la documentation et la conception évoluer à partir d'observations
plutôt que de spéculations :

- prouver que l'API du framework est **stable et ergonomique** dans des domaines variés ;
- faire remonter les **points de friction** (`F-1`, `F-2`, …) sous forme d'observations concrètes et corrigeables ;
- accumuler des **connaissances en sécurité** grâce aux diagnostics et aux pentests ;
- maintenir le framework **lisible par les IA** en documentant les décisions.

Le résultat durable de chaque FT est son **rapport dans `docs/field-trials/`** — le bac à
sable lui-même est jetable (son `.venv` est régénérable avec `uv sync`, et les anciens bacs
à sable sont périodiquement nettoyés avec `ft-status.sh --clean-sandbox`).

---

## Phases (l'objectif a évolué)

La boucle FT n'a pas été une activité unique. Son objectif a évolué, et la #540 existe
précisément parce que cette évolution n'avait jamais été consignée.

### Phase 0 — Boucle de retour du framework (FT1–FT6)

Des applications exemples réelles (lunchlog, bookshelf, tasklist, wallet, weather, …) ont
exercé les **fonctionnalités du framework** : auth (Bearer/ApiKey), pile middleware, serveur/client
MCP, transactions, `AsyncUseCaseProtocol`. L'objectif était de **consolider l'API propre du
framework**. Les résultats ont été répercutés directement dans `nene2.*`.

### Phase 1 — Validation systématique de la stdlib (FT7–~FT202)

Une fois l'API principale stabilisée, la boucle a pivoté pour encapsuler **un module de la
bibliothèque standard par FT** dans une fine couche HTTP nene2. Chaque FT répond à la question :
"la forme parse → use-case → response du framework est-elle ergonomique pour *ce* domaine, et
quels sont les pièges d'utilisation sûre de *ce* module ?" Cette phase a produit l'essentiel de
l'[INDEX FT](../field-trials/INDEX.md) et du corpus how-to.

### Phase 2 — Approfondissement de la sécurité (FT203+)

À partir de ~FT203, la boucle s'est centrée de plus en plus sur les **primitives de sécurité** et
la série "évitement des primitives dangereuses" : `secrets`/`hashlib`/`hmac` (crypto),
`pickle`/`marshal`/`ast.literal_eval`/`eval` (désérialisation), `subprocess` (injection de commandes),
`urllib.parse`/`ipaddress` (SSRF), `re` (ReDoS), `zipfile`/`tarfile`/`zlib`/`gzip`/`lzma`
(bombes à glissement et de décompression), `string.Formatter`/`string.Template` (format-string / SSTI).
Ces FTs ont la plus grande valeur durable car ils servent également de **liste de contrôle d'audit**.

### Cadence

- **Diagnostic de sécurité** (🔒) à chaque FT où `FT % 3 == 0`.
- **Pentest cracker** (🔍) à chaque FT où `FT % 4 == 0`.
- **Revue DX à 6 personas** à chaque FT.

---

## Terminus — ce que "terminé" signifie

Le balayage exhaustif de la stdlib n'était pas censé s'exécuter indéfiniment, et en Phase 2 la
**surface de la bibliothèque standard pertinente pour la sécurité est couverte** (sérialisation,
compression/archives, analyse/balisage, crypto/auth, subprocess, chemins de fichiers, entrée réseau,
regex, renforcement de la validation numérique). Continuer à encapsuler des modules purement
computationnels (`colorsys`, `cmath`, `calendar`, `math`, …) apporte des **rendements décroissants**
par rapport à l'objectif initial.

La boucle FT est donc considérée **terminée en tant que balayage exhaustif**, et passe en mode
**maintenance + à la demande**. Un nouveau FT n'est justifié que lorsque l'un de ces déclencheurs
se produit :

1. **Une nouvelle capacité du framework** doit être validée (retour au style Phase 0).
2. **Une nouvelle dépendance** (stdlib ou tierce partie) est *adoptée dans le framework ou les
   exemples* — la valider avant de s'y fier.
3. **Une catégorie de sécurité non couverte** est identifiée (p. ex. une nouvelle classe d'injection).
4. **Demande explicite** du mainteneur.

En mode maintenance, les obligations récurrentes sont le cycle mensuel
`uv lock --upgrade` → `pip-audit` → tests → PR (CLAUDE.md §5), pas de nouveaux FTs.

### Comment décider d'arrêter ou de continuer

- Si un FT candidat ne correspond à **aucun** des quatre déclencheurs ci-dessus, préférez
  **ne pas** l'exécuter — clôturez la boucle et consacrez le cycle aux issues ouvertes ou
  aux fonctionnalités du framework.
- "Complétion" est une décision documentée, pas un nombre. Enregistrez la décision dans
  [`docs/todo/current.md`](../todo/current.md) (et mettez à jour le
  [pied de page de l'INDEX FT](../field-trials/INDEX.md)) lorsque la boucle est mise en pause.

---

## Classification des frictions et des décisions

Lorsqu'un FT à la demande est lancé, enregistrez chaque point de friction (F-1, F-2, …) avec un
**type** et une **décision**, afin que les résultats restent cohérents et analysables d'un essai
à l'autre plutôt qu'en prose libre.

**Types de friction**

| Type | Signification |
|---|---|
| `docs-gap` | Le framework se comporte correctement, mais la doc/les exemples ne permettaient pas de le découvrir. |
| `feature-gap` | Une capacité véritablement manquante que l'implémenteur attendait. |
| `design-trade-off` | La friction est une conséquence acceptée d'un choix de conception délibéré. |
| `process-gap` | Friction d'outillage/workflow (CI, vérifications, scaffolding), pas l'API elle-même. |
| `python-idiomatic-trade-off` | Friction spécifique à Python (coercition Pydantic v2, async/await, `uv lock`, mypy strict) sans réponse unique "correcte". |

Le dernier type remplace le `legacy-preserved` spécifique à la rénovation de NeNe, qui ne
s'applique pas à un framework Python greenfield.

**Types de décision** — chaque friction se résout en exactement un :

| Décision | Action |
|---|---|
| `fix-in-framework` | Modifier le code framework/exemple dans le même PR FT. |
| `document` | Le comportement est correct ; ajouter ou clarifier la doc / CLAUDE.md. |
| `keep` | Accepter tel quel et enregistrer la justification. |
| `defer` | Suivre en tant qu'Issue de suivi avec une raison indiquée — le seul cas où une Issue survit au PR FT (CLAUDE.md §12). |

Cette taxonomie a été distillée à partir de la proposition de gouvernance du dépôt sœur (#545).
Le reste de cette proposition (script bootstrap, un ADR dédié, un README FT séparé) était déjà
couvert par CLAUDE.md §12, le [modèle de rapport](../templates/field-trial-report.md) existant
et ce document — ou rendu peu utile par l'atteinte du terminus de la boucle.

---

## Résumé

| Phase | Plage | Objectif | Statut |
|---|---|---|---|
| 0 — Retour du framework | FT1–FT6 | Consolider l'API nene2 | ✅ terminé |
| 1 — Validation stdlib | FT7–~FT202 | Confirmer l'ergonomie + développer la doc | ✅ balayé |
| 2 — Approfondissement sécurité | FT203+ | Primitives de sécurité comme liste d'audit | ✅ surface couverte |
| Maintenance + à la demande | — | FT uniquement sur les 4 déclencheurs ; deps mensuelles | 🔄 actuel |
