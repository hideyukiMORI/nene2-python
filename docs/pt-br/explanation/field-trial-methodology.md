# Metodologia de Field Trial — propósito, fases e encerramento

Este documento explica **por que** o loop de Field Trial (FT) existe, **como seu propósito
mudou ao longo do tempo** e **o que conta como "concluído"**. Para o processo mecânico
(cadência, template de relatório, personas do DX review) veja o §12 do CLAUDE.md e
[`docs/templates/field-trial-report.md`](../templates/field-trial-report.md).

---

## Por que o loop de FT existe

Um Field Trial implementa uma carga de trabalho real sobre o nene2-python em um **sandbox
isolado** (`/home/xi/docker/nene2-python-FT/ftNNN-*/`), executa o conjunto completo de
verificações e registra os pontos de atrito que um implementador realmente encontra. O
objetivo é deixar a documentação e o design crescerem a partir da observação, não da
especulação:

- provar que a API do framework é **estável e ergonômica** em domínios diversos;
- identificar **pontos de atrito** (`F-1`, `F-2`, …) como observações concretas e corrigíveis;
- acumular **conhecimento de segurança** por meio de diagnósticos e pentests;
- manter o framework **AI-readable** documentando decisões.

O resultado duradouro de cada FT é seu **relatório em `docs/field-trials/`** — o
sandbox em si é descartável (seu `.venv` pode ser regerado com `uv sync`, e sandboxes
antigos são periodicamente limpos com `ft-status.sh --clean-sandbox`).

---

## Fases (o propósito mudou ao longo do tempo)

O loop de FT não foi uma atividade única. Seu propósito evoluiu, e a issue #540 existe
precisamente porque essa evolução nunca foi documentada.

### Fase 0 — Loop de feedback do framework (FT1–FT6)

Apps de exemplo reais (lunchlog, bookshelf, tasklist, wallet, weather, …) exercitaram
**funcionalidades do framework**: auth (Bearer/ApiKey), pilha de middleware, MCP server/client,
transações, `AsyncUseCaseProtocol`. O objetivo era **fortalecer a API do framework**.
Os achados alimentaram diretamente o `nene2.*`.

### Fase 1 — Validação sistemática da stdlib (FT7–~FT202)

Com a API core estável, o loop pivotou para encapsular **um módulo da biblioteca padrão por FT**
em uma camada HTTP nene2 fina. Cada FT responde: "a forma parse → use-case → response do
framework é ergonômica para *este* domínio e quais são os cuidados de uso seguro *deste* módulo?"
Esta fase produziu a maior parte do [FT INDEX](../field-trials/INDEX.md) e do corpus de how-tos.

### Fase 2 — Aprofundamento de segurança (FT203+)

A partir de ~FT203, o loop se centrou cada vez mais em **primitivos de segurança** e na
série "evitar primitivos perigosos": `secrets`/`hashlib`/`hmac` (criptografia),
`pickle`/`marshal`/`ast.literal_eval`/`eval` (desserialização), `subprocess`
(injeção de comandos), `urllib.parse`/`ipaddress` (SSRF), `re` (ReDoS),
`zipfile`/`tarfile`/`zlib`/`gzip`/`lzma` (path traversal e zip bombs),
`string.Formatter`/`string.Template` (format-string / SSTI). Esses FTs têm o
maior valor duradouro porque funcionam como uma **lista de verificação de auditoria**.

### Cadência

- **Diagnóstico de segurança** (🔒) a cada FT onde `FT % 3 == 0`.
- **Pentest de cracker** (🔍) a cada FT onde `FT % 4 == 0`.
- **DX review de 6 personas** em todo FT.

---

## Encerramento — o que "concluído" significa

A varredura exaustiva da stdlib nunca foi planejada para durar para sempre, e na Fase 2 a
**superfície de segurança relevante da biblioteca padrão está coberta** (serialização,
compressão/arquivos, parsing/markup, crypto/auth, subprocess, caminhos de arquivo,
entrada de rede, regex, hardening de entrada numérica). Continuar encapsulando módulos
puramente computacionais (`colorsys`, `cmath`, `calendar`, `math`, …) gera
**retornos decrescentes** em relação ao propósito original.

