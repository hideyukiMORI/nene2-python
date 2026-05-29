# FT234: ipaddress — ip_address / ip_network / is_private（SSRF 対策）

**日付**: 2026-05-29
**テーマ**: Python `ipaddress` モジュールの IP 分類と IP ベース SSRF 対策の実装と検証
**セキュリティ診断**: 🔒 あり（234 % 3 = 0）
**クラッカーペンテスト**: なし（234 % 4 = 2）

---

## 概要

`ipaddress` は IP アドレス/ネットワークの解析・分類を行う。FT228（urllib.parse の host 許可リスト）と相補的に、**IP リテラルベースの SSRF 対策**を検証した。ホスト名許可リストで守れない「URL に直接 IP を書く」攻撃（`http://127.0.0.1/`、`http://169.254.169.254/`）を、IP 分類で遮断する。

| API | ユースケース |
|---|---|
| `ipaddress.ip_address(s)` | IPv4/IPv6 アドレス解析 |
| `.is_global` / `.is_private` / `.is_loopback` 等 | アドレス分類 |
| `.ipv4_mapped` | IPv4-mapped IPv6 の埋め込み v4 取得 |
| `ipaddress.ip_network(cidr)` + `in` | CIDR 包含判定 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft234-ipaddress/`

| 関数 | 概要 |
|---|---|
| `classify_ip()` | 分類フラグ（private/loopback/link_local/global）を返す |
| `ssrf_check()` | **`is_global` を肯定条件**に安全判定（IPv4-mapped を展開） |
| `_unwrap_mapped()` | `::ffff:127.0.0.1` を埋め込み v4 に展開 |
| `in_network()` | CIDR 包含判定 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/ip/classify` | IP 分類 |
| POST | `/ip/ssrf-check` | SSRF 安全性判定 |
| POST | `/ip/in-network` | CIDR 包含判定 |

---

## 摩擦点

### F-1【重要】`is_private` 等のフラグ OR は CGNAT（100.64.0.0/10）を取りこぼす

**観察**: 当初 SSRF 判定を `is_private or is_loopback or is_link_local or is_reserved or is_multicast or is_unspecified` の OR で実装したが、診断で **`100.64.0.1`（CGNAT, RFC 6598）が SAFE と誤判定**された。Python 3.14 で `100.64.0.1` は `is_private=False` / `is_reserved=False` だが **`is_global=False`**。フラグ OR の列挙では取りこぼす範囲が存在する。

**対処**: 安全判定を「**`is_global` が True であること**」という肯定条件に変更（許可リスト的発想）。これで CGNAT・TEST-NET（`192.0.2.0/24`）・ベンチマーク（`198.18.0.0/15`）など、列挙しきれない非グローバル範囲をまとめて遮断できる。診断で `100.64.0.1` / `192.0.2.1` / `198.18.0.1` がすべて BLOCK になることを確認。

```python
ip = _unwrap_mapped(_parse_ip(value))
safe = ip.is_global   # 列挙 OR ではなく「グローバル到達可能」を肯定条件に
```

### F-2: IPv4-mapped IPv6 混乱攻撃（`::ffff:127.0.0.1`）

**観察**: `::ffff:127.0.0.1` は IPv6 表記だが実体は IPv4 ループバック。IPv6Address のまま分類すると埋め込み v4 の属性が正しく反映されない場合があり、SSRF バイパスに使われる。

**対処**: `ip.ipv4_mapped` が非 None なら埋め込み v4 に展開してから判定。`::ffff:127.0.0.1` → `127.0.0.1` として BLOCK、`::ffff:169.254.169.254`（メタデータ）も BLOCK。

### F-3: `ip_network` の `strict` と CIDR 解析

**観察**: `ip_network("10.0.0.1/8", strict=True)`（既定）はホストビットが立っていると `ValueError`。ユーザー入力 CIDR では `strict=False` が扱いやすい。

**対処**: `ip_network(cidr, strict=False)` で寛容に解析しつつ、不正 CIDR は 422。

---

## セキュリティ診断結果

