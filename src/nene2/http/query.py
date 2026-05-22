"""型付きクエリパラメータ抽出ヘルパー。

FastAPI の Query() 型注釈が使えないコンテキスト（ミドルウェア・共通処理）で
Request オブジェクトからクエリパラメータを型安全に取り出す。
"""

from starlette.requests import Request


def query_string(request: Request, key: str, default: str | None = None) -> str | None:
    """クエリパラメータを文字列として取得する。"""
    return request.query_params.get(key, default)


def query_int(request: Request, key: str, default: int | None = None) -> int | None:
    """クエリパラメータを整数として取得する。変換できない場合は *default* を返す。"""
    raw = request.query_params.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def query_bool(request: Request, key: str, default: bool | None = None) -> bool | None:
    """クエリパラメータを bool として取得する。

    ``"true"`` / ``"1"`` / ``"yes"`` → ``True``、
    ``"false"`` / ``"0"`` / ``"no"`` → ``False``（大文字小文字を問わない）。
    それ以外の値は *default* を返す。
    """
    raw = request.query_params.get(key)
    if raw is None:
        return default
    lower = raw.lower()
    if lower in ("true", "1", "yes"):
        return True
    if lower in ("false", "0", "no"):
        return False
    return default


def query_comma_separated(request: Request, key: str) -> list[str] | None:
    """カンマ区切りのクエリパラメータをリストとして取得する。

    空要素は除外する。パラメータが存在しない場合は ``None`` を返す。

    Example: ``?tags=a,b,c`` → ``["a", "b", "c"]``
    """
    raw = request.query_params.get(key)
    if raw is None:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def query_array(request: Request, key: str) -> list[str] | None:
    """同一キーの複数値をリストとして取得する。

    パラメータが存在しない場合は ``None`` を返す。

    Example: ``?ids=1&ids=2&ids=3`` → ``["1", "2", "3"]``
    """
    values = request.query_params.getlist(key)
    if not values:
        return None
    return values
