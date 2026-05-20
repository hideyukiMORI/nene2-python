"""Tests for LocalMcpServer."""

from nene2.mcp import LocalMcpServer


def _make_server_with_tools() -> LocalMcpServer:
    server = LocalMcpServer("test-server")

    @server.tool("Get data")
    def get_data() -> str:
        return "data"

    @server.tool("Post data")
    def post_data(value: str) -> str:
        return f"posted: {value}"

    return server


def test_list_tools_returns_registered_names() -> None:
    server = _make_server_with_tools()
    tools = server.list_tools()
    assert "get_data" in tools
    assert "post_data" in tools


def test_list_tools_empty_server() -> None:
    server = LocalMcpServer("empty-server")
    assert server.list_tools() == []


def test_list_tools_count() -> None:
    server = _make_server_with_tools()
    assert len(server.list_tools()) == 2


def test_list_tools_returns_list_of_str() -> None:
    server = _make_server_with_tools()
    tools = server.list_tools()
    assert all(isinstance(name, str) for name in tools)


def test_tool_function_still_callable() -> None:
    """tool() デコレーターが関数の呼び出し可能性を壊さない。"""
    server = LocalMcpServer("callable-test")

    @server.tool("Square")
    def square(x: int) -> str:
        return str(x * x)

    assert square(3) == "9"
