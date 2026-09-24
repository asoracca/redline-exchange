"""Export server-owned OpenAPI for the generated TypeScript contract."""

import json
from pathlib import Path
from exchange.api import create_app
from research_copilot.api import create_app as research_app

Path("web/openapi.json").write_text(json.dumps(create_app().openapi(), indent=2) + "\n")


Path("web/research-openapi.json").write_text(
    json.dumps(research_app().openapi(), indent=2) + "\n"
)
