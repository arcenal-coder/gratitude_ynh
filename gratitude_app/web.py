"""Interface web et API REST de Gratitude."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from gratitude_app.domain import DomainError, validate_message_draft
from gratitude_app.storage import Repository

STATIC_DIRECTORY = Path(__file__).parent / "static"


class GratitudeServer(HTTPServer):
    """Serveur configuré avec son dépôt et ses règles métier."""

    def __init__(self, address: tuple[str, int], repository: Repository, admin_username: str, require_moderation: bool = True) -> None:
        super().__init__(address, GratitudeHandler)
        self.repository: Repository = repository
        self.admin_username: str = admin_username
        self.require_moderation: bool = require_moderation


class GratitudeHandler(BaseHTTPRequestHandler):
    """Expose l'interface française et le contrat mobile `/api/v1`."""

    server: GratitudeServer

    def do_GET(self) -> None:
        """Traite les ressources en lecture."""
        self._dispatch(self._get_routes(), self._dynamic_get)

    def do_POST(self) -> None:
        """Traite les commandes d'écriture."""
        self._dispatch(self._post_routes(), self._dynamic_post)

    def _get_routes(self) -> dict[str, Callable[[], None]]:
        """Déclare les routes HTTP stables."""
        return {
            "/": self._home,
            "/assets/app.css": lambda: self._asset("app.css", "text/css; charset=utf-8"),
            "/assets/app.js": lambda: self._asset("app.js", "application/javascript; charset=utf-8"),
            "/api/v1/me": self._me,
            "/api/v1/dashboard": self._dashboard,
            "/api/v1/entities": self._entities,
            "/api/v1/messages": self._messages,
            "/api/v1/community": self._community,
            "/api/v1/challenges": self._challenges,
            "/api/v1/moderation": self._moderation_queue,
        }

    def _post_routes(self) -> dict[str, Callable[[], None]]:
        """Déclare les commandes HTTP stables."""
        return {
            "/api/v1/entities": self._create_entity,
            "/api/v1/messages": self._create_message,
            "/api/v1/challenges": self._create_challenge,
        }

    def _dispatch(self, routes: dict[str, Callable[[], None]], fallback: Callable[[], None] | None = None) -> None:
        """Exécute une route et normalise ses erreurs attendues."""
        try:
            handler: Callable[[], None] | None = routes.get(self._path())
            if handler is not None:
                handler()
                return
            if fallback is not None:
                fallback()
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "Route introuvable."})
        except DomainError as error:
            self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": str(error)})
        except PermissionError as error:
            self._json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        except json.JSONDecodeError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "JSON invalide."})
        except ValueError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "Identifiant invalide."})

    def _path(self) -> str:
        """Retourne le chemin sans les paramètres de requête."""
        return urlparse(self.path).path

    def _identity(self) -> dict[str, Any]:
        """Récupère l'identité injectée par le proxy YunoHost."""
        username: str | None = self.headers.get("X-Remote-User")
        if not username:
            raise PermissionError("Authentification YunoHost requise.")
        display_name: str = self.headers.get("X-Remote-Name", username)
        identity: dict[str, Any] = self.server.repository.ensure_user(username, display_name, "member")
        self.server.repository.ensure_person_entity(username, display_name)
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
        """Sert l'application monopage pour les membres connectés."""
        self._identity()
        self._text(HTTPStatus.OK, HOME, "text/html; charset=utf-8")

    def _asset(self, name: str, content_type: str) -> None:
        """Sert une ressource statique locale autorisée."""
        content: str = (STATIC_DIRECTORY / name).read_text(encoding="utf-8")
        self._text(HTTPStatus.OK, content, content_type)

    def _me(self) -> None:
        """Retourne l'identité courante."""
        self._json(HTTPStatus.OK, {"data": self._identity()})

    def _dashboard(self) -> None:
        """Retourne les données utiles au premier écran."""
        identity: dict[str, Any] = self._identity()
        messages: list[dict[str, Any]] = self.server.repository.list_messages(identity["username"])
        pending: int = len(self.server.repository.list_pending_messages(identity["username"])) if identity["role"] in {"admin", "moderator"} else 0
        self._json(HTTPStatus.OK, {"data": {"identity": identity, "messages": messages[:4], "challenges": self.server.repository.list_challenges()[:3], "pending_count": pending}})

    def _entities(self) -> None:
        """Liste les destinataires internes."""
        self._identity()
        self._json(HTTPStatus.OK, {"data": self.server.repository.list_entities()})

    def _messages(self) -> None:
        """Liste les mercis accessibles au membre connecté."""
        identity: dict[str, Any] = self._identity()
        self._json(HTTPStatus.OK, {"data": self.server.repository.list_messages(identity["username"])})

    def _community(self) -> None:
        """Liste les messages mis en lumière dans l'espace partagé."""
        identity: dict[str, Any] = self._identity()
        self._json(HTTPStatus.OK, {"data": self.server.repository.list_community_messages(identity["username"])})

    def _challenges(self) -> None:
        """Liste les challenges internes."""
        self._identity()
        self._json(HTTPStatus.OK, {"data": self.server.repository.list_challenges()})

    def _moderation_queue(self) -> None:
        """Expose la file de modération aux rôles habilités."""
        identity: dict[str, Any] = self._require_moderator()
        self._json(HTTPStatus.OK, {"data": self.server.repository.list_pending_messages(identity["username"])})

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

    def _dynamic_get(self) -> None:
        """Route les lectures dépendant d'un identifiant."""
        parts: list[str] = self._path().strip("/").split("/")
        if len(parts) == 5 and parts[:3] == ["api", "v1", "challenges"] and parts[4] == "candidates":
            identity: dict[str, Any] = self._identity()
            self._json(HTTPStatus.OK, {"data": self.server.repository.list_candidates(int(parts[3]), identity["username"])})
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "Route introuvable."})

    def _dynamic_post(self) -> None:
        """Route les commandes de modération et de challenge."""
        parts: list[str] = self._path().strip("/").split("/")
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

    def _text(self, status: HTTPStatus, content: str, content_type: str) -> None:
        """Émet une réponse texte UTF-8."""
        body: bytes = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: HTTPStatus, content: dict[str, Any]) -> None:
        """Émet une réponse JSON UTF-8."""
        self._text(status, json.dumps(content, ensure_ascii=False), "application/json; charset=utf-8")

    def log_message(self, format: str, *args: object) -> None:
        """Délègue les journaux HTTP au superviseur système."""
        return None


HOME = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gratitude</title><link rel="stylesheet" href="assets/app.css"></head>
<body><div id="app" aria-live="polite"><div class="app-loading">Ouverture de votre espace de reconnaissance…</div></div>
<script src="assets/app.js" defer></script></body></html>"""
