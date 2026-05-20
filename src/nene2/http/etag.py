"""ETag 生成ユーティリティ。"""

import hashlib
import json


def generate_etag(data: dict[str, object] | list[object] | str | bytes) -> str:
    """データから ETag ヘッダー値を生成する。

    JSON シリアライズ後に MD5 ハッシュを計算し、RFC 9110 形式の弱いエンティティタグ
    （例: "\"abc123...\"")を返す。

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
