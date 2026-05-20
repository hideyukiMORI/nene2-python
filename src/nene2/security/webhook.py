"""Webhook HMAC-SHA256 署名検証ユーティリティ."""

import hashlib
import hmac


def verify_hmac_signature(
    body: bytes,
    secret: str,
    signature: str,
    *,
    prefix: str = "",
) -> bool:
    """Webhook の HMAC-SHA256 署名を timing-safe に検証する。

    GitHub 方式 (prefix="sha256=") と Stripe 方式 (prefix="") の両方に対応。

    Args:
        body: 検証する生リクエストボディ。
        secret: 共有シークレット文字列。
        signature: 検証対象の署名文字列（prefix を含む場合も可）。
        prefix: 署名文字列のプレフィックス（例: "sha256="）。

    Returns:
        署名が一致すれば True、不一致なら False。
    """
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    expected = prefix + digest
    return hmac.compare_digest(expected, signature)
