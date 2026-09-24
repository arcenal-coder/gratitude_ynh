# État du projet Gratitude

**Mis à jour :** 24 septembre 2026  
**Branche :** `main`
**Objectif :** application propriétaire de reconnaissance interne installable sur YunoHost, avec API mobile future.

## Décisions actives

- Application autonome, sans connexion à Listen Leon, sans QR code ni accès public.
- Authentification YunoHost par en-tête d'identité injecté par le proxy SSO.
- Python standard library et SQLite pour ne dépendre d'aucun paquet à installer.
- API REST versionnée sous `/api/v1`; les clients mobiles futurs réutiliseront ce contrat.
- Modération préalable par défaut, avec réglage de publication immédiate prévu.

## État observé

- Le CDC v0.3 est approuvé pour lancement et conservé dans `docs/CDC-gratitude-yunohost-v0.1.md`.
- La version 0.2 fournit le domaine Python, SQLite, l'API `/api/v1`, le socle SSO par proxy et une interface web mobile : accueil, envoi, murs, challenges, candidatures, vote et modération.
- Les routes API, l'interface et les règles de saisie sont couvertes par douze tests unitaires et HTTP locaux.
- Les campagnes à révélation différée, notifications email, forces administrables, export/anonymisation et réglages de publication immédiate restent à réaliser avant conformité complète au CDC v0.3.

## Validation prévue

1. `bash -n scripts/_common.sh scripts/install scripts/remove scripts/upgrade scripts/backup scripts/restore` : réussi.
2. Lecture TOML, `python3 -m compileall -q gratitude_app tests` : réussie.
3. `python3 -m unittest discover -s tests -v` : 12 tests réussis, avec permission locale pour les sockets HTTP.
4. `git diff --check` : réussi.
