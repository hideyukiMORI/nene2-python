# FT170: collections モジュール

**日付**: 2026-05-21
**テーマ**: `collections` モジュール — `namedtuple`・`defaultdict`・`Counter`・`deque`・`OrderedDict`・`ChainMap`
**セキュリティ診断**: なし（170 % 3 = 2）

---

## 概要

Python 標準ライブラリの `collections` モジュールを nene2-python フレームワーク上で検証した。
`collections` は Python の基本データ構造を拡張する実用的なモジュールで、
ドメインデータ集計・キャッシュ・グラフ探索・設定管理に直接使えるパターンを提供する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft170-collections/`

### 主要機能

| クラス/関数 | 概要 |
|---|---|
| `ApiError` (namedtuple) | エラー情報の軽量イミュータブル型。`_asdict()` で辞書変換 |
| `group_by_first_char()` | `defaultdict(list)` でグループ集計 |
| `count_tags()` | `defaultdict(int)` で出現頻度集計 |
| `build_adjacency_list()` | `defaultdict(list)` でグラフ構築 |
| `word_frequency()` / `top_n_words()` | `Counter` で単語頻度・トップN |
| `tag_overlap()` | `Counter` の intersection で共通タグを抽出 |
| `merge_counts()` | 複数 `Counter` を `update()` で合算 |
| `sliding_window_max()` | `deque` で O(n) スライディングウィンドウ最大値 |
| `recent_n()` | `deque(maxlen=n)` でリングバッファ |
| `bfs_path()` | `deque` をキューとして BFS 最短経路探索 |
| `LruCache` | `OrderedDict` + `move_to_end()` で O(1) LRU キャッシュ |
| `resolve_config()` / `config_source()` | `ChainMap` で env > file > defaults の優先順位設定 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/collections/namedtuple` | namedtuple デモ（距離計算・エラー構造体） |
| POST | `/collections/group-by` | defaultdict でグループ集計 |
| POST | `/collections/count-tags` | defaultdict でタグ集計 |
| GET | `/collections/word-freq` | Counter で単語頻度分析 |
| GET | `/collections/sliding-window` | deque でスライディングウィンドウ |
| GET | `/collections/recent` | deque(maxlen) リングバッファ |
| POST | `/collections/bfs` | BFS グラフ探索 |
| PUT/GET | `/collections/lru/{key}` | OrderedDict LRU キャッシュ |
| POST | `/collections/config` | ChainMap 設定レイヤー解決 |

---

## テスト結果

**36 passed（摩擦ゼロ）**

```
36 passed in 0.94s
```

---

## 摩擦ポイント

**今回の FT では実装上の摩擦はゼロだった。**

---

## 観察点

### 観察1: `defaultdict` は「キーがなければ初期値」を明示的に設計できる

```python
result: defaultdict[str, list[str]] = defaultdict(list)
for word in words:
    result[word[0]].append(word)  # KeyError なし
```

`dict.setdefault()` より意図が明確で、`if key not in d:` 分岐が不要になる。
グループ集計・グラフ隣接リスト構築・カウンタ実装の3パターンで多用できる。

### 観察2: `Counter` は集合演算（`+`, `-`, `&`, `|`）が使える辞書

```python
Counter(["python", "typing", "python"]) & Counter(["python", "asyncio"])
# → Counter({"python": 1})  — min(2,1) = 1
```

`Counter` 同士の `+` は合算、`&` は最小値、`|` は最大値。
複数の集計結果をマージする `merge_counts()` は `Counter.update()` で自然に書ける。
`most_common(n)` で上位 N 件を O(n log n) で取得できる。

### 観察3: `deque(maxlen=n)` はリングバッファとして使える

```python
buf: deque[str] = deque(maxlen=5)
buf.extend(["a", "b", "c", "d", "e", "f"])
list(buf)  # → ["b", "c", "d", "e", "f"]  — 最新5件のみ保持
```

`maxlen` を指定すると、追加時に先頭から自動削除される。
ログ末尾 N 行・最近の操作履歴・スライディングウィンドウのバッファとして最適。
`collections.deque` は `list` と異なり先頭操作が O(1)。

### 観察4: `OrderedDict.move_to_end()` で O(1) LRU キャッシュが実装できる

```python
class LruCache:
    def get(self, key: str) -> Any:
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)  # 最近使用済みとしてマーク
        return self._cache[key]

    def put(self, key: str, value: Any) -> None:
        ...
        if len(self._cache) > self.capacity:
            self._cache.popitem(last=False)  # 最も古いものを削除
```

`Python 3.7+` の `dict` は挿入順を保証するが、`move_to_end()` がないため
LRU の「使用順序の更新」には `OrderedDict` が必要。
nene2 の `TtlCache` と組み合わせた TTL+LRU キャッシュへの発展も可能。

### 観察5: `ChainMap` で設定レイヤーのオーバーライドが宣言的に書ける

```python
chain = ChainMap(env_vars, file_config, defaults)
chain["DB_HOST"]  # env_vars → file_config → defaults の優先順位で検索
```

