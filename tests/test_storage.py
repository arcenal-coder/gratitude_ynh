"""Tests isolés de la persistance."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gratitude_app.domain import DomainError, validate_message_draft
from gratitude_app.storage import Repository


class RepositoryTests(unittest.TestCase):
    """Vérifie les scénarios métier persistés."""

    def setUp(self) -> None:
        """Prépare une base temporaire."""
        self.directory = tempfile.TemporaryDirectory()
        self.repository = Repository(Path(self.directory.name) / "gratitude.sqlite3")
        self.repository.ensure_user("alice", "Alice", "admin")
        self.repository.ensure_user("bob", "Bob")
        self.bob = self.repository.create_entity("Bob", "person", "bob")

    def tearDown(self) -> None:
        """Ferme la base temporaire."""
        self.repository.close()
        self.directory.cleanup()

    def test_pending_message_is_saved(self) -> None:
        """Le merci est placé en attente lorsque requis."""
        draft = validate_message_draft({"recipient_ids": [self.bob["id"]], "body": "Merci pour ta disponibilité."})
        message = self.repository.create_message("alice", draft, True)
        self.assertEqual("pending", message["status"])
        self.assertEqual("Bob", message["recipients"])

    def test_rejection_requires_a_reason(self) -> None:
        """La modération trace un motif de refus."""
        draft = validate_message_draft({"recipient_ids": [self.bob["id"]], "body": "Merci pour ta disponibilité."})
        message = self.repository.create_message("alice", draft, True)
        with self.assertRaises(DomainError):
            self.repository.moderate(message["id"], "alice", "rejected", None)

    def test_anonymous_message_hides_author_for_recipient(self) -> None:
        """L'auteur est masqué à l'affichage du destinataire."""
        draft = validate_message_draft({"recipient_ids": [self.bob["id"]], "body": "Merci pour ton écoute.", "is_anonymous": True})
        self.repository.create_message("alice", draft, False)
        messages = self.repository.list_messages("bob")
        self.assertIsNone(messages[0]["author"])

    def test_pending_message_is_hidden_from_recipient(self) -> None:
        """Un destinataire ne voit pas un merci avant approbation."""
        draft = validate_message_draft({"recipient_ids": [self.bob["id"]], "body": "Merci pour ton écoute."})
        self.repository.create_message("alice", draft, True)
        self.assertEqual([], self.repository.list_messages("bob"))

    def test_challenge_accepts_only_one_vote_per_member(self) -> None:
        """Un scrutin empêche le second vote du même membre."""
        challenge = self.repository.create_challenge("Amabilité", "amabilité", "2026-09-01", "2026-09-30")
        candidate = self.repository.nominate(challenge["id"], self.bob["id"], "alice")
        self.repository.vote(challenge["id"], candidate["id"], "alice")
        with self.assertRaises(DomainError):
            self.repository.vote(challenge["id"], candidate["id"], "alice")
