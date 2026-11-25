# KOMI Flow — SaaS Freemium dans Telegram

KOMI Flow est un assistant IA accessible dans Telegram grâce à un bot et une Telegram Mini App. Le backend utilise FastAPI, SQLite et Google Gemini.

## Fonctionnalités actuellement préparées

- Mini App Telegram avec interface de discussion.
- Connexion de la Mini App vérifiée par la signature officielle Telegram (initData).
- Offre gratuite : 15 messages par jour (configurable).
- Offre Premium : 200 messages par jour (configurable).
- Historique récent des conversations conservé dans SQLite.
- Commande administrateur `/grantpremium ID_UTILISATEUR JOURS`.
- Commandes bot : `/start` et `/help`.

**Important :** le mode Premium est actuellement attribué manuellement par l'administrateur. Le paiement et le renouvellement automatique ne sont pas encore intégrés.

## Variables d'environnement

Configure ces variables dans les paramètres secrets de ton hébergeur (ne les publie jamais dans GitHub) :

- `TELEGRAM_BOT_TOKEN` : token de BotFather.
- `GEMINI_API_KEY` : clé Google AI Studio.
- `WEBAPP_URL` : URL HTTPS publique du serveur.
- `ADMIN_IDS` : identifiant numérique Telegram du ou des administrateurs, séparés par des virgules.
- `GEMINI_MODEL` : modèle Gemini, par défaut `gemini-2.5-flash`.
- `FREE_DAILY_LIMIT` : quota gratuit, par défaut 15.
- `PREMIUM_DAILY_LIMIT` : quota Premium, par défaut 200.
- `DATABASE_PATH` : fichier SQLite, par défaut `komi_flow.db`.

## Déploiement

Python 3.11+ est recommandé.

```bash
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```

Le `Procfile` lance la même commande sur les plateformes compatibles. Il faut un hébergeur qui conserve le processus Python actif et un stockage persistant pour `komi_flow.db`.

## Configuration Telegram Mini App

1. Déploie le serveur avec une URL HTTPS publique.
2. Renseigne cette URL complète dans `WEBAPP_URL`.
3. Dans Telegram, ouvre `@BotFather`, utilise `/setdomain` et associe le domaine HTTPS de ton serveur au bot.
4. Redémarre le serveur, puis envoie `/start` au bot.
5. Ouvre la Mini App depuis le bouton du bot.

## Attribution Premium

Ajoute ton identifiant Telegram dans `ADMIN_IDS`, puis utilise dans le chat du bot :

```
/grantpremium ID_UTILISATEUR 30
```

Cela attribue 30 jours de Premium. Ne donne jamais le rôle administrateur à une personne non autorisée.

## Limites à connaître

- Les paiements Telegram et abonnements automatiques ne sont pas encore intégrés.
- SQLite convient à un premier lancement ; pour un SaaS avec beaucoup d'utilisateurs, prévoir une base PostgreSQL.
- L'hébergeur doit fournir un stockage persistant si tu veux conserver les conversations après redémarrage.
- Le site vitrine précédent n'est pas nécessaire au fonctionnement de la Mini App.
