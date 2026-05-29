# Field-Trial-Methodik — Zweck, Phasen und Abschluss

Dieses Dokument erläutert **warum** die Field-Trial-Schleife (FT) existiert, **wie sich ihr Zweck im Laufe der Zeit verändert hat** und **was als „abgeschlossen" gilt**. Den mechanischen Ablauf (Rhythmus, Berichtsvorlage, DX-Review-Personas) finden Sie in CLAUDE.md §12 und [`docs/templates/field-trial-report.md`](../templates/field-trial-report.md).

---

## Warum die FT-Schleife existiert

Ein Field Trial implementiert eine echte Arbeitslast auf Basis von nene2-python in einer **isolierten Sandbox** (`/home/xi/docker/nene2-python-FT/ftNNN-*/`), führt die vollständige Prüfsuite aus und dokumentiert die Reibungspunkte, auf die ein Implementierer tatsächlich stößt. Das Ziel ist es, Dokumentation und Design aus der Beobachtung heraus wachsen zu lassen, statt aus Spekulation:

- den Nachweis erbringen, dass die Framework-API **stabil und ergonomisch** über diverse Domains ist;
- **Reibungspunkte** (`F-1`, `F-2`, …) als konkrete, behebbare Beobachtungen aufdecken;
- **Sicherheitswissen** durch Diagnosen und Cracker-Pentests akkumulieren;
- das Framework **AI-lesbar** halten, indem Entscheidungen dokumentiert werden.

Das bleibende Ergebnis jedes FTs ist sein **Bericht in `docs/field-trials/`** — die Sandbox selbst ist wegwerfbar (ihre `.venv` ist mit `uv sync` regenerierbar, und alte Sandboxes werden regelmäßig mit `ft-status.sh --clean-sandbox` bereinigt).

---

## Phasen (der Zweck änderte sich im Laufe der Zeit)

Die FT-Schleife war keine einheitliche Aktivität. Ihr Zweck entwickelte sich weiter, und #540 existiert genau deshalb, weil diese Entwicklung nie dokumentiert wurde.

### Phase 0 — Framework-Feedback-Schleife (FT1–FT6)

Echte Beispielanwendungen (lunchlog, bookshelf, tasklist, wallet, weather, …) übten **Framework-Features** aus: Auth (Bearer/ApiKey), Middleware-Stack, MCP-Server/Client, Transaktionen, `AsyncUseCaseProtocol`. Das Ziel war die **Härtung der eigenen Framework-API**. Erkenntnisse flossen direkt in `nene2.*` zurück.

### Phase 1 — Systematische stdlib-Validierung (FT7–~FT202)

Sobald die Kern-API stabil war, schwenkte die Schleife auf das Einwickeln **eines Standard-Bibliothek-Moduls pro FT** in eine dünne nene2-HTTP-Schicht um. Jeder FT beantwortet: „Ist die parse → use-case → response-Form des Frameworks für *diese* Domain ergonomisch, und was sind die Safe-Usage-Fallstricke *dieses* Moduls?" Diese Phase erzeugte den Großteil des [FT INDEX](../field-trials/INDEX.md) und des How-to-Korpus.

### Phase 2 — Sicherheitsvertiefung (FT203+)

Ab ~FT203 konzentrierte sich die Schleife zunehmend auf **Sicherheitsprimitive** und die Serie zur Vermeidung gefährlicher Primitive: `secrets`/`hashlib`/`hmac` (Krypto), `pickle`/`marshal`/`ast.literal_eval`/`eval` (Deserialisierung), `subprocess` (Command Injection), `urllib.parse`/`ipaddress` (SSRF), `re` (ReDoS), `zipfile`/`tarfile`/`zlib`/`gzip`/`lzma` (Slip & Dekomprimierungsbomben), `string.Formatter`/`string.Template` (Format-String / SSTI). Diese FTs haben den höchsten bleibenden Wert, da sie gleichzeitig als **Audit-Checkliste** dienen.

### Rhythmus

- **Sicherheitsdiagnose** (🔒) bei jedem FT, bei dem `FT % 3 == 0`.
- **Cracker-Pentest** (🔍) bei jedem FT, bei dem `FT % 4 == 0`.
- **6-Persona-DX-Review** bei jedem FT.

---

## Abschluss — was „fertig" bedeutet

Die erschöpfende stdlib-Durchsicht war nie dazu gedacht, ewig zu laufen, und in Phase 2 ist die **sicherheitsrelevante Standard-Bibliothek-Oberfläche abgedeckt** (Serialisierung, Komprimierung/Archive, Parsing/Markup, Krypto/Auth, Subprocess, Dateisystempfade, Netzwerkeingabe, Regex, numerische Eingabeabsicherung). Das Weiterhüllen rein rechenintensiver Module (`colorsys`, `cmath`, `calendar`, `math`, …) bringt **abnehmende Renditen** gegenüber dem ursprünglichen Zweck.

