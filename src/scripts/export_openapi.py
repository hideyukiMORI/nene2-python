"""Export the FastAPI OpenAPI schema to docs/openapi.yaml.

Usage:
  uv run export-openapi
  uv run python src/scripts/export_openapi.py
"""

import json
import pathlib
import sys

import yaml  # type: ignore[import-untyped]

from example.app import create_app


def main() -> None:
    app = create_app()
    schema = app.openapi()

    output_path = pathlib.Path("docs/openapi.yaml")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.dump(json.loads(json.dumps(schema)), allow_unicode=True))

    sys.stdout.write(f"OpenAPI schema written to {output_path}\n")


if __name__ == "__main__":
    main()
