# FT275: cmath — 複素数演算 / 極座標変換

**日付**: 2026-05-29
**テーマ**: Python `cmath` モジュールの複素数演算の実装と検証
**セキュリティ診断**: なし（275 % 3 = 2）
**クラッカーペンテスト**: なし（275 % 4 = 3）

---

## 概要

`cmath` は複素数の数学関数を提供する。`math` と異なり**負数の平方根**などを複素数で返す。HTTP API でラップし複素平方根と極座標変換を検証した。複素数の JSON シリアライズ（real/imag 分離）と Infinity ガードが要点。

| API | ユースケース |
|---|---|
| `cmath.sqrt(x)` | 平方根（負数→虚数） |
| `cmath.polar(z)` | 直交→極座標 (radius, phase) |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft275-cmath/`

| 関数 | 概要 |
|---|---|
| `complex_sqrt()` | 実数の平方根を複素数で返す（負数可） |
| `to_polar()` | 直交座標を極座標へ変換 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/cmath/sqrt` | 複素平方根 |
| POST | `/cmath/polar` | 極座標変換 |

---

## 摩擦点

### F-1: `cmath.sqrt(-1)` は `1j`（`math.sqrt` は例外）

**観察**: `math.sqrt(-1)` は `ValueError`、`cmath.sqrt(-1)` は `1j`。負数を扱うなら cmath。逆に実数のみを期待する箇所で cmath を使うと予期せぬ複素数が返る。

**対処**: 複素数を返す用途は cmath。結果を real/imag に分離して JSON 化（複素数はそのままシリアライズ不可）。`sqrt(4)`→`(2,0)`、`sqrt(-1)`→`(0,1)`。

### F-2: 生 JSON の `Infinity` トークンを isfinite で弾く

**観察**: クライアントは標準の JSON エンコーダでは `inf` を送れないが、**生 JSON ボディに `Infinity` トークン**を書くと Python の `json.loads`（FastAPI が使用）が受理し、Pydantic float も既定で inf を通す。inf を cmath に渡すと無意味な結果や nan が伝播する。

**対処**: `math.isfinite` で inf/nan を 422。診断で生 `{"value": Infinity}` を送っても弾けることを確認（実装中に JSON クライアントでは inf を送れない点も判明）。

### F-3: 絶対値の上限

**観察**: 極端に大きな値はオーバーフロー/精度劣化を招く。

**対処**: `abs(value) <= 1e9` で制限。結果は 6 桁丸め。

---

## テスト結果

```
6 passed in 0.30s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

負数の平方根が虚数になるのは新鮮。real/imag 分離で複素数が見える。

**ドキュメント理解**: cmath と math の違いをコメントで明示。
**事故リスク（低）**: 計算のみ。
**規約の使いやすさ**: value → real/imag が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

信号処理や数値計算で使う。複素数の JSON 化（分離）が要点。

**コピペ可能性**: complex_sqrt/to_polar は流用可。
**拡張時の罠**: cmath/math の混同・inf 伝播。
**事故リスク（低）**: isfinite ガード。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JS に複素数型がないのでサーバー側が便利。real/imag のペアで受け取る。

**エラーレスポンスの質**: inf/範囲外は 422。
**Python 固有概念**: 複素数型・極座標。
**事故リスク（低）**: ガードあり。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

FFT・電気回路計算等で使う。Infinity トークンの JSON 受理は盲点になりやすく、isfinite ガードは重要。

**他フレームワークとの差異**: 大規模数値は numpy。標準 cmath は軽量。
**nene2 の薄さへの評価**: isfinite ガード・上限が丁寧。
**事故リスク（低）**: ガードあり。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- 複素数を JSON 化する際 real/imag に分離しているか。
- 生 JSON の Infinity/NaN を isfinite で弾いているか（FT252 json と同系統）。
- cmath/math の使い分け。
- 絶対値・精度の上限。

**チームでの安全なパターン**: 数値入力は isfinite + 範囲検証、複素数は分離シリアライズ。
**事故リスク（低）**: ガードを回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。Infinity ガードは FT252（json）の NaN/Infinity 拒否と一貫。
**初心者でも安全な API 達成度**: isfinite・範囲・分離シリアライズを関数内に固定。
**改善提案**: 数値入力共通の「isfinite + 範囲」バリデータを `nene2` に用意し FT250/252/275 で再利用する。
