# Field Trial 127: collections モジュールの高度な活用

## テーマ

`Counter`, `defaultdict`, `deque`, `ChainMap` を使った
集計・グルーピング・固定長履歴管理・設定レイヤリングを FastAPI エンドポイントで検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft127-collections/` に以下を実装:

- `VoteStore` — `Counter[str]` を使った投票集計・`most_common()` ランキング
- `group_by_tag()` — `defaultdict(list)` を使ったタグ別記事グルーピング
- `_request_history` — `deque(maxlen=10)` を使った固定長リクエスト履歴
- `ChainMap` — session > user > default の優先順位で設定をレイヤリング
- `POST /votes/{candidate}` — 投票
- `GET /votes/top/{n}` — 上位N件取得
- `GET /articles/by-tag` — タグ別グルーピング
- `GET /history` — リクエスト履歴
- `GET /config/{key}` — ChainMap で解決した設定値
- `PUT /config/session/{key}` — セッション設定の上書き
- 19 テスト通過

## テスト結果

全 19 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `Counter` で投票集計と `most_common()` が自然に表現できる

```python
from collections import Counter

counter: Counter[str] = Counter()
counter["alice"] += 1
counter["alice"] += 1
counter["bob"] += 1

counter.most_common(2)   # [("alice", 2), ("bob", 1)]
counter.total()          # 3  (Python 3.10+)
```

`dict` で実装するより `Counter` のほうが意図が明確。
`+` 演算子でカウンターを合算することもできる。

### O2: `defaultdict(list)` でグルーピングがシンプルに書ける

```python
from collections import defaultdict

grouped: defaultdict[str, list[int]] = defaultdict(list)
for article in articles:
    for tag in article.tags:
        grouped[tag].append(article.article_id)
```

`if key not in grouped: grouped[key] = []` のボイラープレートが不要。
`dict(grouped)` で通常の dict に変換できる。

### O3: `deque(maxlen=N)` で固定長キューが実現できる

```python
from collections import deque

history: deque[dict[str, object]] = deque(maxlen=10)
history.append({"path": "/api/v1", "status": 200})
# 11個目を追加すると自動的に先頭の要素が削除される
```

`list` に `[-N:]` スライスするより効率的。
右端追加・左端削除が O(1)（list は O(n)）。

### O4: `ChainMap` で設定のレイヤリングが実現できる

```python
from collections import ChainMap

default_cfg = {"theme": "light", "language": "en", "page_size": 20}
user_cfg = {"theme": "dark", "language": "ja"}
session_cfg = {}  # 空でも参照として持てる

config: ChainMap[str, object] = ChainMap(session_cfg, user_cfg, default_cfg)

config["theme"]     # "dark"  (user_cfg が優先)
config["page_size"] # 20      (default_cfg にフォールバック)

# セッション設定を上書き（session_cfg の参照が変わるので自動反映）
session_cfg["theme"] = "system"
config["theme"]     # "system" (session_cfg が最優先)
```

`session_cfg` への直接変更が `ChainMap` に即座に反映される。
これは `ChainMap` が各マップへの **参照** を保持しているため。

## まとめ

FT127 は摩擦ゼロ確認。`collections` の各クラスを FastAPI エンドポイントで
活用するパターンを確認した。特に `ChainMap` による設定レイヤリングは
環境変数・ファイル設定・実行時オーバーライドの優先順位管理に応用できる。
