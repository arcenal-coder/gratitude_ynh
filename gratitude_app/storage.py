"""Persistance SQLite de Gratitude."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from gratitude_app.domain import DomainError, MessageDraft, MessageStatus, utc_now


class Repository:
    """Accès transactionnel aux données de reconnaissance."""

    def __init__(self, database_path: Path) -> None:
        self.connection: sqlite3.Connection = sqlite3.connect(database_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def close(self) -> None:
        """Ferme la connexion de stockage."""
        self.connection.close()

    def _create_schema(self) -> None:
        """Crée le schéma idempotent."""
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def ensure_user(self, username: str, display_name: str, role: str = "member") -> dict[str, Any]:
        """Synchronise un utilisateur fourni par YunoHost."""
        self.connection.execute("INSERT INTO users(username, display_name, role) VALUES(?, ?, ?) ON CONFLICT(username) DO UPDATE SET display_name=excluded.display_name", (username, display_name, role))
        self.connection.commit()
        return self.user_by_username(username)

    def user_by_username(self, username: str) -> dict[str, Any]:
        """Retourne un utilisateur connu."""
        row: sqlite3.Row | None = self.connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if row is None:
            raise DomainError("Utilisateur introuvable.")
        return dict(row)

    def list_entities(self) -> list[dict[str, Any]]:
        """Liste les destinataires référencés."""
        rows: list[sqlite3.Row] = self.connection.execute("SELECT * FROM entities ORDER BY kind, name").fetchall()
        return [dict(row) for row in rows]

    def ensure_person_entity(self, username: str, display_name: str) -> dict[str, Any]:
        """Garantit qu'un membre connecté peut être choisi comme destinataire."""
        row: sqlite3.Row | None = self.connection.execute("SELECT * FROM entities WHERE kind = 'person' AND owner_username = ?", (username,)).fetchone()
        if row is not None:
            return dict(row)
        return self.create_entity(display_name, "person", username)

    def requires_moderation(self) -> bool:
        """Retourne la règle de publication active de l'organisation."""
        row: sqlite3.Row | None = self.connection.execute("SELECT value FROM settings WHERE name = 'require_moderation'").fetchone()
        return row is None or row["value"] == "true"

    def set_requires_moderation(self, required: bool) -> bool:
        """Enregistre la règle de publication choisie par l'administrateur."""
        value: str = "true" if required else "false"
        self.connection.execute("INSERT INTO settings(name, value) VALUES('require_moderation', ?) ON CONFLICT(name) DO UPDATE SET value=excluded.value", (value,))
        self.connection.commit()
        return self.requires_moderation()

    def add_entity_member(self, entity_id: int, username: str, is_manager: bool) -> None:
        """Associe un membre ou gestionnaire à une entité collective."""
        self.entity_by_id(entity_id)
        self.user_by_username(username)
        self.connection.execute("INSERT INTO entity_members(entity_id, username, is_manager) VALUES(?, ?, ?) ON CONFLICT(entity_id, username) DO UPDATE SET is_manager=excluded.is_manager", (entity_id, username, is_manager))
        self.connection.commit()

    def set_user_role(self, username: str, role: str) -> dict[str, Any]:
        """Attribue un rôle d'administration autorisé."""
        if role not in {"member", "moderator", "admin"}:
            raise DomainError("Rôle invalide.")
        changed: int = self.connection.execute("UPDATE users SET role = ? WHERE username = ?", (role, username)).rowcount
        if changed != 1:
            raise DomainError("Utilisateur introuvable.")
        self.connection.commit()
        return self.user_by_username(username)

    def create_entity(self, name: str, kind: str, owner_username: str | None = None) -> dict[str, Any]:
        """Ajoute une personne ou une entité collective."""
        if kind not in {"person", "team", "service", "client", "contractor"} or not name.strip():
            raise DomainError("Nom ou type d'entité invalide.")
        cursor: sqlite3.Cursor = self.connection.execute("INSERT INTO entities(name, kind, owner_username) VALUES(?, ?, ?)", (name.strip(), kind, owner_username))
        self.connection.commit()
        if owner_username is not None:
            self.add_entity_member(cursor.lastrowid, owner_username, True)
        return self.entity_by_id(cursor.lastrowid)

    def entity_by_id(self, entity_id: int) -> dict[str, Any]:
        """Retourne une entité par son identifiant."""
        row: sqlite3.Row | None = self.connection.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
        if row is None:
            raise DomainError("Destinataire introuvable.")
        return dict(row)

    def create_message(self, author: str, draft: MessageDraft, requires_moderation: bool) -> dict[str, Any]:
        """Enregistre un merci et ses destinataires."""
        self._validate_recipients(draft.recipient_ids)
        status: str = MessageStatus.PENDING if requires_moderation else MessageStatus.APPROVED
        cursor: sqlite3.Cursor = self.connection.execute("INSERT INTO messages(author_username, body, is_anonymous, visibility, strength, challenge_id, status, created_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", (author, draft.body, draft.is_anonymous, draft.visibility, draft.strength, draft.challenge_id, status, utc_now()))
        self.connection.executemany("INSERT INTO message_recipients(message_id, entity_id) VALUES(?, ?)", [(cursor.lastrowid, entity_id) for entity_id in draft.recipient_ids])
        self.connection.commit()
        return self.message_by_id(cursor.lastrowid, author)

    def _validate_recipients(self, entity_ids: tuple[int, ...]) -> None:
        """Vérifie que les destinataires existent."""
        placeholders: str = ",".join("?" for _ in entity_ids)
        count: int = self.connection.execute(f"SELECT COUNT(*) FROM entities WHERE id IN ({placeholders})", entity_ids).fetchone()[0]
        if count != len(entity_ids):
            raise DomainError("Au moins un destinataire est inconnu.")

    def message_by_id(self, message_id: int, viewer: str) -> dict[str, Any]:
        """Retourne un message sérialisé pour son auteur."""
        row: sqlite3.Row | None = self.connection.execute(MESSAGE_QUERY + " WHERE m.id = ? GROUP BY m.id", (viewer, message_id)).fetchone()
        if row is None:
            raise DomainError("Message introuvable.")
        return dict(row)

    def list_messages(self, viewer: str, status: str | None = None) -> list[dict[str, Any]]:
        """Liste les messages accessibles au membre."""
        clause: str = " AND m.status = ?" if status else ""
        params: tuple[object, ...] = (viewer, viewer, viewer, *([status] if status else []))
        access: str = "(m.author_username = ? OR (EXISTS(SELECT 1 FROM entity_members em WHERE em.entity_id = e.id AND em.username = ?) AND m.status = 'approved') OR (m.visibility = 'common' AND m.status = 'approved'))"
        rows: list[sqlite3.Row] = self.connection.execute(MESSAGE_QUERY + " WHERE " + access + clause + " GROUP BY m.id ORDER BY m.created_at DESC", params).fetchall()
        return [dict(row) for row in rows]

    def list_community_messages(self, viewer: str) -> list[dict[str, Any]]:
        """Liste les mercis approuvés mis en lumière dans l'espace commun."""
        rows: list[sqlite3.Row] = self.connection.execute(
            MESSAGE_QUERY + " WHERE m.visibility = 'common' AND m.status = 'approved' GROUP BY m.id ORDER BY m.created_at DESC",
            (viewer,),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_pending_messages(self, viewer: str) -> list[dict[str, Any]]:
        """Liste les mercis nécessitant une décision de modération."""
        rows: list[sqlite3.Row] = self.connection.execute(
            MESSAGE_QUERY + " WHERE m.status = 'pending' GROUP BY m.id ORDER BY m.created_at ASC",
            (viewer,),
        ).fetchall()
        return [dict(row) for row in rows]

    def moderate(self, message_id: int, moderator: str, decision: str, reason: str | None) -> dict[str, Any]:
        """Approuve ou refuse un merci en attente."""
        if decision not in {MessageStatus.APPROVED, MessageStatus.REJECTED}:
            raise DomainError("Décision de modération invalide.")
        if decision == MessageStatus.REJECTED and not reason:
            raise DomainError("Un motif est obligatoire lors d'un refus.")
        changed: int = self.connection.execute("UPDATE messages SET status = ?, moderated_by = ?, moderated_at = ?, moderation_reason = ? WHERE id = ? AND status = ?", (decision, moderator, utc_now(), reason, message_id, MessageStatus.PENDING)).rowcount
        if changed != 1:
            raise DomainError("Ce message n'est plus en attente de modération.")
        self.connection.commit()
        self.audit(moderator, "moderate_message", "message", message_id)
        return self.message_by_id(message_id, moderator)

    def audit(self, actor: str, action: str, resource: str, resource_id: int) -> None:
        """Conserve une trace d'administration horodatée."""
        self.connection.execute("INSERT INTO audit_events(actor, action, resource, resource_id, created_at) VALUES(?, ?, ?, ?, ?)", (actor, action, resource, resource_id, utc_now()))
        self.connection.commit()

    def create_challenge(self, title: str, theme: str, opens_at: str, closes_at: str) -> dict[str, Any]:
        """Crée un challenge interne."""
        if not title.strip() or not theme.strip() or opens_at >= closes_at:
            raise DomainError("Les données du challenge sont invalides.")
        cursor: sqlite3.Cursor = self.connection.execute("INSERT INTO challenges(title, theme, opens_at, closes_at, status) VALUES(?, ?, ?, ?, 'open')", (title.strip(), theme.strip(), opens_at, closes_at))
        self.connection.commit()
        return self.challenge_by_id(cursor.lastrowid)

    def challenge_by_id(self, challenge_id: int) -> dict[str, Any]:
        """Retourne un challenge."""
        row: sqlite3.Row | None = self.connection.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,)).fetchone()
        if row is None:
            raise DomainError("Challenge introuvable.")
        return dict(row)

    def list_challenges(self) -> list[dict[str, Any]]:
        """Liste les challenges."""
        query: str = """SELECT c.*, e.name AS winner_name
        FROM challenges c LEFT JOIN challenge_candidates cc ON cc.id = c.winner_candidate_id
        LEFT JOIN entities e ON e.id = cc.entity_id ORDER BY c.closes_at DESC"""
        return [dict(row) for row in self.connection.execute(query).fetchall()]

    def list_candidates(self, challenge_id: int, username: str) -> list[dict[str, Any]]:
        """Retourne les candidatures et le choix déjà exprimé par le membre."""
        self.challenge_by_id(challenge_id)
        query: str = """SELECT cc.id, cc.challenge_id, cc.entity_id, cc.nominated_by,
        e.name, e.kind, COUNT(cv.username) AS votes,
        EXISTS(SELECT 1 FROM challenge_votes mine WHERE mine.challenge_id = cc.challenge_id
        AND mine.candidate_id = cc.id AND mine.username = ?) AS voted_by_me
        FROM challenge_candidates cc JOIN entities e ON e.id = cc.entity_id
        LEFT JOIN challenge_votes cv ON cv.candidate_id = cc.id
        WHERE cc.challenge_id = ? GROUP BY cc.id ORDER BY votes DESC, e.name ASC"""
        return [dict(row) for row in self.connection.execute(query, (username, challenge_id)).fetchall()]

    def nominate(self, challenge_id: int, entity_id: int, username: str) -> dict[str, Any]:
        """Inscrit une candidature interne à un challenge ouvert."""
        self.entity_by_id(entity_id)
        challenge: dict[str, Any] = self.challenge_by_id(challenge_id)
        self._require_open_challenge(challenge)
        existing: sqlite3.Row | None = self.connection.execute("SELECT id FROM challenge_candidates WHERE challenge_id = ? AND entity_id = ?", (challenge_id, entity_id)).fetchone()
        if existing is not None:
            return {"id": int(existing["id"]), "challenge_id": challenge_id, "entity_id": entity_id}
        cursor: sqlite3.Cursor = self.connection.execute("INSERT INTO challenge_candidates(challenge_id, entity_id, nominated_by) VALUES(?, ?, ?)", (challenge_id, entity_id, username))
        self.connection.commit()
        return {"id": cursor.lastrowid, "challenge_id": challenge_id, "entity_id": entity_id}

    def _require_open_challenge(self, challenge: dict[str, Any]) -> None:
        """Refuse toute participation hors période annoncée."""
        if challenge["status"] != "open":
            raise DomainError("Ce challenge n'accepte plus de candidature.")
        today: str = date.today().isoformat()
        if not challenge["opens_at"] <= today <= challenge["closes_at"]:
            raise DomainError("Ce challenge n'est pas ouvert aux participations aujourd'hui.")

    def vote(self, challenge_id: int, candidate_id: int, username: str) -> None:
        """Enregistre un vote unique par membre et challenge."""
        challenge: dict[str, Any] = self.challenge_by_id(challenge_id)
        self._require_open_challenge(challenge)
        candidate: sqlite3.Row | None = self.connection.execute("SELECT id FROM challenge_candidates WHERE id = ? AND challenge_id = ?", (candidate_id, challenge_id)).fetchone()
        if candidate is None:
            raise DomainError("Candidature introuvable.")
        try:
            self.connection.execute("INSERT INTO challenge_votes(challenge_id, candidate_id, username, created_at) VALUES(?, ?, ?, ?)", (challenge_id, candidate_id, username, utc_now()))
        except sqlite3.IntegrityError as error:
            raise DomainError("Vous avez déjà voté pour ce challenge.") from error
        self.connection.commit()

    def close_challenge(self, challenge_id: int, actor: str) -> dict[str, Any]:
        """Clôture un challenge et désigne le lauréat par majorité."""
        challenge: dict[str, Any] = self.challenge_by_id(challenge_id)
        if challenge["status"] != "open":
            raise DomainError("Ce challenge est déjà clôturé.")
        winner: sqlite3.Row | None = self.connection.execute("SELECT candidate_id, COUNT(*) AS score FROM challenge_votes WHERE challenge_id = ? GROUP BY candidate_id ORDER BY score DESC, candidate_id ASC LIMIT 1", (challenge_id,)).fetchone()
        winner_id: int | None = None if winner is None else int(winner["candidate_id"])
        self.connection.execute("UPDATE challenges SET status = 'closed', winner_candidate_id = ? WHERE id = ?", (winner_id, challenge_id))
        self.connection.commit()
        self.audit(actor, "close_challenge", "challenge", challenge_id)
        return self.challenge_by_id(challenge_id)

    def export_user(self, username: str) -> dict[str, Any]:
        """Produit les données métier associées à un membre."""
        return {"user": self.user_by_username(username), "messages": self.list_messages(username)}


