# Cahier des charges — Application propriétaire de gratitude, auto-hébergée

**Version :** 0.3 — brouillon de cadrage enrichi  
**Date :** 24 septembre 2026  
**Statut :** approuvé pour lancement de la construction le 24 septembre 2026  
**Évolutions v0.3 :** modèle de reconnaissance 360° interne, destinataires individuels ou collectifs, mur personnel, coaching de rédaction et cartographie des forces ; QR code et avis en ligne exclus.

## 1. Intention

Créer une application propriétaire, autonome et auto-hébergée, installable depuis l'administration YunoHost, qui aide une organisation à faire circuler des messages de reconnaissance. L'expérience s'inspire du principe fonctionnel d'un « mur de gratitude » : écrire un merci, le remettre à son destinataire, et conserver une trace positive consultable dans la durée.

L'application est un produit indépendant. Elle ne réutilise ni la marque **Listen Leon**, ni son code, ses textes, ses illustrations, ses données ou son identité visuelle. Elle ne se connecte pas à Listen Leon et n'utilise ni son API, ni ses comptes, ni ses données, ni aucun service externe de cette société.

## 2. Résultat de la première version

Une organisation installe l'application sur son instance YunoHost. Ses membres, connectés avec leur compte YunoHost, peuvent remercier une personne, une équipe ou un service. Les destinataires appartiennent au référentiel interne : personnel, sous-traitants, clients disposant d'un compte, et services. Chaque destinataire dispose d'un espace personnel ou collectif pour relire les mercis reçus. Un administrateur pilote les règles, la modération et les statistiques agrégées.

Nom de travail : **Gratitude**. Le nom final, l'icône et les textes de présentation seront créés pour ce produit.

## 3. Périmètre inclus — MVP

### Rôles

| Rôle | Capacités |
| --- | --- |
| Membre | Se connecter avec YunoHost, rédiger un merci, choisir une personne ou une entité interne, consulter ses mercis reçus et envoyés, signaler un contenu. |
| Modérateur | Consulter la file de modération, approuver, refuser avec motif interne, masquer et traiter les signalements. |
| Administrateur | Gérer les réglages, les modérateurs, les campagnes, les exports et les données de l'organisation. |

### Fonctions

1. **Connexion et comptes** — intégration au SSO/LDAP YunoHost ; aucun mot de passe local.
2. **Référentiel de reconnaissance** — annuaire interne d'individus et d'entités collectives : personnel, sous-traitants, clients dotés d'un compte, équipes et services. Les entités collectives disposent de membres et d'un ou plusieurs gestionnaires désignés.
3. **Écrire un merci** — destinataire individuel ou collectif, message, option « signé » ou « anonyme », aperçu et confirmation. Un assistant de rédaction facultatif encourage un message précis, bienveillant et utile, sans transmettre son contenu à un service tiers.
4. **Recevoir et relire** — mur personnel ou collectif avec filtre par période, expéditeur quand le message est signé, et état lu/non lu.
5. **Mettre en lumière** — le destinataire ou un modérateur peut proposer un merci autorisé au mur commun ; le mur commun ne publie jamais automatiquement un message privé.
6. **Valoriser les forces** — les messages reçus peuvent être associés à des forces ou qualités choisies dans un référentiel administrable (entraide, sécurité, fiabilité, amabilité, etc.). Chaque membre consulte sa synthèse personnelle ; aucun classement individuel n'est public par défaut.
7. **Modération et signalement** — validation préalable obligatoire au lancement ; réglage administrateur pour passer ultérieurement à la publication immédiate ; traçabilité de toute décision ; signalement disponible aux membres.
8. **Notifications** — notification dans l'application ; email optionnel via le serveur de messagerie YunoHost pour un message reçu ou approuvé.
9. **Campagne ponctuelle** — création d'une période de collecte avec date d'ouverture et de révélation ; les messages restent invisibles des destinataires jusqu'à la révélation. Cette fonction reprend le mécanisme de « temps fort » sans impression de cartes dans le MVP.
10. **Challenges participatifs** — l'administrateur crée un challenge tel que « amabilité » ou « sécurité », précise son objectif, sa période, ses règles et ses critères de participation. Les membres votent parmi les participants ou propositions éligibles. À la clôture, l'application désigne et met en avant le ou les lauréats par un portrait et une récompense virtuelle.
11. **Pilotage** — tableau de bord agrégé : volume de messages, participants, messages en attente, activité par période, forces reconnues et suivi des challenges. Aucune lecture des messages privés dans les statistiques.
12. **Protection des données** — durée de conservation configurable, export des données d'un membre, suppression/anonymisation selon les règles de l'organisation, journal d'administration.

