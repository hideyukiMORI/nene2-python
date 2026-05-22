# TODO — current

最終更新: 2026-05-22
現状: **v1.8.69 安定版 / フィールドトライアルループ継続中（FT197 完了）**

---

## 状態サマリー

v1.8.69 完了済み。FT197（urllib.parse — URL 解析・エンコード・クエリ文字列処理）まで全 197 件を実施済み。
ネットワーク系（FT193〜197）の縦断を継続中。
リポジトリは main ブランチ 1 本・Issue/PR/ブランチ全ゼロのクリーンな状態。
フィールドトライアルループは FT198 以降も継続中。

---

## オープン PR

なし（main ブランチはクリーン）

---

## オープン Issue

| # | タイトル | 優先度 | 種別 |
|---|---|---|---|
| [#539](https://github.com/hideyukiMORI/nene2-python/issues/539) | handler の response_model を統一して CLAUDE.md ポリシーに準拠 | 中 | enhancement |
| [#540](https://github.com/hideyukiMORI/nene2-python/issues/540) | FT ループの目的と終着点を明文化する | 中 | docs |
| [#541](https://github.com/hideyukiMORI/nene2-python/issues/541) | PyPI 公開フロー検証（uv publish ワークフロー） | 中 | enhancement |

---

## 直近の完了マイルストーン

| バージョン | 主な内容 |
|---|---|
| v1.8.69 | FT197: urllib.parse — URL 解析・エンコード・クエリ文字列処理 |
| v1.8.68 | FT196: http.client — 低レベル HTTP クライアント・接続管理・SSRF 防御（クラッカーペンテスト、条件付き合格） |
| v1.8.67 | FT195: ssl — SSLContext・暗号スイート列挙・セキュリティ評価 API（セキュリティ診断、条件付き合格） |
| v1.8.66 | FT194: ipaddress — IPv4/IPv6 解析・CIDR 計算・SSRF 防御パターン |
| v1.8.65 | FT193: socket — TCP/UDP socketpair・DNS 解決・ソケットオプション |
| v1.8.64 | FT192: asyncio — コルーチン・タスク・Lock・Event・Semaphore・Queue・TaskGroup（診断＋ペンテスト） |

---

## フィールドトライアル進捗

**実施済み**: FT1〜FT197（全 197 件）

索引: [`docs/field-trials/INDEX.md`](../field-trials/INDEX.md)

**次のアクション**:
- FT198 を開始（198 % 3 = 0 → **セキュリティ診断あり**、198 % 4 = 2 → ペンテストなし）
- テーマ候補: `http.server`（簡易 HTTP サーバー）または `urllib.request`（URL フェッチ）

---

## 明日以降の優先タスク

| 優先度 | Issue | タスク | 種別 |
|---|---|---|---|
| 高 | — | FT198 実施（セキュリティ診断あり） | FT |
| 中 | [#539](https://github.com/hideyukiMORI/nene2-python/issues/539) | handler の response_model 統一（CLAUDE.md ポリシー準拠） | enhancement |
| 中 | [#540](https://github.com/hideyukiMORI/nene2-python/issues/540) | FT ループの目的・終着点を明文化 | docs |
| 中 | [#541](https://github.com/hideyukiMORI/nene2-python/issues/541) | PyPI 公開フロー検証（uv publish） | enhancement |
| 中 | — | 並行系 how-to ガイド作成（FT188〜192 まとめ） | docs |
| 低 | — | PostgreSQL / MySQL 実 DB 統合テスト（CI Docker service） | infra |
| 低 | — | PyJWT 推移的 CVE（PYSEC-2025-183）— mcp 修正待ち | 保留 |

---

## 改善検討事項

| 課題 | 優先度 | Issue | 備考 |
|---|---|---|---|
| handler response_model 未使用 | 中 | [#539](https://github.com/hideyukiMORI/nene2-python/issues/539) | CLAUDE.md ポリシー違反 |
| FT ループ目的の明文化 | 中 | [#540](https://github.com/hideyukiMORI/nene2-python/issues/540) | FT1〜6 と FT7〜 でフェーズが変化している |
| PyPI 未公開 | 中 | [#541](https://github.com/hideyukiMORI/nene2-python/issues/541) | uv publish フロー検証が必要 |
| http.client DNS リバインディング未防御 | 中 | — | FT196 で発見。ipaddress+dns resolve 二段階チェックが必要（本番化時） |
| parse_qs vs parse_qsl how-to | 低 | — | FT197 で観察。クエリ文字列 how-to に追記予定 |
| 並行系 how-to（threading / asyncio 比較） | 中 | — | FT188〜192 の知見を 1 本にまとめる |
| PostgreSQL / MySQL 実 DB 統合テスト | 中〜高 | — | CI に Docker service ジョブを追加検討 |
| PyJWT 推移的 CVE（PYSEC-2025-183） | 低 | — | mcp 側の修正を待ち。文書化済み |
