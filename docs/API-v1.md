# API Gratitude v1

L'API est disponible sous `/api/v1`. Elle est la frontière stable destinée à l'interface web et à une future application mobile. Les réponses sont des objets JSON contenant `data` en succès ou `error` en échec.

## Authentification

La version web reçoit l'identité depuis le proxy SSO YunoHost dans `X-Remote-User`. Une application mobile ne doit jamais envoyer cet en-tête directement : la prochaine version ajoutera un point d'échange de jetons courts, révocables et liés à un appareil. Cette évolution ne modifiera pas les routes métier ci-dessous.

## Routes disponibles

| Méthode | Route | Rôle | Usage |
| --- | --- | --- | --- |
| `GET` | `/me` | membre | Profil YunoHost synchronisé. |
| `GET`, `POST` | `/entities` | membre, administrateur | Consulter ou créer des personnes, équipes, services, clients ou sous-traitants. |
| `GET`, `POST` | `/messages` | membre | Consulter ses messages accessibles ou soumettre un merci. |
| `POST` | `/messages/{id}/moderation` | administrateur | Approuver ou refuser un message en attente. |
| `GET`, `POST` | `/challenges` | membre, administrateur | Consulter ou créer un challenge. |

## Exemple d'envoi

```json
{
  "recipient_ids": [12],
  "body": "Merci pour ton aide pendant l'intervention.",
  "is_anonymous": false,
  "visibility": "private",
  "strength": "entraide"
}
```

La validation impose au moins un destinataire, un message de 3 à 1200 caractères et une visibilité `private` ou `common`.
