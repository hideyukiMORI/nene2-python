# FT193: socket モジュール — TCP/UDP socketpair・DNS 解決・ソケットオプション

**日付**: 2026-05-21
**テーマ**: Python `socket` モジュールの基本操作を nene2-python FastAPI アプリとして実装し、低レベルネットワーク API の DX を検証する
**セキュリティ診断**: なし（193 % 3 = 1）
**クラッカーペンテスト**: なし（193 % 4 = 1）

---

## 概要

`socket` モジュールは Python の BSD ソケット低レベル API。
TCP/UDP 通信・DNS 名前解決・ソケットオプション照会などを提供する。
FT192（asyncio）と並ぶ並行・ネットワーク系の基盤モジュールであり、
今回は `socketpair()` を使ったインプロセスエコーで外部ネットワーク依存なしにテストする設計をとった。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft193-socket/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `dns_lookup(host, port)` | `socket.getaddrinfo` で DNS 名前解決。`match` 文で型安全にアドレスタプルを展開 |
| `hostname_info()` | `gethostname` / `getfqdn` / `gethostbyname` でローカルホスト情報を取得 |
| `tcp_echo_pair(message)` | `socketpair(SOCK_STREAM)` を使ったインプロセス TCP エコー |
| `udp_echo_pair(message)` | `socketpair(SOCK_DGRAM)` を使ったインプロセス UDP エコー |
| `socket_options_info()` | 新規 TCP ソケットのデフォルトオプション値（`SO_REUSEADDR` / `SO_SNDBUF` 等）を返す |
| `socket_capabilities()` | IPv6 対応・デュアルスタック対応・デフォルトタイムアウトを報告 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/socket/dns-lookup` | DNS ルックアップ（`host` / `port` を受け取る） |
| GET | `/socket/hostname` | ローカルホスト情報 |
| POST | `/socket/tcp-echo` | TCP エコー（socketpair） |
| POST | `/socket/udp-echo` | UDP エコー（socketpair） |
| GET | `/socket/options` | ソケットオプション照会 |
| GET | `/socket/capabilities` | 実行環境のソケット機能情報 |

---

## テスト結果

**27 passed**

```
27 passed in 0.35s
```

---

## 摩擦ポイント

### F-1: `sendall(b"")` で `recv()` がブロック（深刻度: 中）

**事象**: `tcp_echo_pair("")` を呼ぶと `client.sendall(b"")` が no-op になり、
`server.recv(256)` がデータを待ち続けてテストが永久ブロックした。

**原因**: TCP ソケットは `send(b"")` を実際には送出しない。
`recv()` はソケットが閉じられるか、データが届くまで待ち続ける。
UDP (`SOCK_DGRAM`) は 0 バイトデータグラムを送信できるため問題にならないが、
TCP とふるまいが異なる点が開発者の盲点になりやすい。

**対応**: 空メッセージを早期リターンで処理する。

```python
def tcp_echo_pair(message: str) -> EchoResult:
    message = message[:MAX_MESSAGE_LEN]
    # sendall(b"") は TCP ではデータを送出しないため server.recv がブロックする
    if not message:
        return EchoResult(sent="", received="", matched=True, byte_count=0)
    ...
```

CLAUDE.md への追記事項なし（一般的な Python ソケット挙動）。

### F-2: `socket.getaddrinfo` 戻り値の mypy 型エラー（深刻度: 低）

**事象**: `info[4][0]` を `AddressInfo.address: str` に渡すと mypy が
`Argument has incompatible type "str | int"` と報告した。

**原因**: `socket.getaddrinfo` の戻り値アドレスタプルは
`tuple[str, int] | tuple[str, int, int, int]` より広い union として typeshed が定義しており、
`[0]` インデックスアクセスで `str | int` になる。

**対応**: `match` 文の型パターンで絞り込む。

```python
match info[4]:
    case (str() as address, int() as addr_port, *_):
        addresses.append(AddressInfo(
            family=info[0].name,
            type=info[1].name,
            address=address,
            port=addr_port,
        ))
    case _:
        pass
```

`str() as address` / `int() as addr_port` のパターンが mypy の型絞り込みを働かせ、
`cast()` や `# type: ignore` なしで型安全に書けた。Python 3.10+ `match` の典型的な有効活用。

---

## 観察点

### 観察1: `socketpair` でネットワーク依存なしにソケット動作を検証できる

```python
client, server = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
try:
    client.sendall(message.encode())
    data = server.recv(MAX_MESSAGE_LEN)
    server.sendall(data)
    received_bytes = client.recv(MAX_MESSAGE_LEN)
finally:
    client.close()
    server.close()
```