Die FT-Schleife gilt daher als **als erschöpfender Sweep abgeschlossen** und wechselt in den **Wartungs- + On-Demand**-Modus. Ein neuer FT ist nur dann gerechtfertigt, wenn einer dieser Auslöser eintritt:

1. **Neue Framework-Fähigkeit** muss validiert werden (zurück zum Phase-0-Feedback-Stil).
2. **Eine neue Abhängigkeit** (stdlib oder Drittanbieter) wird *in das Framework oder die Beispiele aufgenommen* — vor der Nutzung validieren.
3. **Eine nicht abgedeckte Sicherheitskategorie** wird identifiziert (z. B. eine neue Injektionsklasse).
4. **Explizite Anfrage** vom Maintainer.

Im Wartungsmodus sind die wiederkehrenden Pflichten der monatliche `uv lock --upgrade` → `pip-audit` → Test → PR-Zyklus (CLAUDE.md §5), nicht neue FTs.

### Wie man entscheidet, ob man aufhört oder weitermacht

- Wenn ein FT-Kandidat **keinem** der vier Auslöser oben zugeordnet werden kann, ziehen Sie es vor, ihn **nicht** durchzuführen — schließen Sie die Schleife und investieren Sie den Zyklus stattdessen in offene Issues oder Framework-Features.
- „Abschluss" ist eine dokumentierte Entscheidung, keine Zahl. Halten Sie die Entscheidung in [`docs/todo/current.md`](../todo/current.md) fest (und aktualisieren Sie den [FT INDEX](../field-trials/INDEX.md)-Fußbereich), wenn die Schleife pausiert wird.

---

## Klassifizierung von Reibung und Entscheidungen

Wenn ein On-Demand-FT durchgeführt wird, dokumentieren Sie jeden Reibungspunkt (F-1, F-2, …) mit einer **Art** und einer **Entscheidung**, damit die Erkenntnisse konsistent und analysierbar über alle Trials hinweg bleiben, statt als Freitext.

**Reibungsarten**

| Art | Bedeutung |
|---|---|
| `docs-gap` | Das Framework verhält sich korrekt, aber die Dokumentation/Beispiele machten es nicht auffindbar. |
| `feature-gap` | Eine tatsächlich fehlende Fähigkeit, die der Implementierer erwartet hatte. |
| `design-trade-off` | Die Reibung ist eine akzeptierte Konsequenz einer bewussten Designentscheidung. |
| `process-gap` | Tooling-/Workflow-Reibung (CI, Prüfungen, Gerüste), nicht die API selbst. |
| `python-idiomatic-trade-off` | Python-spezifische Reibung (Pydantic v2-Coercion, async/await, `uv lock`, mypy strict) ohne eindeutige „richtige" Antwort. |

Die letzte Art ersetzt NeNes renovierungsspezifisches `legacy-preserved`, das auf ein Python-Framework der grünen Wiese nicht zutrifft.

**Entscheidungsarten** — jede Reibung löst sich in genau eine auf:

| Entscheidung | Aktion |
|---|---|
| `fix-in-framework` | Framework-/Beispielcode im selben FT-PR ändern. |
| `document` | Verhalten ist korrekt; Dokumentation / CLAUDE.md hinzufügen oder klären. |
| `keep` | So belassen und die Begründung festhalten. |
| `defer` | Als Follow-up-Issue mit angegebenem Grund verfolgen — der einzige Fall, in dem ein Issue den FT-PR überlebt (CLAUDE.md §12). |

Diese Taxonomie wurde aus dem Schwester-Repo-Governance-Vorschlag (#545) destilliert. Der Rest dieses Vorschlags (Bootstrap-Skript, ein dediziertes ADR, ein separates FT-README) war bereits durch CLAUDE.md §12, die bestehende [Berichtsvorlage](../templates/field-trial-report.md) und dieses Dokument abgedeckt — oder wurde durch das Erreichen seines Abschlusses wertlos.

---

## Zusammenfassung

| Phase | Bereich | Zweck | Status |
|---|---|---|---|
| 0 — Framework-Feedback | FT1–FT6 | nene2-API härten | ✅ abgeschlossen |
| 1 — stdlib-Validierung | FT7–~FT202 | Ergonomie bestätigen + Dokumentation ausbauen | ✅ durchgegangen |
| 2 — Sicherheitsvertiefung | FT203+ | Sicherheitsprimitive als Audit-Checkliste | ✅ Oberfläche abgedeckt |
| Wartung + On-Demand | — | FT nur bei den 4 Auslösern; monatliche Abhängigkeiten | 🔄 aktuell |
