"""Tests du contrat HTTP versionné."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from gratitude_app.storage import Repository
from gratitude_app.web import GratitudeServer


class ApiTests(unittest.TestCase):
    """Vérifie les frontières nécessaires au futur mobile."""

    def setUp(self) -> None:
        """Lance un serveur HTTP isolé."""
        self.directory = tempfile.TemporaryDirectory()
        self.repository = Repository(Path(self.directory.name) / "gratitude.sqlite3")
        self.server = GratitudeServer(("127.0.0.1", 0), self.repository, "alice")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        """Arrête le serveur de test."""
        self.server.shutdown()
        self.server.server_close()
        self.repository.close()
        self.directory.cleanup()

    def test_api_requires_yunohost_identity(self) -> None:
        """Une API interne refuse une requête sans identité."""
        status, body = self._request("GET", "/api/v1/me")
        self.assertEqual(403, status)
        self.assertIn("Authentification", body["error"])

    def test_message_creation_is_moderated(self) -> None:
        """Un merci API est créé en attente par défaut."""
        entity_id = self._create_entity()
        status, body = self._request("POST", "/api/v1/messages", {"recipient_ids": [entity_id], "body": "Merci pour ton aide aujourd'hui."}, "bob")
        self.assertEqual(201, status)
        self.assertEqual("pending", body["data"]["status"])

    def _create_entity(self) -> int:
        """Crée un destinataire depuis le compte administrateur."""
        status, body = self._request("POST", "/api/v1/entities", {"name": "Équipe terrain", "kind": "team"}, "alice")
        self.assertEqual(201, status)
        return int(body["data"]["id"])

    def _request(self, method: str, path: str, payload: dict[str, object] | None = None, username: str | None = None) -> tuple[int, dict[str, object]]:
        """Exécute une requête JSON avec une identité simulée."""
        content: bytes | None = None if payload is None else json.dumps(payload).encode("utf-8")
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if username is not None:
            headers["X-Remote-User"] = username
        connection = HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request(method, path, content, headers)
        response = connection.getresponse()
        result = json.loads(response.read())
        connection.close()
        return response.status, result
