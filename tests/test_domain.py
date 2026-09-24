"""Tests des règles de saisie métier."""

from __future__ import annotations

import unittest

from gratitude_app.domain import DomainError, validate_message_draft


class MessageDraftTests(unittest.TestCase):
    """Vérifie les messages valides et invalides."""

    def test_valid_draft_is_normalized(self) -> None:
        """Un message complet est normalisé."""
        draft = validate_message_draft({"recipient_ids": [1, 2], "body": " Merci pour ton aide ! ", "is_anonymous": True, "visibility": "private", "strength": "entraide"})
        self.assertEqual((1, 2), draft.recipient_ids)
        self.assertEqual("Merci pour ton aide !", draft.body)
        self.assertTrue(draft.is_anonymous)

    def test_duplicate_recipients_are_rejected(self) -> None:
        """Un merci ne peut pas répéter un destinataire."""
        with self.assertRaises(DomainError):
            validate_message_draft({"recipient_ids": [1, 1], "body": "Merci"})

    def test_short_message_is_rejected(self) -> None:
        """Un message trop court ne franchit pas la frontière."""
        with self.assertRaises(DomainError):
            validate_message_draft({"recipient_ids": [1], "body": "ok"})
