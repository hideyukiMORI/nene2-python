"""Entry point: python -m example.mcp  (or  python -m example)"""

from .mcp import create_mcp_server

if __name__ == "__main__":
    create_mcp_server().run()
