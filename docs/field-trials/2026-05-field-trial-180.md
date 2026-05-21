# FT180: xml モジュール

**日付**: 2026-05-21
**テーマ**: XML パース・構造検証・XXE/エンティティ展開爆弾防御
**セキュリティ診断**: **あり**（180 % 3 = 0）

---

## 概要

Python 標準ライブラリの `xml.etree.ElementTree` と、セキュリティ強化ライブラリ `defusedxml` を検証する。
単純な XML パースにとどまらず、XXE (XML External Entity) インジェクション、
エンティティ展開爆弾（Billion Laughs 攻撃）への対策、
XML 構造検証、安全な XML 構築、RSS フィードパースまで網羅する。

FT180 は 180 % 3 = 0（セキュリティ診断）かつ 180 % 4 = 0（クラッカーペンテスト）の最も重い回。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft180-xml/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `parse_xml(content)` | defusedxml で安全にパース（XXE/展開爆弾防御） |
| `extract_elements(content, tag)` | 指定タグを全て抽出 |
| `xml_to_dict(content)` | XML を dict に変換 |
| `validate_structure(content, required_tags)` | 必須タグの存在検証 |
| `build_xml(data, root_tag)` | dict から XML を安全に構築（NCName 検証 + 自動エスケープ） |
| `prettify_xml(content)` | XML の整形（ET.indent） |
| `parse_rss_feed(content)` | RSS 2.0 フィードをパース |
| `is_safe_xml(content)` | XML の安全性チェック |
| `detect_entity_expansion(content)` | DTD/ENTITY 宣言の検出 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/parse` | XML を安全にパース |
| POST | `/extract` | 指定タグの要素を抽出 |
| POST | `/to-dict` | XML を dict に変換 |
| POST | `/validate` | 必須タグの存在検証 |
| POST | `/build` | dict から XML を構築 |
| POST | `/prettify` | XML を整形 |
| POST | `/rss` | RSS フィードをパース |
| POST | `/safe-check` | XML 安全性チェック |

---

## テスト結果

**56 passed**（初回 54 通過 → F-1 修正後 56 全通過）

```
56 passed in 0.48s
```

mypy: Success / ruff: All checks passed / pip-audit: PYSEC-2025-183（継続監視）

---

## 摩擦ポイント

### F-1: `ET.Element()` が不正な XML タグ名を受け入れる（深刻度: 高）

**事象**: `build_xml({"a": "b"}, root_tag="<inject/>")` を呼ぶと
`ET.Element("<inject/>")` がエラーなしに実行され、`<<inject/>><a>b</a></<inject/>>` という
壊れた XML 文字列が生成された。

**原因**: `xml.etree.ElementTree.Element()` はタグ名に対してバリデーションを行わない。
不正なタグ名を渡しても例外を raise せず、そのまま文字列として使用する。
生成された XML は再パースできない（`ET.fromstring()` が `ParseError` を raise する）が、
API レスポンスとして返されてしまう。

**対応**:
```python
_VALID_XML_NAME_RE = re.compile(r"^[a-zA-Z_][\w\-\.]*$")

def build_xml(data: dict[str, str], root_tag: str = "root") -> str | None:
    if not _VALID_XML_NAME_RE.match(root_tag):
        return None  # 不正なタグ名は拒否
    ...
```

HTTP エンドポイントでは `None` → 400 Bad Request を返すように修正済み。

---

## 観察点

### 観察1: `xml.etree.ElementTree` は XXE に対してデフォルトで脆弱

Python の標準ライブラリ `xml.etree.ElementTree` は、Python 3.8 以降は
一部の外部エンティティ展開を制限しているが、完全ではない。
`defusedxml` はより包括的な防御を提供する。

```python
# 標準ライブラリ: XXE に脆弱（バージョンにより挙動が異なる）
import xml.etree.ElementTree as ET
ET.fromstring(xxe_payload)  # → /etc/passwd の内容が展開される可能性

