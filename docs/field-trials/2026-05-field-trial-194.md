# FT194: ipaddress モジュール — IPv4/IPv6 解析・CIDR 計算・SSRF 防御パターン

**日付**: 2026-05-21
**テーマ**: Python `ipaddress` モジュールを使ったアドレス解析・ネットワーク計算・SSRF 防御パターンの実装と検証
**セキュリティ診断**: なし（194 % 3 = 2）
**クラッカーペンテスト**: なし（194 % 4 = 2）

---

## 概要

`ipaddress` モジュールは IPv4/IPv6 アドレス・ネットワークを型安全に扱う標準ライブラリ。
FT193（socket）で DNS 解決の話が出たが、解決後の IP が安全かどうかを確認するのに `ipaddress` は不可欠。
FT184（urllib.request SSRF 防御）で使ったパターンの理論的基盤となるモジュールを正面から検証する。

主要ユースケース:
- DNS 解決後 IP の SSRF 安全性チェック（AWS メタデータ `169.254.169.254` 等のブロック）
- CIDR ネットワーク計算（ホスト数・アドレス範囲）
- IP バージョン・分類フラグの判定（private / loopback / link-local / multicast）
- IP 範囲列挙（監査・ログ用途）

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft194-ipaddress/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `parse_address(ip_str)` | IPv4/IPv6 アドレスを解析。バージョン・分類フラグ全量を返す |
| `parse_network(cidr)` | CIDR 表記を解析。`strict=False` でホストビット許容 |
| `ssrf_safety_check(ip_str)` | DNS 解決後 IP が SSRF に悪用されないか確認。理由コードも返す |
| `cidr_contains(cidr, ip_str)` | IP が CIDR 範囲内にあるか。IPv4/IPv6 バージョン不一致は安全に `False` |
| `ip_range(start, end)` | 範囲内 IP を最大 100 件列挙。超過時は `truncated=True` |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/ipaddress/parse` | IP アドレス解析（フィールドバリデータで不正 IP を 422 返却） |
| POST | `/ipaddress/network` | CIDR ネットワーク解析 |
| POST | `/ipaddress/ssrf-check` | SSRF 安全性チェック |
| POST | `/ipaddress/contains` | CIDR 包含チェック |
| POST | `/ipaddress/range` | IP 範囲列挙 |

---

## テスト結果

**42 passed**

```
42 passed in 0.32s
```

---

## 摩擦ポイント

### F-1: `IPv4Network.num_hosts` が typeshed 未定義（深刻度: 低）

**事象**: `net.num_hosts` を呼ぶと mypy が
`Item "IPv4Network" of "IPv4Network | IPv6Network" has no attribute "num_hosts"` を報告した。

**原因**: Python 標準ライブラリの `ipaddress` モジュールには `num_hosts` プロパティが存在するが、
typeshed の `IPv4Network` / `IPv6Network` スタブには宣言されていない（`_BaseNetwork` に定義されているが継承スタブが未整備）。

**対応**: `num_hosts` を使わず、`prefixlen` と `max_prefixlen` から手動計算する。

```python
# typeshed に num_hosts が未定義のため手動計算
# /31・/127（ポイントツーポイント）と /32・/128（ホストルート）は全アドレスが使用可能
if net.prefixlen >= net.max_prefixlen - 1:
    num_hosts = net.num_addresses
else:
    num_hosts = net.num_addresses - 2
```

### F-2: Python 3.11+ で `127.0.0.1.is_private` が `True` に変更（深刻度: 低）

**事象**: `parse_address("127.0.0.1")` の結果に `is_private=True` が返り、
`assert result.is_private is False` のテストが失敗した。

**原因**: Python 3.11 で `ipaddress` モジュールの `is_private` の定義が拡張された。
`127.0.0.0/8`（ループバック）が `is_private=True` を返すように変更された（RFC 1918 の厳密な解釈から RFC 5735 準拠の解釈へ）。

**対応**: テストから `is_private=False` の仮定を削除し、`is_global=False` のみを確認。

```python
def test_ipv4_loopback(self) -> None:
    result = parse_address("127.0.0.1")
    assert result.is_loopback is True
    # Python 3.11+ では 127.0.0.0/8 が is_private=True を返す仕様変更
    assert result.is_global is False