O loop de FT é, portanto, considerado **concluído como varredura exaustiva** e transita para
o modo **manutenção + sob demanda**. Um novo FT só é justificado quando um destes gatilhos ocorre:

1. **Nova capacidade do framework** precisa de validação (de volta ao estilo de feedback da Fase 0).
2. **Uma nova dependência** (stdlib ou de terceiros) é *adotada no framework ou nos exemplos*
   — valide antes de depender dela.
3. **Uma categoria de segurança não coberta** é identificada (ex: uma nova classe de injeção).
4. **Solicitação explícita** do mantenedor.

No modo de manutenção, as obrigações recorrentes são o ciclo mensal de
`uv lock --upgrade` → `pip-audit` → teste → PR (CLAUDE.md §5), não novos FTs.

### Como decidir parar ou continuar

- Se um FT candidato **não** mapeia para nenhum dos quatro gatilhos acima, prefira
  **não** executá-lo — encerre o loop e gaste o ciclo em issues abertas ou
  funcionalidades do framework.
- "Conclusão" é uma decisão documentada, não um número. Registre a decisão em
  [`docs/todo/current.md`](../todo/current.md) (e atualize o
  [FT INDEX](../field-trials/INDEX.md)) quando o loop for pausado.

---

## Classificando atrito e decisões

Quando um FT sob demanda é executado, registre cada ponto de atrito (F-1, F-2, …) com um
**tipo** e uma **decisão**, para que os achados permaneçam consistentes e analisáveis entre
os trials em vez de prosa livre.

**Tipos de atrito**

| Tipo | Significado |
|---|---|
| `docs-gap` | O framework se comporta corretamente, mas a docs/exemplos não tornaram isso descobrível. |
| `feature-gap` | Uma capacidade genuinamente ausente que o implementador esperava. |
| `design-trade-off` | O atrito é uma consequência aceita de uma escolha de design deliberada. |
| `process-gap` | Atrito de tooling/fluxo de trabalho (CI, verificações, scaffolding), não a API em si. |
| `python-idiomatic-trade-off` | Atrito específico do Python (coerção do Pydantic v2, async/await, `uv lock`, mypy strict) sem uma única resposta "certa". |

O último tipo substitui o `legacy-preserved` específico de renovação do NeNe, que não
se aplica a um framework Python greenfield.

**Tipos de decisão** — cada atrito se resolve em exatamente uma:

| Decisão | Ação |
|---|---|
| `fix-in-framework` | Alterar o código do framework/exemplo no mesmo PR do FT. |
| `document` | O comportamento está correto; adicionar ou clarificar docs / CLAUDE.md. |
| `keep` | Aceitar como está e registrar o raciocínio. |
| `defer` | Rastrear como uma issue de acompanhamento com motivo declarado — o único caso em que uma issue sobrevive ao PR do FT (CLAUDE.md §12). |

Esta taxonomia foi destilada da proposta de governança do repositório irmão (#545). O
restante dessa proposta (script de bootstrap, ADR dedicado, FT README separado) já estava
coberto pelo CLAUDE.md §12, pelo [template de relatório](../templates/field-trial-report.md)
existente e por este documento — ou tornaram-se de baixo valor com o loop chegando ao seu encerramento.

---

## Resumo

| Fase | Intervalo | Propósito | Status |
|---|---|---|---|
| 0 — Feedback do framework | FT1–FT6 | Fortalecer a API do nene2 | ✅ concluído |
| 1 — Validação da stdlib | FT7–~FT202 | Confirmar ergonomia + expandir docs | ✅ varrido |
| 2 — Aprofundamento de segurança | FT203+ | Primitivos de segurança como checklist de auditoria | ✅ superfície coberta |
| Manutenção + sob demanda | — | FT apenas nos 4 gatilhos; deps mensais | 🔄 atual |