MESSAGE_QUERY = """SELECT m.*, GROUP_CONCAT(e.name, ', ') AS recipients,
CASE WHEN m.is_anonymous = 1 AND m.author_username != ? THEN NULL ELSE m.author_username END AS author
FROM messages m JOIN message_recipients mr ON mr.message_id = m.id
JOIN entities e ON e.id = mr.entity_id"""


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, display_name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'member');
CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS entities (id INTEGER PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, owner_username TEXT REFERENCES users(username));
CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, author_username TEXT NOT NULL REFERENCES users(username), body TEXT NOT NULL, is_anonymous INTEGER NOT NULL, visibility TEXT NOT NULL, strength TEXT, challenge_id INTEGER, status TEXT NOT NULL, created_at TEXT NOT NULL, moderated_by TEXT, moderated_at TEXT, moderation_reason TEXT);
CREATE TABLE IF NOT EXISTS message_recipients (message_id INTEGER NOT NULL REFERENCES messages(id), entity_id INTEGER NOT NULL REFERENCES entities(id), PRIMARY KEY(message_id, entity_id));
CREATE TABLE IF NOT EXISTS entity_members (entity_id INTEGER NOT NULL REFERENCES entities(id), username TEXT NOT NULL REFERENCES users(username), is_manager INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(entity_id, username));
CREATE TABLE IF NOT EXISTS challenges (id INTEGER PRIMARY KEY, title TEXT NOT NULL, theme TEXT NOT NULL, opens_at TEXT NOT NULL, closes_at TEXT NOT NULL, status TEXT NOT NULL, winner_candidate_id INTEGER);
CREATE TABLE IF NOT EXISTS challenge_candidates (id INTEGER PRIMARY KEY, challenge_id INTEGER NOT NULL REFERENCES challenges(id), entity_id INTEGER NOT NULL REFERENCES entities(id), nominated_by TEXT NOT NULL REFERENCES users(username), UNIQUE(challenge_id, entity_id));
CREATE TABLE IF NOT EXISTS challenge_votes (challenge_id INTEGER NOT NULL REFERENCES challenges(id), candidate_id INTEGER NOT NULL REFERENCES challenge_candidates(id), username TEXT NOT NULL REFERENCES users(username), created_at TEXT NOT NULL, UNIQUE(challenge_id, username));
CREATE TABLE IF NOT EXISTS audit_events (id INTEGER PRIMARY KEY, actor TEXT NOT NULL REFERENCES users(username), action TEXT NOT NULL, resource TEXT NOT NULL, resource_id INTEGER NOT NULL, created_at TEXT NOT NULL);
"""