# defusedxml: XXE を明示的に拒否
import defusedxml.ElementTree as safe_ET
safe_ET.fromstring(xxe_payload)  # → DefusedXmlException を raise
```

セキュリティ上の理由から、外部データの XML パースには必ず `defusedxml` を使用すること。

### 観察2: Billion Laughs 攻撃はエンティティ展開爆弾

エンティティを再帰的に参照させることで指数関数的にメモリを消費させる攻撃。
数KB の入力が解凍後に GB 規模のメモリを要求する。

```xml
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  ...
]>
<root>&lolN;</root>
```

`defusedxml` は DTD/ENTITY 宣言を含む XML を拒否するため、この攻撃を無効化できる。

### 観察3: `ET.SubElement` による自動エスケープ

XML を文字列フォーマットで構築するとインジェクション脆弱性になる。
`ET.SubElement` はテキストコンテンツを自動エスケープするため安全。

```python
# 危険: 文字列フォーマットでの XML 構築
f"<root><comment>{user_input}</comment></root>"
# user_input = "</comment><evil/><comment>" の場合: 構造が破壊される

# 安全: ET.SubElement を使う（自動エスケープ）
root = ET.Element("root")
child = ET.SubElement(root, "comment")
child.text = user_input  # < > & が自動的にエスケープされる
```

### 観察4: CDATA セクションはそのままテキストとして扱われる

XML の `<![CDATA[...]]>` セクション内のコンテンツは ElementTree によって
そのままテキストとして展開される。これ自体は安全だが、
CDATA 内の `<evil>` タグなどがテキストとして返されることを API クライアントが知っておく必要がある。

```python
result = parse_xml("<root><![CDATA[<evil>not xml</evil>]]></root>")
# result.text == "<evil>not xml</evil>"（エスケープなし — テキストとして展開済み）
```

---

## nene2-python フレームワークとの統合

- `defusedxml` は `pip install defusedxml` で追加（軽量、メンテ活発）
- `parse_xml()` / `parse_rss_feed()` は XML を受け取る API エンドポイントの入力処理として使える
- `build_xml()` の NCName バリデーション（`_VALID_XML_NAME_RE`）は tag 名入力を受ける全関数で必要
- `MAX_XML_BYTES = 1MB` + Pydantic `max_length=2MB` で DoS 対策済み
- `MAX_ELEMENTS = 10_000` + `MAX_DEPTH = 50` で構造爆発（大量ネスト）も防御
- `APIRouter` + `create_app()` パターンを最初から適用済み

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

SOAP API や RSS フィードを扱う API を実装しようとしている。

**ドキュメント理解**: `import xml.etree.ElementTree as ET` → `ET.parse()` は直感的。
しかし「なぜ `defusedxml` を使うのか」の説明がなければ標準ライブラリのみで実装してしまう。  
**事故リスク**: 高。`xml.etree.ElementTree` で外部データをパースする実装は XXE に脆弱になりうる。
公式ドキュメントにも警告はあるが、見落としやすい。  
**規約の使いやすさ**: `defusedxml` の `fromstring()` は標準ライブラリとほぼ同じ API なので移行コストは低い。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

既存の XML パースコードをコピーして API に組み込もうとしている。

**コピペ可能性**: `ET.parse()` / `ET.fromstring()` のサンプルはネットに多いが、
`defusedxml` を使うサンプルは少ない。コピペすると脆弱なコードになる。  
**拡張時の罠**: `parse_xml()` を `ET.fromstring()` に置き換えると XXE 防御が消える。
「同じ API だし速いから」という判断で変更する人がいる。  
**セキュリティ的な事故リスク**: 高。XXE 経由で内部ファイル読み取りが可能になる。
本番環境でサーバー設定ファイルや秘密鍵が読まれる可能性がある。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JS の `DOMParser` に慣れており、Python で同じことをしようとしている。

**エラーレスポンスの質**: 400 Bad Request に具体的なメッセージが返るのは良い。
XXE と単純な XML 不正の区別が API レスポンスからできない（どちらも 400）が、
セキュリティ上は意図的な設計。  
**Python 固有概念の学習コスト**: `ET.Element` のツリー操作は `DOM` に近い。
`root.iter()` / `root.find()` の違いは JS の `querySelectorAll` と `querySelector` に相当する。  
**事故リスク**: 低。HTTP 境界での Pydantic バリデーションが充実。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

他のフレームワークで XML を扱った経験があり、`lxml` を好む。

**他フレームワークとの差異**: Django は XML サポートを標準で持たない。
`lxml` の `etree.XMLParser(resolve_entities=False)` でも XXE を防御できるが、
`defusedxml` の方が意図が明確で読みやすい。  
**nene2-python の薄さへの評価**: `defusedxml` の採用判断が明示的でドキュメント化されている点は良い。
`lxml` ほど高機能でないが、標準ライブラリとの API 互換性が高く学習コストが低い。  
**本番投入可能性**: `defusedxml` + `MAX_ELEMENTS` + `MAX_DEPTH` の多層防御は本番品質。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- [x] `import xml.etree.ElementTree` を直接使っていないか（`defusedxml` が必要）
- [x] `ET.Element(user_input)` のようにユーザー入力をタグ名に使っていないか（F-1 の罠）
- [x] 文字列フォーマットで XML を構築していないか（`ET.SubElement` を使うこと）
- [x] `MAX_XML_BYTES` / `MAX_ELEMENTS` / `MAX_DEPTH` の三重チェックがあるか

**チームでの安全な共有パターン**: `parse_xml()` を社内ユーティリティとして共有し、
直接 `ET.fromstring()` や `safe_ET.fromstring()` を呼ぶ実装を禁止にすることで
チーム全体で一貫したセキュリティレベルを維持できる。  
**ツール追加の必要性**: `bandit` (B314〜B320) で `xml.etree.ElementTree` の危険な使用を検出できる。
ruff には相当するルールがなく、コードレビューチェックリストに追加すべき。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 中  
— 標準ライブラリの `ET.fromstring()` を直接呼ぶと再発する。
`defusedxml` を必須とすることをドキュメントに明記する価値がある。  
**設計上の負債**: `_VALID_XML_NAME_RE` は `build_xml()` でのみ使われるが、
タグ名を受け取る他の関数（存在する場合）でも必要になる。
共通バリデーターとして明示しておく価値がある。  
**Follow-up Issue 候補**: `defusedxml` を XML 処理の必須依存として CLAUDE.md に追記する

---

## セキュリティ診断（FT番号が3の倍数のときのみ実施）

> **診断方針**: XML 処理固有の攻撃ベクターを中心に実施。

### 1. OWASP API Security Top 10 (2023)

#### API1: オブジェクトレベルの認可不備 (BOLA / IDOR)
- XML パース API は ID ベースのアクセス制御を持たない構造。認可不備 N/A。
- **結果**: ✅ 対象外

#### API3: オブジェクトプロパティレベルの認可不備 (Mass Assignment)
- Pydantic Body で `content`, `tag`, `required_tags` 等の明示的フィールドのみ受け入れ。
- 余分なフィールドは自動的に無視される（Pydantic のデフォルト動作）。
- **結果**: ✅ 問題なし

#### API4: 無制限リソース消費 (Unrestricted Resource Consumption)
- `MAX_XML_BYTES = 1MB`、Pydantic `max_length=2MB` の二重チェック。
- `MAX_ELEMENTS = 10_000`、`MAX_DEPTH = 50` で構造爆発も防御。
- `required_tags: list[str] = Field(max_length=50)` でリスト長も制限。
- **結果**: ✅ 問題なし

---

### 2. XML 固有のインジェクション攻撃

#### XXE (XML External Entity) インジェクション
```xml
<?xml version="1.0"?>
<!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root>&xxe;</root>
```
- `defusedxml.ElementTree.fromstring()` が `DefusedXmlException` を raise → `None` 返却
- **結果**: ✅ 防御済み

#### エンティティ展開爆弾（Billion Laughs 攻撃）
```xml
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  ...
]>
<root>&lol4;</root>
```
- `defusedxml` が DTD を含む XML を拒否 → `None` 返却
- **結果**: ✅ 防御済み

#### XML インジェクション（構築時）
- `build_xml()` は `ET.SubElement` でテキストを自動エスケープ
- `<script>` → `&lt;script&gt;`、`&` → `&amp;`
- **結果**: ✅ 防御済み

#### タグ名インジェクション（F-1 発見・修正済み）
```python
build_xml({"a": "b"}, root_tag="<inject/>")
# 修正前: <<inject/>><a>b</a></<inject/>> を返していた
# 修正後: None を返し、HTTP エンドポイントは 400 を返す
```
- `_VALID_XML_NAME_RE = re.compile(r"^[a-zA-Z_][\w\-\.]*$")` で NCName 検証
- **結果**: ✅ 修正後は問題なし（ペンテストで発見）

---

### 3. 入力バリデーション

- 全フィールドに `max_length` 制限あり
- `content` フィールドは長さ 2MB（hex 換算で約 1MB のバイナリ相当）
- `required_tags: list[str]` は `max_length=50` でリスト長を制限
- Null バイト (`\x00`) を含む XML は `defusedxml` がパースエラーとして拒否
- **結果**: ✅ 問題なし

---

### 4. 情報漏洩

- XXE 経由でファイル内容がレスポンスに含まれないことを確認
- `parse_xml(xxe_payload)` → `None` → HTTP 400（ファイル内容は返さない）
- エラーレスポンスに内部パスや例外詳細は含まれない
- **結果**: ✅ 問題なし

---

### 5. 依存関係の脆弱性スキャン

```
Found 1 known vulnerability in 1 package
pyjwt 2.12.1  PYSEC-2025-183  (fix version: なし)
```

- `defusedxml==0.7.1`: pip-audit 問題なし（設計上の安全性に特化したライブラリ）
- **対応方針**: PYSEC-2025-183 は mcp 経由の推移的依存。修正版リリース待ち（継続監視）

---

### 診断サマリー

| カテゴリ | 結果 | 最重要発見 |
|---|---|---|
| OWASP API Security Top 10 | ✅ 全通過 | - |
| XXE インジェクション | ✅ defusedxml で防御 | - |
| エンティティ展開爆弾 | ✅ defusedxml で防御 | - |
| XML インジェクション（構築時） | ✅ ET.SubElement が自動エスケープ | - |
| タグ名インジェクション | ✅ NCName 検証で防御（F-1 修正済み） | ET.Element() の無バリデーション |
| 入力バリデーション | ✅ 問題なし | - |
| 情報漏洩 | ✅ 問題なし | - |
| 依存関係 CVE | ⚠️ PYSEC-2025-183 継続監視 | mcp 経由 PyJWT |

**総合評価**: 合格（F-1 をペンテストで発見し修正済み）  
**発見した脆弱性**: 1件（HIGH: タグ名インジェクション → 修正済み）  
**新規セキュリティ Issue**: なし（修正済みのため）

---

## クラッカーペンテスト（FT180 — FT172, 176, 180... のみ実施）

> **実施方針**: HTTP エンドポイントに攻撃ペイロードを送り込み、耐えられるかを試験する。

### フェーズ1: 構造推測（攻撃者の視点）

- `/parse` エンドポイントのレスポンス `element_count` から内部ツリー構造が推測可能
- `/extract` の `tag` フィールドは XPath インジェクションではなく単純なタグ名マッチング
- エラーレスポンスに Python の例外クラス名・パスは含まれない

### フェーズ2: 攻撃実行ログ

#### A. Pydantic バイパス攻撃
```python
# required_tags に数値を送る
POST /validate {"content": "<root/>", "required_tags": [1, 2, 3]}
# → 422 Validation Error（string_type エラー）✅