## 4. Hors périmètre de la première version

- Impression et expédition de cartes physiques.
- Formation, contenus pédagogiques, quiz de confiance ou réseau social généraliste.
- Import automatique depuis un SIRH, Microsoft 365, Google Workspace ou Slack.
- Application mobile native ; l'interface web reste adaptée au mobile.
- QR code, lien d'accès public ou saisie de messages sans compte YunoHost.
- Publication automatique d'avis en ligne ou intégration à une plateforme d'avis externe.
- Analyse externe ou automatisée des messages par intelligence artificielle ; l'assistant de rédaction et les forces reposent sur des règles locales et contrôlables.
- Messagerie privée bidirectionnelle.

## 5. Interface et navigation

L'interface doit être chaleureuse, sobre et inclusive ; elle ne reproduit pas le site de référence. Elle est conçue d'abord pour le web mobile, puis pour ordinateur.

| Écran / menu | Objectif et action principale |
| --- | --- |
| Accueil | Voir ses derniers mercis et envoyer un merci. |
| Envoyer un merci | Choisir une personne, une équipe ou un service ; écrire, sélectionner la signature et soumettre. |
| Mon mur | Basculer entre reçus et envoyés ; filtrer, relire et consulter ses forces reconnues. |
| Mur commun | Consulter les messages mis en lumière pour l'organisation. |
| Campagnes | Participer à la campagne ouverte ; connaître sa date de révélation. |
| Challenges | Découvrir les challenges ouverts, proposer ou soutenir une participation, voter et consulter les lauréats. |
| Administration | Gérer modération, règles, campagnes, utilisateurs et indicateurs. |

États obligatoires : chargement, liste vide, confirmation d'envoi, message en attente de modération, refus de droit, erreur récupérable, succès de révélation de campagne et absence de forces encore identifiées.

## 6. Parcours prioritaires

### P-01 — Remercier un collègue

1. Le membre ouvre « Envoyer un merci ».
2. Il choisit une personne, une équipe ou un service du référentiel interne, saisit un message et choisit signé ou anonyme.
3. Il confirme après aperçu.
4. Le système enregistre le message puis l'envoie en modération ou le publie selon le réglage.
5. Le membre voit une confirmation et retrouve l'envoi dans « Mon mur ».

### P-02 — Recevoir un merci

1. Un message est publié ou la campagne est révélée.
2. Le destinataire reçoit une notification interne, et un email si activé.
3. Il ouvre « Mon mur », consulte le message et le marque lu.

### P-03 — Modérer un message

1. Le modérateur ouvre la file d'attente.
2. Il approuve ou refuse un message, avec un motif interne obligatoire en cas de refus.
3. La décision et son auteur sont journalisés ; les personnes concernées reçoivent l'information adaptée à leur rôle.

### P-04 — Lancer une campagne à révélation différée

1. L'administrateur définit le titre, les dates et la règle de signature.
2. Les membres autorisés déposent leurs messages pendant la collecte.
3. À la date choisie, l'administrateur déclenche ou le système effectue la révélation.
4. Les destinataires reçoivent l'ensemble de leurs mercis de campagne.

### P-05 — Organiser un challenge et élire un lauréat

1. L'administrateur crée un challenge : thème, explication, dates, participants concernés, mode de candidature et nombre de lauréats.
2. Les membres consultent les candidatures ou propositions éligibles et votent une fois, selon les règles affichées.
3. À la clôture, l'application calcule le résultat, conserve la trace du scrutin et affiche le portrait du lauréat avec sa récompense virtuelle.
4. L'administrateur peut publier un message de félicitations sur le mur commun.

## 7. Exigences YunoHost et techniques

