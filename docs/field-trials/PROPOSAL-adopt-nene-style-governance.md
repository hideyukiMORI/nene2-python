# Proposal: NeNe 流 Field Trial ガバナンスの導入

> **ステータス**: 提案 (Proposal) — 採否と作業は nene2-python のメンテナに委ねる
> **提案元**: 姉妹リポジトリ `hideyukiMORI/NeNe` のメンテナンス文脈
> **日付**: 2026-05-22

## 背景

nene2-python は Field Trial (FT) を 78 本積み上げている (`docs/field-trials/2026-05-field-trial-1.md` 〜 `2026-05-field-trial-78.md`)。これは姉妹リポジトリ群の中で最多であり、FT 実践そのものが定着している証拠でもある。

ただし **FT を運用する上での規律 (ガバナンス) は明文化されていない**。現状の `CLAUDE.md` と `AGENTS.md` は FT 方法論を `../NENE2/docs/field-trials/` に委譲しているが、NENE2 側にもガバナンス文書は存在しない (本提案と並行して NENE2 にも同等の提案 PR を投げている)。結果として、何を friction とみなすか、どう Issue 化するか、次のトライアルをいつ始めるかといった判断はメンテナの暗黙知に依存している。

`hideyukiMORI/NeNe` (PHP renovation 系) は NENE2 / nene2-python の FT 実践を借りた上に、**形式化レイヤ** (ADR、friction taxonomy、loop cadence、クローン分離規律、bootstrap script) を載せ、過去 1 週間で FT1〜FT6 を回した。本提案はこの形式化レイヤを nene2-python に逆輸入することを推奨する。

## 現状の差分

NeNe には揃っているが nene2-python にはまだ無いもの:

| 資材 | NeNe での所在 | nene2-python の現状 |
|---|---|---|
| FT 方針 ADR | `docs/adr/0002-adopt-field-trial-methodology.md` (53 行) | 無し |
| FT README (運用ガイド) | `docs/field-trials/README.md` (132 行) | 無し |
| Friction 分類タクソノミー | 同 README L73–94 (`docs-gap` / `feature-gap` / `design-trade-off` / `legacy-preserved` / `process-gap`) | 無し |
| Decision 分類 | 同 README L85–94 (`fix-in-framework` / `document` / `keep-legacy` / `defer`) | 無し |
| クローン分離規律 | 同 README L18–50 (`../NeNe-FT/ft{N}-{topic}/`、独立ワーキングツリー、ポートオフセット) | 無し |
| ブートストラップスクリプト | `tools/nene-ft-new.sh` (254 行) | 無し |
| レポートテンプレート | `docs/templates/field-trial-report.md` (95 行) | **無し** (NENE2 にのみ存在) |
| ループ規律 | ADR-0002 L34「次のトライアルは前のトライアルの Issue が全て閉じるまで開始しない」 | 暗黙 |

NENE2 が `docs/templates/field-trial-report.md` を持つのに対し、nene2-python はテンプレートも持たない。委譲パターンの帰結だが、Python 固有の文脈 (uv / alembic / pytest / Pydantic) はそもそも PHP 用テンプレートでは記述できない事項を含む。

## なぜ形式化が役に立つか

NeNe で FT を 6 本走らせて確認できた効果:

1. **ループ規律により finding が「次のトライアル」に混入しなくなる**。78 本の規模では特に、過去の FT で発見した friction を新規 FT で再発見してしまうリスクが高い。
2. **Friction kind により「修正」「文書化」「意図的に残す」が分離される**。`legacy-preserved` は NeNe (renovation 思想) 由来なので nene2-python ではそのまま使えないかもしれないが、置換候補 (例: `python-idiomatic-trade-off`) を立てる余地はある。
3. **ブートストラップスクリプトでトライアル開始コストがほぼゼロになる**。nene2-python は uv / alembic / Docker compose / pytest を組み合わせるためセットアップが PHP より複雑であり、スクリプト化の効果が NENE2 より大きい可能性がある。
4. **ADR 化により姉妹リポジトリへの参照が双方向になる**。現状 nene2-python が NENE2 を参照する一方向だが、nene2-python 独自の ADR があれば NENE2 から逆参照できる関係になる。

