# KOMI Flow — assistant IA Freemium dans Telegram

KOMI Flow est un assistant IA servi par un bot Telegram et une Telegram Mini App. Le backend utilise Python, FastAPI, SQLite et Google Gemini.

## Fonctionnalités intégrées

- Mini App accessible depuis le bouton du bot et le menu Telegram.
- Authentification des appels Mini App par validation HMAC de `initData`.
- Offre gratuite : quota de 15 messages par jour par défaut.
- Offre Premium : quota de 200 messages par jour par défaut.
- Historique des 30 derniers messages, isolé par identifiant Telegram.
- Comptage des quotas avec réservations atomiques SQLite pour limiter les dépassements en cas de requêtes simultanées.
- Commandes `/start`, `/help`, `/plan` et `/grantpremium`.
- Attribution Premium manuelle et réservée aux identifiants présents dans `ADMIN_IDS`.

## Modèle Freemium

| Offre | Quota quotidien | Accès |
|---|---:|---|
| Gratuit | 15 messages | Chat IA et historique récent |
| Premium | 200 messages | Chat IA avec quota supérieur et historique récent |

Les quotas sont configurables avec `FREE_DAILY_LIMIT` et `PREMIUM_DAILY_LIMIT`. Le compteur est réinitialisé chaque jour en UTC.

**À savoir :** le paiement automatique et le renouvellement Premium ne sont pas encore activés. Pour le moment, un administrateur attribue Premium avec `/grantpremium ID_UTILISATEUR JOURS`. La Mini App ne doit pas afficher de paiement comme s'il était déjà disponible.

## Configuration

Configure les variables suivantes dans les paramètres secrets de ton hébergeur :

- `TELEGRAM_BOT_TOKEN` : token donné par @BotFather.
- `GEMINI_API_KEY` : clé Google AI Studio.
- `WEBAPP_URL` : URL HTTPS publique du serveur.
- `ADMIN_IDS` : identifiants Telegram des administrateurs, séparés par des virgules.
- `GEMINI_MODEL` : modèle Gemini, par défaut `gemini-2.5-flash`.
- `FREE_DAILY_LIMIT` : quota quotidien gratuit, par défaut 15.
- `PREMIUM_DAILY_LIMIT` : quota quotidien Premium, par défaut 200.
- `DATABASE_PATH` : chemin du fichier SQLite, par défaut `komi_flow.db`.

Ne place jamais les clés dans GitHub, le HTML ou les messages Telegram. Utilise les variables d'environnement privées de l'hébergeur.

## Lancer le projet

Python 3.11+ :

```bash
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```

Le `Procfile` fournit la commande de démarrage pour les plateformes compatibles. Le service doit conserver un processus Python actif et un disque persistant pour le fichier SQLite.

## Configurer la Mini App

1. Déploie le serveur sur une adresse HTTPS publique.
2. Ajoute cette adresse dans la variable `WEBAPP_URL`.
3. Dans @BotFather, configure le domaine du bot avec `/setdomain`.
4. Redémarre le serveur.
5. Envoie `/start` au bot : le bouton d'ouverture de la Mini App apparaîtra. Le serveur configure aussi le bouton de menu Telegram.

## Gérer les utilisateurs Premium

Ajoute ton propre identifiant Telegram à `ADMIN_IDS`, puis envoie au bot :

```
/grantpremium ID_UTILISATEUR 30
```

Cela ajoute 30 jours à l'abonnement Premium de l'utilisateur. La commande est limitée aux administrateurs autorisés.

## Références d'architecture étudiées

KOMI Flow reprend des idées générales et des pratiques documentées dans ces projets publics, sans importer leur code :

- [SorhyAI](https://github.com/FarkhodovIslom/SorhyAI) — séparation bot / Mini App / API, plans Freemium et fonctionnalités administrateur.
- [AI Token Platform](https://github.com/shiny-a2/ai-token-platform) — authentification Telegram Mini App, quotas et séparation des données utilisateurs.
- [telegram-ai](https://github.com/shulya-tech/telegram-ai) — intégration Gemini, quotas et gestion des accès.
- [Telegram Mini App with OpenUI](https://github.com/thesysdev/telegram-mini-app) — lancement de Mini App et validation d'identité Telegram.

## Limites et prochaines étapes

- Ajouter des tests automatisés pour l'authentification, les quotas et l'isolation des conversations.
- Ajouter un vrai système de paiement et de renouvellement avant de commercialiser Premium.
- Migrer vers PostgreSQL si le nombre d'utilisateurs augmente.
- Ajouter une politique de confidentialité, une procédure de suppression des données et des limites anti-abus.
- Le stockage SQLite doit être persistant sur l'hébergeur.
