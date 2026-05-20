# Field Trial 154: array モジュールと memoryview

## テーマ

`array.array` の typecode, `frombytes/tobytes`, `fromlist/tolist`, `buffer_info`,
`memoryview` でのゼロコピースライス を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft154-array/` に以下を実装:

- `create_int/float/double_array()` — 各型の `array.array` を作成
- `array_to_bytes()` / `bytes_to_int_array()` — バイト列との相互変換
- `array_to_list()` / `list_to_uint16_array()` — Python リストとの相互変換
- `slice_bytes_zero_copy()` — `memoryview` でゼロコピースライス
- `bytes_sum_via_memoryview()` — `memoryview` + `array.frombytes()` でバイト合計
- `get_memoryview_info()` — `memoryview` のメタ情報取得
- `get_array_info()` / `array_statistics()` — `array.array` の情報と統計
- HTTP エンドポイント 5 本
- 22 テスト全通過（摩擦0件）

## テスト結果

初回: 22 テスト全通過。摩擦なし。

## 摩擦なし

今回はブロッカーとなる摩擦なし。`array.array` の型注釈の扱いが確認できた。

## 観察

### O1: `array.array` は homogeneous な型付き配列

```python
arr = array.array("H", [0, 100, 65535])  # unsigned short (2 bytes each)
arr.typecode  # "H"
arr.itemsize  # 2
```

Python リストと違い、すべての要素が同じ C 型でなければならない。
`typecode` は `B`(uint8), `H`(uint16), `I`(uint32), `f`(float32), `d`(float64) など。

### O2: `tobytes()` / `frombytes()` でバイナリとの相互変換ができる

```python
arr = array.array("H", [1, 2, 3])
raw = arr.tobytes()        # → b'\x01\x00\x02\x00\x03\x00' (little-endian on x86)
arr2 = array.array("H")
arr2.frombytes(raw)
arr2.tolist()              # → [1, 2, 3]
```

`tobytes()` のバイトオーダーはプラットフォームのネイティブオーダー。
`struct.pack("!H", ...)` と組み合わせてネットワークオーダーに変換することも可能。

### O3: `memoryview` でゼロコピースライスができる

```python
data = b"Hello, World!"
mv = memoryview(data)
sliced = bytes(mv[7:12])  # → b"World"
# slice した時点ではコピーが発生しない
```

`bytes[7:12]` は新しい `bytes` オブジェクトを作るが、
`memoryview(data)[7:12]` は同じメモリを参照するだけ（コピーなし）。
大きなバッファを扱うときのメモリ使用量削減に有効。

### O4: `bytes` の `memoryview` は読み取り専用

```python
data = b"hello"
mv = memoryview(data)
mv.readonly  # → True
# mv[0] = 72  # TypeError: cannot modify read-only memory
```

書き込み可能な `memoryview` は `bytearray` や `array.array` から作成する。

### O5: `buffer_info()` でメモリアドレスと要素数を取得できる

```python
arr = array.array("H", [1, 2, 3])
address, length = arr.buffer_info()
# address: メモリアドレス (int)
# length: 要素数 (3)
```

`buffer_info()` は C 拡張との連携（ctypes など）でメモリポインタを得るのに使う。

### O6: `array.array` の型注釈は `array.array[int]` / `array.array[float]`

```python
from typing import Any
import array

def create_int_array(values: list[int]) -> array.array[int]:
    return array.array("i", values)

def array_statistics(arr: "array.array[Any]") -> dict[str, float]:
    lst = arr.tolist()
    ...
```

`array.array` は Python 3.9+ でジェネリック指定可能。
`array.array[int]` / `array.array[float]` の使い分けが typecode に対応している。

## まとめ

FT154 は摩擦ゼロ。`array.array` は数値データの密なバイナリ表現に有用で、
`tobytes/frombytes` でバイナリプロトコルとの相互変換が簡単にできる。
`memoryview` はゼロコピーで大きなバッファをスライスするのに有用で、
`bytes` からの `memoryview` は読み取り専用になる点を把握しておくとよい。