## 推奨する導入順 (nene2-python メンテナへの依頼)

採否含めて nene2-python メンテナに委ねるが、もし採用する場合の現実的な順序を提案する:

1. **ADR-0012 (Adopt Field Trial Methodology)** を起こす。NeNe `docs/adr/0002-adopt-field-trial-methodology.md` を雛形に、nene2-python の文脈で書き直す。`docs/adr/` は 0001–0006、0009–0011 で 0007/0008 が欠番だが、慣例通り次番号で 0012 を割り当てる方が安全。
2. **`docs/field-trials/README.md`** を作る。NeNe の README をベースに、Python (uv / alembic / pytest / Pydantic) 文脈で言い換える。クローン分離規律のポート番号は nene2-python の `compose.yaml` 既定値に合わせて調整。
3. **`tools/nene2py-ft-new.sh`** または **`scripts/nene2py-ft-new.sh`** を作る。NeNe `tools/nene-ft-new.sh` を以下のように移植:
    - `composer install` → `uv sync`
    - `compose.yaml` の `app=8000+N` / `postgres=5432+N` (or 既存 nene2-python の port 規則に合わせる)
    - `.claude/settings.local.json` には pytest / uv / alembic 系のコマンドを含める
    - `FT{N}-PLAN.md` skeleton は Python プロジェクト向け項目に書き換え
4. **`docs/templates/field-trial-report.md`** を新規作成。NENE2 のもの (`../NENE2/docs/templates/field-trial-report.md`) を Python 文脈に移植するか、NeNe のテンプレートを直接借りる。

## 留意点 / トレードオフ

- **委譲パターンの解消**: 現在 `CLAUDE.md` / `AGENTS.md` で「FT 方法論は `../NENE2/docs/` を参照」と書かれている。本提案を採用すれば nene2-python は独自のガバナンスを持つことになり、委譲文言は「言語固有の論点は本リポジトリ、共通論点は NENE2 を参照」のような形に書き換えが必要。
- **Python 固有の friction**: pytest fixture、async/await、uv lock、Pydantic v2 移行、alembic autogenerate の挙動など、PHP 側では発生しないタイプの friction が記録対象になる。NENE2 のタクソノミーをそのまま使うか、Python 固有 kind を 1〜2 個追加するかは検討の余地がある。
- **過去 78 本の遡及適用は不要**: 過去レポートにタクソノミーを後付けすることに意味は薄い。新規 (FT-79 以降) から適用すれば十分。
- **NENE2 との同期**: 本 PR と同タイミングで NENE2 側にも同等の提案 PR を投げている。両リポジトリで足並みを揃えるか、片方先行で進めるかはメンテナ判断。

## 作業のオーナーシップ

本提案は方針提示までに留め、**実装作業と受け入れ判断は nene2-python のメンテナ側で行うことを想定している**。NeNe 側で持ち込み PR を出すことはしない (Python プロジェクト固有の慣習を NeNe コンテキストで再構築する負荷の方が大きい)。

nene2-python で実際に着手する場合は、本ファイルを起点に Issue 化 (例: 「ADR-0012 起草」「FT README 作成」「bootstrap script 移植」「report template 作成」を別 Issue) して進めるのが既存のサイクル (branch name `docs/<#issue>-<topic>` 等) と整合する。

## 参考リンク (NeNe 側の参照点)

- ADR-0002: <https://github.com/hideyukiMORI/NeNe/blob/main/docs/adr/0002-adopt-field-trial-methodology.md>
- FT README (friction kind / decision の定義込み): <https://github.com/hideyukiMORI/NeNe/blob/main/docs/field-trials/README.md>
- ブートストラップスクリプト: <https://github.com/hideyukiMORI/NeNe/blob/main/tools/nene-ft-new.sh>
- レポートテンプレート: <https://github.com/hideyukiMORI/NeNe/blob/main/docs/templates/field-trial-report.md>
- 6 トライアル振り返り: <https://github.com/hideyukiMORI/NeNe/blob/main/docs/field-trials/2026-05-reflection-after-six-trials.md>