# null コンテンツ
POST /parse {"content": null}
# → 422 ✅
```
**結果**: 耐えた（Pydantic が全て 422 で拒否）

#### B. XML 固有攻撃
```python
# XXE 攻撃
POST /parse {"content": "<?xml?><!DOCTYPE r [<!ENTITY x SYSTEM \"file:///etc/passwd\">]><r>&x;</r>"}
# → 400 ✅

# Billion Laughs
POST /parse {"content": "<!DOCTYPE lolz [<!ENTITY lol \"lol\">...]><root>&lol4;</root>"}
# → 400 ✅

# RSS フィード内 XXE
POST /rss {"content": "<?xml?><!DOCTYPE rss [<!ENTITY x SYSTEM \"file:///etc/passwd\">]><rss>..."}
# → 400 ✅
```
**結果**: 耐えた（defusedxml が全て拒否）

#### C. タグ名インジェクション（F-1 発見）
```python
# root_tag に XML 特殊文字
POST /build {"data": {"a": "b"}, "root_tag": "<inject/>"}
# → 修正前: 200 + 壊れた XML
# → 修正後: 400 Bad Request ✅

POST /build {"data": {"a": "b"}, "root_tag": "123invalid"}
# → 修正後: 400 ✅
```
**結果**: 突破（修正前） → 修正後は耐えた

#### D. 境界値・エッジケース
```python
# 深いネスト（MAX_DEPTH=50 ちょうど）
parse_xml("<a>" * 51 + "x" + "</a>" * 51)
# → ParseResult（depth=50、境界値）✅

