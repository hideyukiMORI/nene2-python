# FT90: ファイルアップロード — multipart/form-data バリデーションパターン検証

**日付**: 2026-05-20  
**テーマ**: FastAPI UploadFile + nene2 でのファイルアップロードバリデーション  
**バージョン**: v1.8.30  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft90-file-upload/`

---

## 概要

`UploadFile` を使ったファイルアップロード、コンテントタイプ・サイズバリデーション、
複数ファイル一括アップロード、`RequestSizeLimitMiddleware` との共存を検証。
`setup_middlewares()` のパラメーター名の非自明さと、
FastAPI がコンテントタイプを自動検証しないことが摩擦として発見された。

---

## 実装パターン

### 単一ファイルアップロード + バリデーション

```python
_ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})
_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

@app.post("/files", response_model=FileResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(description="ファイル"),
    description: str = Form(default="", max_length=500),
) -> JSONResponse:
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        return problem_details_response(
            "invalid-content-type", "Invalid Content Type", 415,
            headers={"Accept": ", ".join(sorted(_ALLOWED_IMAGE_TYPES))},
        )
    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        return problem_details_response("file-too-large", "File Too Large", 413, ...)
    ...
```

### nene2 の RequestSizeLimitMiddleware との共存

```python
# ✅ 正しいパラメーター名: max_request_bytes
setup_middlewares(app, max_request_bytes=10 * 1024 * 1024)

# ❌ 間違い（TypeError になる）
setup_middlewares(app, max_request_size=10 * 1024 * 1024)
```

---

## 発見した問題

### 問題1: `setup_middlewares()` のパラメーター名が非自明

`max_request_bytes` という名前は正確だが、
`max_request_size` や `max_body_size` を試みるユーザーが多い。
`TypeError: setup_middlewares() got an unexpected keyword argument 'max_request_size'. Did you mean 'max_request_bytes'?`
というエラーが出るため気付けるが、IDE 補完がないと分かりにくい。

### 問題2: FastAPI は UploadFile のコンテントタイプを自動検証しない

```python
# コンテントタイプを偽って送信しても FastAPI は受け付ける
client.post("/files", files={"file": ("evil.exe", content, "image/jpeg")})
# → content_type="image/jpeg" として処理される（EXE バイナリでも）
```

本番環境では `file.content_type` ヘッダーだけでなく、
ファイルの魔法バイト（magic bytes）を検証する必要があるが、
nene2 ドキュメントにそのパターンが示されていない。

### 問題3: `async def` ハンドラーが必要

`UploadFile.read()` は `await` が必要なため、ハンドラーを `async def` で定義する必要がある。
nene2 の run_in_threadpool パターン（FT76）との組み合わせで注意が必要。

---

## テスト結果（全13件パス）

```
test_upload_valid_jpeg_returns_201                              PASSED
test_upload_png_returns_201                                     PASSED
test_upload_with_description_form_field                         PASSED
test_upload_invalid_content_type_returns_415                    PASSED
test_upload_too_large_returns_413                               PASSED
test_upload_same_content_returns_same_id                        PASSED
test_get_uploaded_file_info                                     PASSED
test_get_nonexistent_file_returns_404                           PASSED
test_list_files_after_upload                                    PASSED
test_batch_upload_multiple_files                                PASSED
test_batch_upload_invalid_type_returns_415                      PASSED
test_friction_upload_file_missing_returns_422                   PASSED
test_friction_content_type_not_validated_by_fastapi             PASSED
```

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F90-1 | `setup_middlewares()` の `max_request_bytes` パラメーター名が非自明（`max_request_size` と間違えやすい） | 低 |
| F90-2 | FastAPI は UploadFile のコンテントタイプを自動検証しない（魔法バイト検証のパターン未文書） | 中 |
| F90-3 | `UploadFile.read()` は `async def` が必要（sync ハンドラーとの混在に注意） | 低 |

---

## 使用感（主観評価）

### 直感性 ★★★★☆

`UploadFile` + `File()` のパターンは直感的。
Form フィールドと同時に送信する場合も `data={"field": "value"}` で簡単。
`problem_details_response(headers=...)` で 415 の `Accept` ヘッダーも付けられた（FT87 の成果）。

### 実害の深刻さ ★★★☆☆

F90-2 はセキュリティ観点で中程度。
コンテントタイプを偽ったファイルアップロードは現実の攻撃手法。
nene2 ドキュメントに魔法バイト検証の例があれば防げる。

### 修正のしやすさ ★★★★★

F90-1: `max_request_bytes` のドキュメントに `max_request_size` との違いを明記するだけ。
F90-2: ドキュメントに魔法バイト検証の例を追加。
F90-3: ドキュメントに `async def` が必要な旨を明記。

### 総合コメント

nene2 の `RequestSizeLimitMiddleware` との共存は問題なし。
`problem_details_response()` を使ったエラー応答（415, 413）もきれいに動く。
FT87 で追加した `headers` パラメーターが早速役立った（415 に `Accept` ヘッダーを付与）。

---

## 推奨アクション

1. **docs**: how-to に「ファイルアップロード」ガイドを追加
   - `UploadFile` + コンテントタイプ・サイズバリデーションのパターン
   - 魔法バイト（magic bytes）検証の例
   - `RequestSizeLimitMiddleware` との組み合わせ（`max_request_bytes` を明示）
2. **docs**: `max_request_bytes` パラメーターに `max_request_size` との混同を防ぐ注記
