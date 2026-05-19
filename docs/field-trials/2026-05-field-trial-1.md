# Field Trial 1 — lunchlog: git+ インストールからの新規プロジェクト構築

## Date

2026-05-19

## Baseline

- nene2-python v1.0.0 (`uv add git+https://github.com/hideyukiMORI/nene2-python.git`)
- Python 3.14.5（uv managed）
- プロジェクト: **lunchlog** — ランチ記録 JSON API
- エンティティ: `Lunch`（title, rating, price）— 5 エンドポイント（CRUD）
- InMemory リポジトリ使用（SQLite 接続なし）

## Goal

`git clone` ではなく `uv add git+...` から新規プロジェクトを構築し、
ドキュメントだけを頼りに CRUD API が動くまでの摩擦箇所を記録する。

---

## Steps Taken

### 1. プロジェクト初期化・インストール

```bash
mkdir nene2-ft1-lunchlog && cd nene2-ft1-lunchlog
uv init --name lunchlog --no-workspace
uv add "nene2-python @ git+https://github.com/hideyukiMORI/nene2-python.git"
```

→ インストール自体は成功。43 パッケージ解決。

**Finding (F-1)**: ドキュメント（getting-started.md）は `git clone` と `uv sync` の手順のみ。
`uv add git+...` で外部依存として使う方法が一切記載されていない。
「自分のプロジェクトで nene2 を使う」ケースが想定されていない。

### 2. パッケージの公開 API 確認

```python
import nene2; print(dir(nene2))
# → 基本属性のみ。何もエクスポートされていない
```

**Finding (F-2)**: `nene2/__init__.py` が空でサブモジュールを直接インポートするしかないが、
何が使えるかの一覧がない。`from nene2.http import ...` など個別パスは
`docs/reference/framework-modules.md` に書いてあるが、新規ユーザーはそこに辿り着けない。

### 3. Entity / Repository / UseCase の実装

チュートリアル（`docs/tutorials/first-domain.md`）を参照しながら実装。

**Finding なし**: このレイヤーはドキュメントが明確で迷わなかった。
`@dataclass(frozen=True, slots=True)` パターン、ABC、UseCase の `execute()` 署名、
すべてチュートリアル通りに書けた。

### 4. 例外ハンドラーの実装

`ErrorHandlerMiddleware` にドメイン例外を登録しようとした。

**Finding (F-3)**: `DomainExceptionHandlerProtocol` の `handles()` / `handle()` シグネチャが
ドキュメントに記載なし。`docs/reference/framework-modules.md` には「登録できる」とだけ書いてある。
venv に入った `domain_exception.py` を読んで判明した。

```python
class LunchNotFoundExceptionHandler:
    def handles(self, exc: Exception) -> bool: ...
    def handle(self, exc: Exception) -> Response: ...
```

### 5. アプリケーションファクトリの組み立て

`create_app()` 相当を自分で書く必要があった。

**Finding (F-4)**: ミドルウェアスタック全体の組み立てパターンが一切ドキュメント化されていない。
`src/example/app.py` はインストールパッケージに含まれないため参照できない。
「外から使うユーザー向けの app.py 例」が必要。

**Finding (F-5)**: `ErrorHandlerMiddleware` の引数（`debug`, `domain_handlers`）が
ドキュメントに記載なし。また Starlette の `add_middleware` が逆順適用されるという
仕様もどこにも説明がない（後に追加したものが外側になる）。

**Finding (F-6)**: `RequestSizeLimitMiddleware` の引数名が `max_bytes` だが、
設定クラスの属性名は `max_body_size`。ドキュメントには環境変数名（`MAX_BODY_SIZE`）しか書いていない。
また `ThrottleMiddleware` には `enabled` パラメータがなく、
`if settings.throttle_enabled:` で条件分岐する必要があるが、そのパターンが示されていない。

初回の `add_middleware` 呼び出しで `TypeError` が発生し、venv ソースを読んで解決した。

### 6. 動作確認

全 CRUD を TestClient で検証。すべてのエンドポイントが期待通りに動作した。

**Finding (F-7)**: Pydantic `BaseModel` のバリデーションエラー（422）が
nene2 の RFC 9457 Problem Details 形式ではなく FastAPI ネイティブ形式で返される。

```json
// 実際の 422 レスポンス（FastAPI ネイティブ）
{"detail": [{"type": "less_than_equal", "loc": [...], "msg": "..."}]}

// API リファレンスが示す期待形式
{"type": "https://nene2.dev/problems/validation-failed", "status": 422, ...}
```

ドキュメントには「422 → validation-failed」と書いてあるが、
これは `ValidationException` を手動で投げた場合のみ。
`BaseModel` の自動バリデーションには適用されない。

---

## Results

| シナリオ | 期待 | 実際 | 状態 |
|---|---|---|---|
| git+ インストール | 成功 | ✓ | Pass |
| Entity / Repository / UseCase 実装 | ドキュメント通りに書ける | ✓ | Pass |
| 全 CRUD 動作 | 5エンドポイントすべて動く | ✓ | Pass |
| 404 Problem Details | `LunchNotFoundException` → 404 | ✓ | Pass |
| 422 Problem Details | nene2 形式で返る | ✗ FastAPI ネイティブ形式 | F-7 |
| ミドルウェア組み立て | ドキュメントで分かる | ✗ venv を読まないと分からない | F-4, F-5, F-6 |

---

## Friction Summary

| ID | 箇所 | 深刻度 | 種別 |
|---|---|---|---|
| F-1 | `git+` インストールのガイドがない | 高 | ドキュメント欠如 |
| F-2 | `import nene2` で何も見えない | 中 | ドキュメント欠如 |
| F-3 | `DomainExceptionHandlerProtocol` のシグネチャが未記載 | 高 | ドキュメント欠如 |
| F-4 | ミドルウェアスタック組み立てパターンが未記載 | 高 | ドキュメント欠如 |
| F-5 | `ErrorHandlerMiddleware` 引数 / `add_middleware` 逆順ルールが未記載 | 高 | ドキュメント欠如 |
| F-6 | ミドルウェア引数名と環境変数名の不一致、条件分岐パターン未記載 | 中 | ドキュメント欠如 + 設計 |
| F-7 | `BaseModel` 422 エラーが Problem Details 形式にならない | 高 | 機能改善 |

---

## Overall Impression

Entity → Repository → UseCase の実装パターンはチュートリアルを読んで**迷わず書けた**。
ここはドキュメントが明確で摩擦がなく、フレームワークのコアは良好。

摩擦のほぼすべては「外部から使うユーザー向けのアプリ組み立てガイドがない」という一点に集約される。
`src/example/app.py` がパッケージから除外された今、その内容を参照できる場所がどこにもない。
**ミドルウェアスタックの組み立て方を示す How-to ページ一枚が最大の改善**になる。

F-7（Pydantic 422 の形式不一致）は機能改善が必要で、ドキュメントで言い訳するより
FastAPI の exception handler を上書きして一貫させる方が正しい。

---

## Follow-up Issues

- [ ] docs: `uv add git+...` による新規プロジェクト作成ガイドを追加（F-1）
- [ ] docs: `DomainExceptionHandlerProtocol` の実装例をリファレンスに追記（F-3）
- [ ] docs/howto: ミドルウェアスタック組み立てガイド（`create_app()` 例付き）を追加（F-4, F-5, F-6）
- [ ] feat: FastAPI の `RequestValidationError` を nene2 Problem Details に変換（F-7）