- Paquet YunoHost privé, stocké dans le dépôt choisi par le commanditaire, utilisant le format YunoHost courant avec `manifest.toml`.
- Installation sur domaine racine ou sous-chemin, au moins une instance par organisation ; choix à confirmer pour le multi-instance.
- Authentification YunoHost SSO/LDAP ; l'accès est exclusivement réservé aux membres connectés de l'instance, sans lien ou QR code public.
- Espace unique partagé par tous les membres autorisés ; les groupes YunoHost ne servent pas à cloisonner les espaces au MVP.
- Service démarré, supervisé et redémarrable ; journalisation exploitable par l'administrateur.
- Installation, mise à niveau, suppression, sauvegarde et restauration prises en charge par le paquet.
- Base de données et secrets provisionnés sans saisie technique inutile ; aucune donnée sensible dans le dépôt.
- Interface en français au lancement ; architecture prête pour l'anglais.
- Respect des bonnes pratiques d'accessibilité : navigation clavier, contrastes, libellés explicites et alternatives textuelles.
- API REST versionnée sous `/api/v1`, servant l'interface web et une future application mobile ; l'authentification mobile par jeton révocable sera ajoutée sans modifier les routes métier.

## 8. Données et règles métier

Un message contient : identifiant, organisation, auteur réel, destinataire(s), texte, visibilité sur le mur, statut, dates et éventuelle campagne. L'auteur réel n'est jamais exposé dans les vues membre et mur lorsque le message est anonyme. Il reste accessible uniquement à un administrateur habilité, lorsqu'un abus doit être traité ; chaque consultation de cette identité est journalisée.

Le destinataire ne peut pas modifier un message reçu. L'auteur peut retirer un message uniquement tant qu'il n'est pas publié ou révélé ; après publication, une demande de retrait est traitée par un modérateur.

## 9. Critères d'acceptation

- **AC-01** : un utilisateur YunoHost autorisé accède sans créer de compte local.
- **AC-02** : après l'envoi valide d'un merci à une personne, une équipe ou un service, il est conservé et visible dans la boîte « envoyés » après rechargement.
- **AC-03** : en mode modération préalable, aucun message en attente n'est visible du destinataire ni du mur.
- **AC-04** : après approbation, le message devient visible uniquement aux destinataires et au public prévu.
- **AC-05** : un message anonyme ne révèle pas son auteur dans les vues membre et mur.
- **AC-06** : les messages d'une campagne ne sont pas visibles avant sa révélation ; ils deviennent accessibles au moment prévu.
- **AC-07** : un administrateur peut exporter les données d'un membre et appliquer la politique de suppression configurée.
- **AC-08** : une sauvegarde YunoHost restaurée sur une instance de test retrouve les réglages et les messages autorisés.
- **AC-09** : le paquet s'installe, se met à jour et se désinstalle proprement sur l'environnement YunoHost cible.
- **AC-10** : un membre connecté vote une seule fois par challenge ouvert et ne peut pas voter après la date de clôture.
- **AC-11** : à la clôture d'un challenge, le classement et le ou les lauréats sont calculés selon les règles annoncées, puis le portrait du lauréat et sa récompense virtuelle sont visibles dans l'espace commun.
- **AC-12** : un merci livré à une personne apparaît sur son mur personnel ; un merci livré à une équipe ou un service apparaît sur son mur collectif, accessible à ses gestionnaires autorisés.
- **AC-13** : un membre peut consulter les forces associées à ses propres messages reçus sans rendre son profil ou son classement public.

## 10. Décisions à prendre ensemble

1. **Destinataires externes internes :** les sous-traitants et clients ont-ils chacun un compte YunoHost, ou doivent-ils être représentés comme des fiches/entités sans connexion ?
2. **Règles du vote :** le vote doit-il désigner une personne, une équipe, une action proposée, ou ces trois formats selon le challenge ?
3. **Candidature :** pour un challenge, les membres sont-ils automatiquement candidats, proposés par des pairs, ou candidats volontairement ?
4. **Résultat :** souhaitez-vous afficher les scores détaillés ou uniquement le ou les lauréats ?
5. **Récompense virtuelle :** quels éléments faut-il prévoir au lancement : badge, trophée, points, certificat PDF, portrait sur le mur, ou plusieurs de ces éléments ?
6. **Distribution :** le paquet sera publié dans le catalogue GitHub ARCenal. Il reste à préciser si ce dépôt est public ou privé et si ce catalogue est réservé à vos instances.

## 11. Références de cadrage

Le produit de référence présente publiquement une plateforme de reconnaissance 360°, un mur de gratitude, des messages signés ou anonymes modérés et des temps forts avec révélation simultanée. Cette analyse sert uniquement à identifier les besoins fonctionnels, pas à reproduire le produit.

- [Listen Leon — accueil](https://www.listenleon.com/fr/)
- [Listen Leon — Positive Team Challenge](https://www.listenleon.com/fr/positive-team-challenge)
- [Documentation de packaging YunoHost](https://doc.yunohost.org/en/dev/packaging/)