`socketpair()` はカーネル内のパイプに近く、ネットワークスタックを経由しない。
FT 環境でポートを bind/listen せずにソケット通信をテストするのに最適。
`AF_UNIX + SOCK_STREAM` (TCP 相当) と `AF_UNIX + SOCK_DGRAM` (UDP 相当) の両方が使える。

### 観察2: `socket.getaddrinfo` 戻り値を `match` で分岐するパターン

```python
match info[4]:
    case (str() as address, int() as addr_port, *_):
        # AF_INET: (host, port)
        # AF_INET6: (host, port, flowinfo, scopeid)
        # どちらも先頭2要素が (str, int) なのでこのパターンで捕捉できる
        ...
    case _:
        pass  # 想定外のアドレス族（AF_ALG 等）はスキップ
```

`*_` で残余要素を無視しているため AF_INET4/INET6 の両方を1パターンで処理できる。
これは Python 3.10 以降の `match` がある場合の慣用的な書き方。

### 観察3: `socket.AddressFamily.name` / `socket.SocketKind.name` で読みやすい文字列を取得

```python
# info[0] は AddressFamily IntEnum なので .name でシンボル名を取得
family=info[0].name   # "AF_INET" / "AF_INET6"
type=info[1].name     # "SOCK_STREAM"
```

`IntEnum` の `.name` プロパティはシリアライズ時に読みやすく、
直接 `int` を返すより API レスポンスとして価値が高い。

### 観察4: `socket_capabilities()` で環境差異を明示的に記録

```python
def socket_capabilities() -> SocketCapabilities:
    has_ipv6 = socket.has_ipv6
    try:
        has_dual = socket.has_dualstack_ipv6()
    except OSError:
        has_dual = False
    return SocketCapabilities(
        has_ipv6=has_ipv6,
        has_dualstack_ipv6=has_dual,
        default_timeout=socket.getdefaulttimeout(),
        hostname=socket.gethostname(),
    )
```

`has_dualstack_ipv6()` は OS レベルで IPv6 デュアルスタックが使えるかを確認する。
WSL2 環境では `False` になることがある。`OSError` でガードしてポータブルに書く。

---

## nene2-python フレームワークとの統合

- `socket` モジュールは nene2-python のミドルウェアや認証と直接の接点はない。
  DNS 解決やホスト情報を FastAPI エンドポイントで提供する形で統合した。
- 戻り値は `@dataclass(frozen=True, slots=True)` で定義し、
  FastAPI が Pydantic v2 経由で JSON シリアライズする。
  ネストした dataclass (`DnsResult.addresses: list[AddressInfo]`) も問題なく動作した。
- HTTP 境界での入力制約（`host: str = Field(..., max_length=253)`, `port: int = Field(80, ge=1, le=65535)`）
  は Pydantic Body で完結し、DNS ルックアップに不正入力が渡らないよう保護した。
- `getaddrinfo` が失敗する未知ホストに対しては `socket.gaierror` を捕捉して空リストを返す
  設計にした。例外を 500 にせず意味のあるレスポンスを返す nene2 の「薄い HTTP 層」の原則に合致する。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

FastAPI の Hello World を書けるようになった段階。
`socket` が標準ライブラリにあることは知っているが、
「なぜ TCP と UDP で動きが違うのか」の理解が浅い。

**ドキュメント理解**: `socket.getaddrinfo` の戻り値型が複雑で、Python 公式ドキュメントだけでは
タプルの構造を読み取りにくい。サンプルコードと「`info[4]` はアドレスタプルで AF_INET は `(host, port)`」
という図解があると理解が一段上がる。  
**事故リスク**: 中。`sendall(b"")` で `recv()` がブロックするというF-1の罠は
初心者には気づきにくい。「空文字の扱い」は必ずコメントかドキュメントに記載が必要。  
**規約の使いやすさ**: `socketpair` → `sendall` → `recv` のシーケンスは直感的で、
一度理解すれば机械的に書ける。`finally` でクローズを忘れない規約（または `with` 文）を教えれば問題ない。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

既存コードを見て `socketpair` を使いこなせるが、深い仕組みはブラックボックスにしがち。

**コピペ可能性**: `tcp_echo_pair` のコードをそのままコピーして使える。
ただし「空メッセージのガード」を知らずに削除するリスクがある（F-1 の再発）。  
**拡張時の罠**: `socketpair` を `connect` に置き換えて外部サービスに向けるとき、
タイムアウトを設定しないまま本番投入するリスクが高い。
`sock.settimeout(seconds)` を必ず設定することをコードコメントかテンプレートで強制すべき。  
**セキュリティ的な事故リスク**: 低。`socket` そのものは低レベル API のため、
使い方を誤っても金銭的損害には直結しにくい。ただし `getaddrinfo` を SSRF の起点にするパターンには注意が必要。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

