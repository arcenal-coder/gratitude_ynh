"""API HTTP versionnée et interface web minimale."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable

from gratitude_app.domain import DomainError, validate_message_draft
from gratitude_app.storage import Repository


class GratitudeServer(HTTPServer):
    """Serveur configuré avec son dépôt et ses règles."""

    def __init__(self, address: tuple[str, int], repository: Repository, admin_username: str, require_moderation: bool = True) -> None:
        super().__init__(address, GratitudeHandler)
        self.repository: Repository = repository
        self.admin_username: str = admin_username
        self.require_moderation: bool = require_moderation


class GratitudeHandler(BaseHTTPRequestHandler):
    """Expose le contrat `/api/v1` et une page d'accueil."""

    server: GratitudeServer

    def do_GET(self) -> None:
        """Traite les ressources en lecture."""
        self._dispatch({"/": self._home, "/api/v1/me": self._me, "/api/v1/entities": self._entities, "/api/v1/messages": self._messages, "/api/v1/challenges": self._challenges})

    def do_POST(self) -> None:
        """Traite les commandes d'écriture."""
        self._dispatch({"/api/v1/entities": self._create_entity, "/api/v1/messages": self._create_message, "/api/v1/challenges": self._create_challenge}, self._dynamic_post)

    def _dispatch(self, routes: dict[str, Callable[[], None]], fallback: Callable[[], None] | None = None) -> None:
        """Exécute une route et normalise ses erreurs."""
        try:
            handler: Callable[[], None] | None = routes.get(self.path)
            if handler is not None:
                handler()
            elif fallback is not None:
                fallback()
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "Route introuvable."})
        except DomainError as error:
            self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": str(error)})
        except PermissionError as error:
            self._json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        except json.JSONDecodeError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "JSON invalide."})
        except ValueError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "Identifiant invalide."})

    def _identity(self) -> dict[str, Any]:
        """Récupère l'identité injectée par le proxy YunoHost."""
        username: str | None = self.headers.get("X-Remote-User")
        if not username:
            raise PermissionError("Authentification YunoHost requise.")
        display_name: str = self.headers.get("X-Remote-Name", username)
        identity: dict[str, Any] = self.server.repository.ensure_user(username, display_name, "member")
        if username == self.server.admin_username and identity["role"] != "admin":
            return self.server.repository.set_user_role(username, "admin")
        return identity

    def _require_admin(self) -> dict[str, Any]:
        """Restreint une action au rôle administrateur."""
        identity: dict[str, Any] = self._identity()
        if identity["role"] != "admin":
            raise PermissionError("Droit administrateur requis.")
        return identity

    def _require_moderator(self) -> dict[str, Any]:
        """Restreint une action aux rôles de modération."""
        identity: dict[str, Any] = self._identity()
        if identity["role"] not in {"admin", "moderator"}:
            raise PermissionError("Droit de modération requis.")
        return identity

    def _payload(self) -> dict[str, Any]:
        """Lit un objet JSON borné à un mégaoctet."""
        length: int = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > 1_000_000:
            raise DomainError("La taille de la requête est invalide.")
        value: object = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise DomainError("Le corps de la requête doit être un objet JSON.")
        return value

    def _home(self) -> None:
        """Sert une interface de démarrage pour les membres connectés."""
        self._identity()
        body: bytes = HOME.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _me(self) -> None:
        """Retourne l'identité courante."""
        self._json(HTTPStatus.OK, {"data": self._identity()})

    def _entities(self) -> None:
        """Liste les destinataires internes."""
        self._identity()
        self._json(HTTPStatus.OK, {"data": self.server.repository.list_entities()})

    def _messages(self) -> None:
        """Liste les mercis du membre connecté."""
        identity: dict[str, Any] = self._identity()
        self._json(HTTPStatus.OK, {"data": self.server.repository.list_messages(identity["username"])})

    def _challenges(self) -> None:
        """Liste les challenges internes."""
        self._identity()
        self._json(HTTPStatus.OK, {"data": self.server.repository.list_challenges()})

    def _create_entity(self) -> None:
        """Ajoute une entité par administration."""
        self._require_admin()
        payload: dict[str, Any] = self._payload()
        entity: dict[str, Any] = self.server.repository.create_entity(str(payload.get("name", "")), str(payload.get("kind", "")), payload.get("owner_username"))
        self._json(HTTPStatus.CREATED, {"data": entity})

    def _create_message(self) -> None:
        """Crée un merci soumis à la règle de modération."""
        identity: dict[str, Any] = self._identity()
        message: dict[str, Any] = self.server.repository.create_message(identity["username"], validate_message_draft(self._payload()), self.server.require_moderation)
        self._json(HTTPStatus.CREATED, {"data": message})

    def _create_challenge(self) -> None:
        """Crée un challenge par administration."""
        self._require_admin()
        payload: dict[str, Any] = self._payload()
        challenge: dict[str, Any] = self.server.repository.create_challenge(str(payload.get("title", "")), str(payload.get("theme", "")), str(payload.get("opens_at", "")), str(payload.get("closes_at", "")))
        self._json(HTTPStatus.CREATED, {"data": challenge})

    def _dynamic_post(self) -> None:
        """Route les commandes de modération versionnées."""
        parts: list[str] = self.path.strip("/").split("/")
        if len(parts) == 5 and parts[:3] == ["api", "v1", "messages"] and parts[4] == "moderation":
            self._moderate(int(parts[3]))
            return
        if len(parts) == 6 and parts[:3] == ["api", "v1", "challenges"]:
            self._challenge_action(int(parts[3]), parts[4], parts[5])
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "Route introuvable."})

    def _challenge_action(self, challenge_id: int, action: str, value: str) -> None:
        """Traite candidature, vote ou clôture d'un challenge."""
        identity: dict[str, Any] = self._identity()
        payload: dict[str, Any] = self._payload()
        if action == "candidates" and value == "create":
            data: dict[str, Any] = self.server.repository.nominate(challenge_id, int(payload.get("entity_id", 0)), identity["username"])
            self._json(HTTPStatus.CREATED, {"data": data})
            return
        if action == "votes" and value == "create":
            self.server.repository.vote(challenge_id, int(payload.get("candidate_id", 0)), identity["username"])
            self._json(HTTPStatus.CREATED, {"data": {"challenge_id": challenge_id}})
            return
        if action == "close" and value == "create":
            moderator: dict[str, Any] = self._require_moderator()
            self._json(HTTPStatus.OK, {"data": self.server.repository.close_challenge(challenge_id, moderator["username"])})
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "Action introuvable."})

    def _moderate(self, message_id: int) -> None:
        """Applique une décision de modération."""
        identity: dict[str, Any] = self._require_moderator()
        payload: dict[str, Any] = self._payload()
        message: dict[str, Any] = self.server.repository.moderate(message_id, identity["username"], str(payload.get("decision", "")), payload.get("reason"))
        self._json(HTTPStatus.OK, {"data": message})

    def _json(self, status: HTTPStatus, content: dict[str, Any]) -> None:
        """Émet une réponse JSON UTF-8."""
        body: bytes = json.dumps(content, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Délègue les journaux HTTP au superviseur système."""
        return None


HOME = """<!doctype html><html lang=\"fr\"><meta charset=\"utf-8\"><title>Gratitude</title><body><main><h1>Gratitude</h1><p>La reconnaissance interne, simplement.</p><p>Votre espace est prêt. L'interface complète est construite sur l'API <code>/api/v1</code>.</p></main></body></html>"""
