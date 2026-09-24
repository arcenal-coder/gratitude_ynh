"""Règles métier indépendantes des transports HTTP et du stockage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class DomainError(ValueError):
    """Erreur de règle métier exposable au client."""


class MessageStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class EntityKind(StrEnum):
    PERSON = "person"
    TEAM = "team"
    SERVICE = "service"
    CLIENT = "client"
    CONTRACTOR = "contractor"


@dataclass(frozen=True)
class MessageDraft:
    recipient_ids: tuple[int, ...]
    body: str
    is_anonymous: bool
    visibility: str
    strength: str | None
    challenge_id: int | None


def validate_message_draft(payload: object) -> MessageDraft:
    """Valide les données d'envoi à la frontière HTTP."""
    if not isinstance(payload, dict):
        raise DomainError("Le corps de la requête doit être un objet JSON.")
    recipients: object = payload.get("recipient_ids")
    body: object = payload.get("body")
    if not isinstance(recipients, list) or not all(isinstance(item, int) for item in recipients):
        raise DomainError("recipient_ids doit contenir au moins un identifiant numérique.")
    if not recipients or len(set(recipients)) != len(recipients):
        raise DomainError("Les destinataires doivent être uniques et non vides.")
    if not isinstance(body, str) or not 3 <= len(body.strip()) <= 1200:
        raise DomainError("Le message doit contenir entre 3 et 1200 caractères.")
    return MessageDraft(tuple(recipients), body.strip(), bool(payload.get("is_anonymous", False)), _visibility(payload), _optional_text(payload, "strength"), _optional_int(payload, "challenge_id"))


def _visibility(payload: dict[object, object]) -> str:
    """Normalise la portée demandée."""
    value: object = payload.get("visibility", "private")
    if value not in {"private", "common"}:
        raise DomainError("La visibilité doit être private ou common.")
    return str(value)


def _optional_text(payload: dict[object, object], name: str) -> str | None:
    """Lit un texte facultatif borné."""
    value: object = payload.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 80:
        raise DomainError(f"{name} doit être un texte de 1 à 80 caractères.")
    return value.strip()


def _optional_int(payload: dict[object, object], name: str) -> int | None:
    """Lit un entier facultatif strictement positif."""
    value: object = payload.get(name)
    if value is None:
        return None
    if not isinstance(value, int) or value < 1:
        raise DomainError(f"{name} doit être un entier strictement positif.")
    return value


def utc_now() -> str:
    """Retourne un horodatage UTC ISO-8601."""
    return datetime.now(UTC).isoformat()