| カテゴリ | 例 | 判定 |
|---|---|---|
| 公開 IPv4/IPv6 | `8.8.8.8` / `1.1.1.1` / `2001:4860:4860::8888` | **SAFE** |
| ループバック | `127.0.0.1` / `127.5.5.5` / `::1` | **BLOCK** |
| プライベート | `10.0.0.1` / `172.16.0.1` / `192.168.1.1` / `fc00::1` | **BLOCK** |
| リンクローカル（AWS メタデータ） | `169.254.169.254` / `fe80::1` | **BLOCK** |
| CGNAT（F-1） | `100.64.0.1` | **BLOCK**（is_global 採用後） |
| TEST-NET / ベンチマーク | `192.0.2.1` / `198.18.0.1` | **BLOCK** |
| 未指定 / マルチキャスト / ブロードキャスト | `0.0.0.0` / `224.0.0.1` / `255.255.255.255` | **BLOCK** |
| IPv4-mapped IPv6（F-2） | `::ffff:127.0.0.1` / `::ffff:169.254.169.254` | **BLOCK**（展開して判定） |
| 不正入力 | `999.1.1.1` / `not-an-ip` / `10.0.0.1/8` / `0x7f.0.0.1` | **422** |

**総合評価: 合格（診断で発見した CGNAT 取りこぼしを `is_global` 採用で修正）**

最大の学びは F-1 — **「危険な範囲を列挙する denylist より、`is_global` で公開到達性を肯定する allowlist 的判定が堅い」**。`ipaddress` のフラグは網羅的でないため、SSRF では `is_global` を基準にすべき。

> 補足: 本 FT は IP リテラルの分類のみ。実際の SSRF 完全防御には、ホスト名の **名前解決後の IP** を本 check に通し、かつ DNS リバインディング（解決と接続の間で IP が変わる）対策として「解決した IP に直接接続する」運用が必要（既知の http.client 課題と接続）。

---

## テスト結果

```
11 passed in 0.31s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

IP が「公開かプライベートか」を判定できるのは分かりやすい。`is_global` 一発で安全判定できるのは学びやすい。

**ドキュメント理解**: CGNAT・IPv4-mapped の話は高度。コメントで理由を明示。
**事故リスク（中）**: 自分でフラグを列挙して CGNAT を取りこぼす。
**規約の使いやすさ**: ip → safe/normalized が明快。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

Webhook や画像取得 URL の IP 検証で使う。`is_private` だけ見て CGNAT を見逃す罠は実務で踏みやすい。

**コピペ可能性**: `ssrf_check`（is_global ベース）はそのまま流用可。
**拡張時の罠**: フラグ OR の列挙漏れ・IPv4-mapped。
**事故リスク（中）**: denylist 発想での取りこぼし。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

IP 分類はフロントにない概念。SSRF がサーバー固有の脅威だと理解する契機。

**エラーレスポンスの質**: 不正 IP は 422。
**Python 固有概念**: `ipaddress` のフラグ群・IPv4-mapped。
**事故リスク（低）**: is_global ベースで堅い。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

SSRF 対策の IP 層。`is_global` を基準にする判断は正しい。完全防御には DNS 解決後の IP 検証＋リバインディング対策が要る点も把握済み。

**他フレームワークとの差異**: 多くの SSRF ライブラリが is_global 相当 + 名前解決後検証を行う。
**nene2 の薄さへの評価**: FT228（host 許可リスト）と本 FT（IP 分類）の二段で SSRF を多層防御できる設計。
**事故リスク（低）**: 診断で取りこぼしを修正済み。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- SSRF 判定が `is_global` ベース（肯定条件）か、フラグ OR の denylist になっていないか（CGNAT 取りこぼし）。
- IPv4-mapped IPv6（`::ffff:...`）を展開して判定しているか。
- ホスト名の場合、**名前解決後の IP** を検証しているか（DNS リバインディング）。
- CIDR の `strict` 指定。

**チームでの安全なパターン**: `ssrf_check`（is_global）+ FT228 の host 許可リスト + 解決後 IP 接続を組み合わせる。
**事故リスク（低）**: 診断で CGNAT 修正を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。`is_global` 肯定判定は「許可を明示」思想（CORS/SSRF 共通）。
**初心者でも安全な API 達成度**: `is_global` + IPv4-mapped 展開を関数内に隠蔽し、denylist 取りこぼしの余地を排除。
**改善提案**: FT228 の `validate_url` と本 FT の `ssrf_check` を統合した「SSRF セーフ URL/IP ガード」を `nene2.http` に提供し、名前解決後 IP 検証まで含めた how-to を用意する。
