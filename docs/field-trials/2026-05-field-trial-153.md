# Field Trial 153: struct モジュール

## テーマ

`struct.pack`, `struct.unpack`, `struct.calcsize`, `struct.Struct`,
`struct.iter_unpack`, ビッグ/リトルエンディアン, フォーマット文字を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft153-struct/` に以下を実装:

- `pack_integers()` / `unpack_integers()` — 整数リストのパック/アンパック
- `pack_packet()` / `unpack_packet()` — 疑似ネットワークパケット (`!BBHHI`)
- `pack_uint32_big/little()` / `read_uint32_big/little()` — エンディアン変換
- `pack_float/double()` / `unpack_float/double()` — IEEE 754 浮動小数点数
- `pack_coordinate()` / `unpack_coordinate()` — `struct.Struct` を使った座標データ
- `unpack_array()` — `struct.iter_unpack()` で配列アンパック
- `get_format_info()` — `struct.calcsize()` でフォーマットのバイトサイズ取得
- HTTP エンドポイント 5 本
- 25 テスト全通過（摩擦1件）

## テスト結果

初回: 1 失敗 → 修正後: 25 テスト全通過。

## Friction Points

### FP1: `pack_packet()` の引数名 `packet_type` が辞書展開で衝突した

```python
def pack_packet(version: int, packet_type: int, ...) -> bytes:
    ...

# NG: "type" キーは "packet_type" に対応しない
original = {"version": 1, "type": 2, ...}
pack_packet(**original)  # → TypeError: unexpected keyword argument 'type'
```

関数の引数名として `type` を避け `packet_type` としたが、
テストで辞書を `**` 展開したとき `type` キーが `packet_type` 引数にマッチせず
`TypeError` が発生した。

**対処**: テストで `pack_packet(version=1, packet_type=2, ...)` とキーワード引数を明示した。

## 観察

### O1: フォーマット文字で型とバイトサイズを指定する

```
B  unsigned char    1 byte    (0〜255)
H  unsigned short   2 bytes   (0〜65535)
I  unsigned int     4 bytes   (0〜4294967295)
Q  unsigned long long 8 bytes
f  float (単精度)   4 bytes
d  double (倍精度)  8 bytes
```

先頭の文字でバイトオーダーを指定する:
- `!` または `>` — ビッグエンディアン（ネットワークバイトオーダー）
- `<` — リトルエンディアン
- `=` — ネイティブバイトオーダー（プラットフォーム依存）

### O2: `struct.calcsize()` でフォーマットのバイトサイズを事前計算できる

```python
struct.calcsize("!BBHHI")  # → 10 (1+1+2+2+4)
struct.calcsize("!ddd")    # → 24 (8+8+8)
```

パケット受信時に何バイト読むべきかを静的に決定するのに使う。

### O3: `struct.Struct` でフォーマットをコンパイル済みオブジェクトにする

```python
_COORD_STRUCT = struct.Struct("!ddd")  # モジュール初期化時にコンパイル

data = _COORD_STRUCT.pack(lat, lon, alt)
lat, lon, alt = _COORD_STRUCT.unpack(data)
```

繰り返し使うフォーマットはモジュールレベルで `struct.Struct` にコンパイルする
ことでパースのオーバーヘッドを削減できる。

### O4: `struct.iter_unpack()` で繰り返しデータをイテレーターで取得できる

```python
data = struct.pack("!HHH", 10, 20, 30)
values = [item[0] for item in struct.iter_unpack("!H", data)]
# → [10, 20, 30]
```

`iter_unpack()` は `data` の先頭から `fmt` サイズずつ区切って
タプルのイテレーターを返す。固定サイズレコードの配列に有用。

### O5: 単精度と倍精度の精度差

```python
value = 1.23456789012345
packed_float = unpack_float(pack_float(value))   # 単精度
packed_double = unpack_double(pack_double(value)) # 倍精度

abs(packed_float - value)   # ≈ 1.5e-8 (誤差が大きい)
abs(packed_double - value)  # ≈ 1.4e-16 (精度が高い)
```

座標・金額など精度が必要なデータには倍精度 (`d`) を使う。

### O6: `!` と `>` はどちらもビッグエンディアン（ネットワークバイトオーダー）

```python
struct.pack("!I", 42) == struct.pack(">I", 42)  # True
```

ネットワークプロトコルの文脈では `!`（ネットワークバイトオーダーの明示）を
使う慣習がある。

## まとめ

FT153 は摩擦1件（`packet_type` 引数名と辞書展開のミスマッチ）。
`struct` モジュールはネットワークパケット・バイナリファイル・センサーデータなど
固定サイズバイナリ形式の処理に有用。`struct.Struct` でコンパイルし
`iter_unpack` で配列を効率よく処理するパターンが実用的。