```

SSRF チェックの `ssrf_safety_check` は `is_loopback` を先にチェックするため影響なし。

### F-3: `ip_range` の `ValueError` が HTTP 500 になる問題（深刻度: 低）

**事象**: `ip_range("10.0.0.10", "10.0.0.1")` で `ValueError` が発生するが、
エンドポイントは 422 を返すべきなのに 500 になっていた。

**原因**: Pydantic の Body バリデーションは `start` / `end` を個別に型チェックするが、
「end >= start」という相関制約は Pydantic では検出できない。
`ip_range` から投げられた `ValueError` は FastAPI のデフォルト動作では 500 になる。

**対応**: エンドポイントで `ValueError` を捕捉して `HTTPException(status_code=422)` に変換。

```python
@router.post("/ipaddress/range")
def range_endpoint(body: RangeBody) -> RangeResult:
    try:
        return ip_range(body.start, body.end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
```

---

## 観察点

### 観察1: `ssrf_safety_check` — SSRF 防御の「セカンドライン」パターン

```python
def ssrf_safety_check(ip_str: str) -> SafetyCheck:
    addr = ipaddress.ip_address(ip_str)
    if addr.is_loopback:
        return SafetyCheck(address=str(addr), is_safe=False, reason="loopback")
    if addr.is_link_local:
        return SafetyCheck(address=str(addr), is_safe=False, reason="link_local")
    if addr.is_private:
        return SafetyCheck(address=str(addr), is_safe=False, reason="private")
    ...
```

SSRF 対策は2層構造が安全:
1. ファーストライン: URL/ホスト名をドメインパターンで拒否（`localhost`, `*.internal` 等）
2. セカンドライン: DNS 解決後に IP を `ssrf_safety_check` で確認

FT184（urllib.request）でカバーしたファーストラインと組み合わせることで DNS Rebinding 攻撃にも対応できる。
`169.254.169.254`（AWS EC2 メタデータ）が `is_link_local=True` で確実にブロックされることを確認した。

### 観察2: `cidr_contains` で `match` 文を使った型安全な分岐

```python
match (net, addr):
    case (ipaddress.IPv4Network() as net4, ipaddress.IPv4Address() as addr4):
        contains = addr4 in net4
    case (ipaddress.IPv6Network() as net6, ipaddress.IPv6Address() as addr6):
        contains = addr6 in net6
    case _:
        contains = False
```

`IPv4Address in IPv4Network` は OK だが `IPv6Address in IPv4Network` は `TypeError`。
`match` で型を同時絞り込みしてバージョン不一致を型レベルで排除できる。
このパターンは FT193（socket）の `getaddrinfo` 型絞り込みと同じアプローチ。

### 観察3: `@field_validator` で HTTP 境界の IP 形式バリデーション

```python
class ParseAddressBody(BaseModel):
    address: str = Field(..., max_length=45)

    @field_validator("address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        try:
            ipaddress.ip_address(v)
        except ValueError as exc:
            raise ValueError("invalid IP address") from exc
        return v
```

Pydantic の `str` フィールドはデフォルトで IP 形式を検証しない。
`@field_validator` で `ipaddress.ip_address()` を呼ぶことで、
HTTP 境界で不正 IP を 422 として弾ける。
`ssrf_safety_check` の入力にはあえてバリデータを付けず、
内部で `invalid_address` を返す設計にした（サービスの挙動が安定する）。

### 観察4: `ip_range` の `match start:` パターン

```python
match start:
    case ipaddress.IPv4Address():
        addresses = [str(ipaddress.IPv4Address(int(start) + i)) for i in range(count)]
    case ipaddress.IPv6Address():
        addresses = [str(ipaddress.IPv6Address(int(start) + i)) for i in range(count)]
```

`ip_address()` の返り値は `IPv4Address | IPv6Address`。
`ipaddress.ip_address(int(start) + i)` を使うと大きい整数が IPv4 範囲外で IPv6 になるリスクがある。
`match` でバージョンを先に絞り込んで `IPv4Address(int)` / `IPv6Address(int)` を直接使うことで
バージョン保存が型レベルで保証される。

---

## nene2-python フレームワークとの統合

- `ipaddress` モジュールは nene2 のミドルウェアと直接の接点はないが、
  `ssrf_safety_check` は `nene2.http` や `nene2.middleware` が提供する SSRF 防御ユーティリティの候補。
- FT184（urllib.request）の SSRF 防御実装では `ipaddress.ip_address(resolved_ip)` をチェックする
  コードが必要になる。今回実装した `ssrf_safety_check` はその実装の参照として使える。
- HTTP 境界のバリデーションで `@field_validator` + `ipaddress.ip_address()` の組み合わせは
  Pydantic BodyModel に組み込む標準パターンとして CLAUDE.md への追記候補。
- `ip_range` の `ValueError` → 422 変換は、ドメインロジックの入力エラーをどう HTTP 境界で扱うかの好例。
  `ValidationException` を使う nene2 パターンとの整合も検討余地がある。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

SSRF という言葉を聞いたことはあるが、「なぜ IP アドレスをコードでチェックするのか」がまだ腑に落ちていない段階。

**ドキュメント理解**: `ipaddress.ip_address()` と `ipaddress.ip_network()` の使い方は Python 公式ドキュメントが丁寧で理解しやすい。
ただし「`is_private` の定義が Python 3.11 で変わった」（F-2）はドキュメントに小さくしか書かれておらず、テストが壊れて初めて気づくことが多い。
バージョン間の差異を解説する how-to ページがあると助かる。  
**事故リスク**: 中。`is_private` と `is_loopback` を個別にチェックしなければ `127.0.0.1` が抜けるリスクがある（3.11 以前の Python では）。`ssrf_safety_check` のような一元的な関数でラップするパターンを教えると安全。  
**規約の使いやすさ**: `ipaddress.ip_address(str)` → `addr.is_private` のシーケンスは直感的で習得しやすい。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

SSRF チェックを実装したことがあり、`if ip.startswith("192.168")` のような文字列比較でやっていた可能性がある。

**コピペ可能性**: `ssrf_safety_check` のコードをそのままコピーできる品質。ただし `is_loopback` と `is_private` の順序を入れ替えると動作が変わる（3.11 以前）ことに気づきにくい。  
**拡張時の罠**: 「IPv4 しかチェックしていない」まま IPv6 対応の要件が来たとき、`is_link_local` の `fe80::/10` などが見落とされやすい。IPv4 と IPv6 を同時にカバーするこの実装は参照価値が高い。  
**セキュリティ的な事故リスク**: 中。`ssrf_safety_check` を使わずに自前チェックを書くと脆弱になる可能性がある。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

IP アドレスの概念は知っているが `is_link_local` や CIDR 表記が馴染み薄い。

**エラーレスポンスの質**: 不正 IP に対して `@field_validator` が 422 + `detail: "invalid IP address"` を返すため、クライアント実装が容易。`ssrf_safety_check` が `is_safe=false, reason="link_local"` を返す設計は、クライアント側でブロック理由を表示できて良い。  
**Python 固有概念の学習コスト**: `ipaddress.ip_network("192.168.1.0/24", strict=False)` の `strict=False` の意味は Python 固有。「ホストビットが立っていても正規化して受け入れる」説明が必要。  
**事故リスク**: 低。このエンドポイントは副作用がない解析系。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

IP 検証を `django.core.validators.validate_ipv4_address` で実装してきた経験がある。

**他フレームワークとの差異**: Django の `InetAddressField` (django-netfields) より明示的だが、標準ライブラリだけでここまでできる点は評価が高い。`@field_validator` + `ipaddress` の組み合わせは Django フォームのカスタムバリデータと発想が同じで移行コストが低い。  
**nene2-python の薄さへの評価**: SSRF チェックがミドルウェアに組み込まれず「ユースケース層で明示的に呼ぶ」設計は、「魔法を排除して可視化する」nene2 の方針と整合している。どのエンドポイントで SSRF チェックをしているかコードレビューで確認しやすい。  
**本番投入可能性**: `ssrf_safety_check` をユーティリティとして共通化し、外部 URL を受け取るエンドポイントすべてで使う運用が望ましい。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

DNS Rebinding 攻撃を知っており、「SSRF チェックは DNS 解決後に行う」の原則を重視している。

**コードレビューチェックポイント**:
- [x] `ssrf_safety_check` を DNS 解決後に呼んでいるか（解決前に呼んでも意味がない）
- [x] `is_loopback` の前に `is_link_local` を確認しているか（順序依存なし、全フラグをカバー）
- [x] IPv6 の `::1` も `is_loopback=True` で弾けているか
- [x] `169.254.169.254`（AWS メタデータ）が `is_link_local` でブロックされるか
- [x] バージョン不一致（IPv4 CIDR + IPv6 アドレス）が型安全に `False` を返すか

**チームでの安全な共有パターン**: `ssrf_safety_check` を `nene2.http.utils` に追加して、外部 URL を受け取る全エンドポイントで import を強制する仕組みが良い。今後の FT で nene2 コアへの昇格を検討。  
**ツール追加の必要性**: ruff では「SSRF チェックなしで外部 URL を fetch している」パターンを静的に検出できない。コードレビューガイドラインへの追記が実用的。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

CLAUDE.md 「Security first」「初心者でも安全な API」との整合を確認する。

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 高  

- HTTP 境界で `@field_validator` + `ipaddress.ip_address()` を使って不正 IP を 422 に変換している。初心者がコピーしても「文字列のまま使う」事故を防げる。
- `ssrf_safety_check` が `loopback` → `link_local` → `private` の順で明示的にチェックするため、SSRF 防御の穴が読みやすい。「何をチェックしているか」が可視化されている。
- F-2（Python 3.11 の `is_private` 変更）は CLAUDE.md に追記すべき知見。`is_loopback` と `is_private` を別々に扱う必要性と Python バージョン間の差異を記録する。
- F-3（`ValueError` → 422 変換）は nene2 の `ValidationException` パターンとの整合を今後検討すべき。`HTTPException(status_code=422)` は簡便だが `Problem Details` 形式ではない。

**設計上の負債**: `ssrf_safety_check` を nene2 コア (`nene2.http.safety` 等) に昇格させる候補。FT184 で urllib.request に使い、今回で ipaddress との組み合わせが確認できた。  
**Follow-up Issue 候補**: `ssrf_safety_check` の nene2 コア昇格（中優先度）

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 中 | `ssrf_safety_check` ユーティリティを nene2 コアに昇格させる | feat |
| 低 | Python 3.11+ の `is_private` 仕様変更を docs/how-to に記録 | docs |

※ nene2 コア昇格は FT 単体の PR 内には収めず、別途 Issue/PR で対応する。

---

## まとめ

`ipaddress` モジュールは SSRF 防御の実装基盤として非常に実用的だった。
`169.254.169.254`（AWS メタデータエンドポイント）が `is_link_local=True` で確実にブロックされることを実証し、
loopback / private / link-local / reserved の全フラグを組み合わせたチェック関数のリファレンス実装を得た。

技術的な発見として、Python 3.11 の `is_private` 定義変更（F-2）と typeshed の `num_hosts` 未定義（F-1）は
バージョン依存のはまりポイントとして記録価値がある。

次の FT195 は 195 % 3 = 0 → **セキュリティ診断あり**、195 % 4 = 3 → クラッカーペンテストなし。
テーマ候補: `ssl` モジュール（TLS コンテキスト・証明書検証）または `http.client`（低レベル HTTP クライアント）。