REST API の呼び出し側として実装経験があり、
「なぜこのエンドポイントが `message: str` だけを受け取るのか」が分かりやすい API を好む。

**エラーレスポンスの質**: `host` が 254 文字以上のとき 422 + `detail` の Pydantic エラーが返り、
クライアントにとって扱いやすい。`gaierror` (DNS 失敗) を 200 + 空 `addresses` で返す設計は
クライアントがエラーを区別する必要がなく良い DX 判断。  
**Python 固有概念の学習コスト**: `socketpair` / `AF_UNIX` / `SOCK_STREAM` の意味は
TypeScript 経験者には馴染みが薄い。エンドポイントの OpenAPI description で目的を説明している点は助かる。  
**事故リスク**: 低。このエンドポイント群は読み取り系で副作用がないため、
フロントエンド寄り開発者が誤用してシステムを壊すリスクは小さい。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`socket` モジュールは使ったことがあるが、`socketpair` は「そんな API があったのか」という反応。

**他フレームワークとの差異**: Django では `socket` をユーザーランドに公開するエンドポイントを
作ることはほとんどない。このFTで示したパターン（ヘルスチェックや環境情報エンドポイントへの応用）は
実用性が高く「使える設計」と評価できる。  
**nene2-python の薄さへの評価**: `create_app()` ファクトリパターン・`APIRouter` の分離が
このサイズ（ファイル3つ）でも一貫して適用されており、「小さくても本番と同じ構造」を実証している。
チームで使うときのテンプレートとして説得力がある。  
**本番投入可能性**: ソケット操作系の本番エンドポイントは認証保護が必須。
このFTでは `BearerTokenMiddleware` を使っていないが、実運用では認証ミドルウェアを被せること。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

チームメンバーが F-1 の罠を再現しないかを重点確認する。

**コードレビューチェックポイント**:
- [x] 空メッセージの早期リターンがあるか（F-1 対策）
- [x] `socketpair` の `finally` でクローズ漏れがないか
- [x] `gaierror` を握りつぶさず意味のある値を返しているか
- [ ] 実運用では `sock.settimeout()` でハングを防いでいるか（このFTには外部接続なし）
- [x] ユーザー入力 `host` / `message` に長さ制限があるか（Pydantic Field で保護済み）

**チームでの安全な共有パターン**: 空入力ガードとタイムアウト設定をセットにした
`safe_socket_connect()` ヘルパーをプロジェクト共通ユーティリティとして提供すると事故が減る。  
**ツール追加の必要性**: ruff の `S` ルールが `socket.create_connection` に `timeout=None` を
flagging しないため、コードレビューで明示的に確認が必要。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

CLAUDE.md の「Security first」「薄い HTTP 層」「AI-readable」との整合を確認する。

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 高  

- `host` の長さ制限（253 chars = DNS 最大長）と `port` の範囲制限（1〜65535）が Pydantic で宣言的に実装されており、検証を忘れるリスクがない。
- `gaierror` の捕捉と空リスト返却は、例外を「500 にする」のではなく「意味のあるレスポンスにする」nene2 の方針に沿っている。
- `match` 文による型安全な分岐は `cast()` / `# type: ignore` を使わず mypy --strict をパスしており、CLAUDE.md「型安全ポリシー」を遵守している。
- F-1（空メッセージブロック）の修正コメント「sendall(b"") は TCP ではデータを送出しないため server.recv がブロックする」は、「WHY が非自明な場合のみコメント」のポリシーに準拠した正当なコメント。

**設計上の負債・ドキュメント不足**: なし  
**Follow-up Issue 候補**: なし

---

## Follow-up Issues

なし — 今回発見した摩擦点（F-1, F-2）はサンドボックス内で即時修正済み。

---

## まとめ

`socket` モジュールは低レベル API ながら、
`socketpair()` を使うことで外部ネットワーク依存なしにインプロセスでエコーテストを書ける点が発見だった。
`getaddrinfo` の戻り値型（F-2）は typeshed の制約で mypy が `str | int` を報告するが、
`match` 文のパターンマッチングで `cast()` なしに解決できた。
`sendall(b"")` が TCP ブロックの原因になる点（F-1）は典型的な「空入力の罠」として記録した。

次のFT194 は 194 % 3 = 2 → セキュリティ診断なし、194 % 4 = 2 → クラッカーペンテストなし。
ネットワーク系の継続として `ssl` モジュール（TLS コンテキスト・自己署名証明書・HTTPS クライアント）が候補。
