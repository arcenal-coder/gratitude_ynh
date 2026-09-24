"""Point d'entrée du service Gratitude."""

from __future__ import annotations

import os
from pathlib import Path

from gratitude_app.storage import Repository
from gratitude_app.web import GratitudeServer


def environment_path(name: str, default: str) -> Path:
    """Lit un chemin de configuration non vide."""
    return Path(os.environ.get(name, default))


def main() -> None:
    """Démarre le serveur HTTP supervisé par systemd."""
    repository: Repository = Repository(environment_path("GRATITUDE_DATABASE", "/var/lib/gratitude/gratitude.sqlite3"))
    admin: str = os.environ.get("GRATITUDE_ADMIN", "admin")
    port: int = int(os.environ.get("GRATITUDE_PORT", "8080"))
    server: GratitudeServer = GratitudeServer(("127.0.0.1", port), repository, admin)
    try:
        server.serve_forever()
    finally:
        repository.close()


if __name__ == "__main__":
    main()
