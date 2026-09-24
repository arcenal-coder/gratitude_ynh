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

    def test_home_serves_the_complete_web_interface(self) -> None:
        """La page membre charge les ressources de l'interface."""
        connection = HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request("GET", "/", headers={"X-Remote-User": "alice"})
        response = connection.getresponse()
        page = response.read().decode("utf-8")
        connection.close()
        self.assertEqual(200, response.status)
        self.assertIn("assets/app.css", page)
        self.assertIn("assets/app.js", page)

    def test_static_interface_assets_are_available(self) -> None:
        """Les fichiers nécessaires à l'application monopage sont livrés."""
        for path, content_type in (("/assets/app.css", "text/css"), ("/assets/app.js", "application/javascript")):
            connection = HTTPConnection("127.0.0.1", self.server.server_port)
            connection.request("GET", path)
            response = connection.getresponse()
            content = response.read().decode("utf-8")
            connection.close()
            self.assertEqual(200, response.status)
            self.assertIn(content_type, response.getheader("Content-Type"))
            self.assertGreater(len(content), 500)

    def test_challenge_candidates_show_votes(self) -> None:
        """Le parcours challenge fournit les candidatures au membre connecté."""
        entity_id = self._create_entity()
        status, body = self._request("POST", "/api/v1/challenges", {"title": "Amabilité", "theme": "amabilité", "opens_at": "2026-09-01", "closes_at": "2026-10-01"}, "alice")
        self.assertEqual(201, status)
        challenge_id = body["data"]["id"]
        status, _ = self._request("POST", f"/api/v1/challenges/{challenge_id}/candidates/create", {"entity_id": entity_id}, "bob")
        self.assertEqual(201, status)
        status, body = self._request("GET", f"/api/v1/challenges/{challenge_id}/candidates", username="bob")
        self.assertEqual(200, status)
        self.assertEqual("Équipe terrain", body["data"][0]["name"])

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