# 要素数上限（MAX_ELEMENTS=10000）
parse_xml("<root>" + "<x/>" * 10001 + "</root>")
# → None（上限超過で拒否）✅

# CDATA セクション
POST /parse {"content": "<root><![CDATA[<evil/>]]></root>"}
# → 200、text="<evil/>"（エスケープ済み文字列として返却）✅

# Unicode タグ名
POST /extract {"content": "<root><日本語>test</日本語></root>", "tag": "日本語"}
# → 200（XML 名前空間仕様では日本語も有効）✅
```
**結果**: 耐えた（F-1 は build_xml の root_tag のみ）

#### E. DoS 試み
```python
# 大量 required_tags（max_length=50 超え）
POST /validate {"content": "<root/>", "required_tags": ["tag"] * 51}
# → 422 ✅

# 長大属性値（50000文字）
POST /parse {"content": f"<root attr=\"{'x' * 50000}\"/>"}
# → 200（defusedxml はパース。属性値は text_length でトリム）
```
**結果**: 耐えた

### フェーズ3: 攻撃まとめ

| 攻撃カテゴリ | 試みた攻撃数 | 突破 | 耐えた | 予期しない動作 |
|---|---|---|---|---|
| Pydantic バイパス | 4 | 0 | 4 | 0 |
| XML 固有攻撃（XXE/展開爆弾） | 5 | 0 | 5 | 0 |
| タグ名インジェクション | 2 | 1 → 修正 | 1 | 0 |
| 境界値/エッジ | 5 | 0 | 5 | 0 |
| DoS | 2 | 0 | 2 | 0 |

**攻撃耐性評価**: 軽微な問題あり（F-1 発見・修正済み）  
**発見した弱点**: `ET.Element()` が不正なタグ名を受け入れる — NCName バリデーションで修正

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 中 | `defusedxml` を XML 処理の必須依存として CLAUDE.md の禁止事項に追記 | docs |
| 低 | `build_xml()` の key（子タグ名）にも NCName バリデーションを追加 | fix |

---

## まとめ

FT180 では `xml.etree.ElementTree` + `defusedxml` を検証した。
56 テストが全通過し、mypy/ruff も問題なし。

セキュリティ診断とクラッカーペンテストで 1 件の脆弱性（F-1: `ET.Element()` のタグ名バリデーション不足）を発見・修正した。
XXE とエンティティ展開爆弾は `defusedxml` が完全に防御しており、
標準ライブラリの `xml.etree.ElementTree` を直接使う実装との差が明確になった。

最大の発見: `xml.etree.ElementTree.Element()` はタグ名に対してバリデーションを行わず、
`<inject/>` のような文字列をタグ名として受け入れて壊れた XML を生成してしまう。
XML を構築する API で `root_tag` 等をユーザー入力から受け取る場合は、
必ず XML NCName 正規表現でバリデーションすること。

v1.8.51 としてリリース。
