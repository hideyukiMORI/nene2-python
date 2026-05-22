"""ETag 生成・条件付きリクエスト評価ユーティリティ。"""

import hashlib
import json

from starlette.requests import Request
from starlette.responses import Response

from nene2.http.problem_details import problem_details_response


def generate_etag(data: dict[str, object] | list[object] | str | bytes) -> str:
    """データから ETag ヘッダー値を生成する。

    JSON シリアライズ後に MD5 ハッシュを計算し、RFC 9110 形式の弱いエンティティタグ
    （例: ``"abc123..."``）を返す。

    暗号セキュリティ用途ではなく、コンテンツの同一性チェックに使用する。
    """
    if isinstance(data, bytes):
        raw = data
    elif isinstance(data, str):
        raw = data.encode()
    else:
        raw = json.dumps(data, sort_keys=True, ensure_ascii=False).encode()

    digest = hashlib.md5(raw, usedforsecurity=False).hexdigest()  # noqa: S324
    return f'"{digest}"'


def check_not_modified(
    request: Request,
    etag: str,
    last_modified: str = "",
) -> Response | None:
    """``If-None-Match`` / ``If-Modified-Since`` を評価し、304 を返すべき場合は Response を返す。

    GET ハンドラーの冒頭で呼び出す。None が返った場合は通常の 200 レスポンスを返す。

    Args:
        request: Starlette の Request オブジェクト。
        etag: 現リソースの ETag（サラウンドダブルクォート形式、例: ``"abc123"``）。
        last_modified: ISO 8601 タイムスタンプ文字列（例: ``"2026-05-20T12:00:00Z"``）。
            省略すると ``If-Modified-Since`` の評価をスキップする。

    Returns:
        クライアントがキャッシュを持っている場合は 304 Response。
        そうでない場合は None（通常レスポンスの生成を続行）。

    Example::

        etag = generate_etag(note)
        if r := check_not_modified(request, etag, note.updated_at):
            return r
        return JSONResponse(note, headers={"ETag": etag})
    """
    if_none_match = request.headers.get("if-none-match", "")
    if if_none_match and if_none_match == etag:
        return _not_modified_response(etag, last_modified)

    if last_modified:
        if_modified_since = request.headers.get("if-modified-since", "")
        if if_modified_since and if_modified_since >= last_modified:
            return _not_modified_response(etag, last_modified)

    return None


def check_precondition(
    request: Request,
    current_etag: str,
    *,
    require: bool = True,
) -> Response | None:
    """``If-Match`` を評価し、412/428 を返すべき場合は Response を返す。

    PUT / PATCH / DELETE ハンドラーの冒頭で呼び出す（楽観的ロック）。
    None が返った場合は書き込みを続行してよい。

    Args:
        request: Starlette の Request オブジェクト。
        current_etag: 現リソースの ETag（サラウンドダブルクォート形式、例: ``"v3"``）。
        require: True（デフォルト）のとき、``If-Match`` ヘッダーが存在しない場合に 428 を返す。
            False のとき、ヘッダーが存在しない場合は通過する。

    Returns:
        412 Precondition Failed、428 Precondition Required のいずれか。
        条件が通れば None。

    Example::

        etag = generate_etag(note)
        if r := check_precondition(request, etag):
            return r
        # safe to update
    """
    if_match = request.headers.get("if-match", "")

    if not if_match:
        if not require:
            return None
        return problem_details_response(
            "precondition-required",
            "Precondition Required",
            428,
            "If-Match header is required. Fetch the current ETag and retry.",
        )

    if if_match == "*":
        return None

    if if_match == current_etag:
        return None

    return problem_details_response(
        "precondition-failed",
        "Precondition Failed",
        412,
        "The supplied ETag does not match the current resource version."
        " Fetch the latest ETag and retry.",
    )


def _not_modified_response(etag: str, last_modified: str) -> Response:
    headers = {"ETag": etag}
    if last_modified:
        headers["Last-Modified"] = last_modified
    return Response(status_code=304, headers=headers)