`os.environ` + ファイル設定 + デフォルト値の優先順位解決は
従来 `{**defaults, **file_config, **env_vars}` で実装していたが、
`ChainMap` は元の辞書を変更せず参照のみのため副作用がない。
`chain.maps[0]` で最優先レイヤー、`chain.new_child()` でスコープを重ねることもできる。

---

## nene2-python フレームワークとの統合

- `Counter` はタグ・カテゴリの集計 Use Case で `GROUP BY` SQL の代替になる（小規模データ）
- `LruCache` は nene2 の `TtlCache[V]` と組み合わせて TTL + LRU の複合キャッシュに発展できる
- `ChainMap` は `AppSettings` の `pydantic-settings` が行っている env > file > default 解決と同じパターン
- `deque` は WebSocket メッセージキューやストリーミングレスポンスのバッファとして適用できる
- `namedtuple` は UseCase の軽量 Output DTO として `dataclass(frozen=True)` より軽量な選択肢になる

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`defaultdict` は「エラーが出なくなった辞書」として直感的に受け入れられる。
`Counter` は「辞書の特殊版」として理解でき、`.most_common()` が使いやすい。
`deque` の「両端キュー」という概念は最初はピンとこないが、`maxlen` のリングバッファ用途はすぐに理解できる。

**ドキュメント理解**: `defaultdict(list)` のファクトリ関数の渡し方（`list` を呼び出さない）は最初に混乱する。
`defaultdict(lambda: [])` との違いを最初に説明すると理解が早い。

**事故リスク**: 中。`defaultdict` は存在しないキーにアクセスすると自動で作成するため、
タイポキーが無音で `{}` や `[]` に変わり、後続処理でのデバッグが難しくなる可能性。

**規約の使いやすさ**: コピペで使えるパターンが多い。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`Counter` を知らずに `dict` + `if key in d: d[key] += 1 else: d[key] = 1` を書いている。
`Counter` を知ると即採用する。

**コピペ可能性**: 高。特に `Counter(list).most_common(n)` のワンライナーは即戦力。

**拡張時の罠**: `LruCache` で `OrderedDict` を使っているが、
Python 3.7+ の `dict` で書き直そうとして `move_to_end()` がないことに気づかず壊す可能性。
「`OrderedDict` には `move_to_end()` がある」という固有 API を README に明記するべき。

**セキュリティ的な事故リスク**: 低。`collections` の誤用は機能バグには繋がるが、セキュリティリスクは低い。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`Counter` は JavaScript の `reduce` で頻度集計するパターンと概念的に近い。
`namedtuple` は TypeScript の `readonly struct` 的に理解できる。

**エラーレスポンスの質**: `/collections/sliding-window` で `"a,b,c"` を送ると 422 が返る。
クライアントには `{"error": "values must be comma-separated integers"}` が届き明確。

**事故リスク**: 低。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `QuerySet.values().annotate(count=Count(...))` と `Counter` の使い分けが判断ポイント。
DB に集計クエリを投げられるなら Django ORM が適切。
インメモリ集計（小規模・一時的）には `Counter` が軽量。

**本番投入可能性**: 問題なし。`LruCache` は nene2 の `TtlCache` と組み合わせて即本番投入できる。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- [ ] `defaultdict` のキーが意図せず作成されていないか（`d[key]` アクセスだけでキーが生える）
- [ ] `Counter` の `most_common()` が `None` を返さないことを前提にしているか（空リストなら空リストを返す）
- [ ] `LruCache` が複数リクエストからアクセスされるグローバル状態の場合、`asyncio.Lock()` が必要か確認
- [ ] `ChainMap` の子マップへの書き込みが親マップに伝播しないことを理解しているか

**チームでの安全なパターン**: グローバルな `LruCache` インスタンスは `asyncio.Lock()` でガードするか、
スレッドセーフな実装（`threading.RLock`）に置き換える。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高

**「初心者でも安全な API」達成度**: 中
- `defaultdict` のキー自動生成は初心者には予期しない動作になりうる
- `LruCache` のスレッドセーフ性は nene2 の非同期環境では注意が必要

**設計上の負債・ドキュメント不足**:
- nene2 の `TtlCache[V]` と `LruCache` の組み合わせパターンが未文書化
- グローバルキャッシュインスタンスの非同期安全性に関する how-to がない

**Follow-up Issue 候補**: `docs: キャッシュの TTL + LRU 複合パターンと非同期安全性の how-to を追加`

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 中 | `docs: collections.Counter をタグ集計 Use Case に適用するパターンを how-to に追加` | docs |
| 低 | `feat: TtlCache に LRU 退去ポリシーを追加するオプションを検討` | feat |

---

## まとめ

`collections` モジュールは nene2-python の集計・キャッシュ・探索・設定管理に直接使える実用的な機能群。
36 テスト全通過、摩擦ゼロ。

`defaultdict` / `Counter` / `deque` の三点セットは Python バックエンドの必須知識。
`OrderedDict.move_to_end()` による LRU キャッシュは nene2 の `TtlCache` と組み合わせる価値がある。
`ChainMap` は `pydantic-settings` が内部でやっている設定レイヤー解決と同じパターンで、
環境別設定のオーバーライドを副作用なしに実装できる。

