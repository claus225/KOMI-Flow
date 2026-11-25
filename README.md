# KOMI Flow — Bot Telegram intelligent

KOMI Flow est un assistant Telegram en Python connecté à Google Gemini. Il répond aux messages texte et conserve un court historique temporaire par discussion pendant que le programme fonctionne.

## Fonctionnalités

- Réponses générées par Google Gemini.
- Commandes Telegram : `/start`, `/help`, `/about` et `/reset`.
- Historique de conversation temporaire en mémoire.
- Configuration par variables d'environnement.
- Déploiement possible comme worker Python ou avec Docker.

## Configuration

1. Dans Telegram, ouvre **@BotFather**, envoie `/newbot` et suis les étapes pour obtenir le token du bot.
2. Crée une clé API Gemini dans [Google AI Studio](https://aistudio.google.com/).
3. Copie `.env.example` vers un fichier nommé `.env` et renseigne les valeurs :

```env
TELEGRAM_BOT_TOKEN=ton_token_telegram
GEMINI_API_KEY=ta_cle_gemini
GEMINI_MODEL=gemini-2.5-flash
BOT_NAME=KOMI Flow
```

**Important :** ne publie jamais le fichier `.env`, le token Telegram ou la clé Gemini. Le fichier `.gitignore` exclut déjà `.env` du dépôt.

## Installation et démarrage

Python 3.11 ou plus récent est recommandé.

```bash
python -m venv .venv
```

Active l'environnement virtuel, puis installe les dépendances :

```bash
pip install -r requirements.txt
```

Lance le bot :

```bash
python main.py
```

Ouvre ensuite ton bot dans Telegram et envoie `/start`.

## Déploiement

Le `Procfile` définit le processus worker avec la commande `python main.py`. Le `Dockerfile` permet également de construire une image du bot. Sur la plateforme d'hébergement choisie, configure les variables d'environnement suivantes : `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `GEMINI_MODEL` et `BOT_NAME`.

## Limites actuelles

- Le bot traite les messages texte, pas encore les photos, fichiers ou notes vocales.
- L'historique est conservé en mémoire et disparaît au redémarrage.
- Les quotas et conditions d'utilisation de l'API Gemini dépendent du compte Google utilisé.
- Le bot n'est pas encore déployé sur un hébergeur : il faut configurer les clés et choisir un service d'hébergement pour le laisser fonctionner en continu.


## Site web gratuit avec GitHub Pages

Le site vitrine est disponible dans `index.html`. Pour le publier gratuitement :

1. Ouvre **Settings → Pages** dans le dépôt GitHub.
2. Sous **Build and deployment**, choisis **Deploy from a branch**.
3. Sélectionne la branche **main** et le dossier **/(root)**, puis clique sur **Save**.
4. Après publication, le site sera accessible à l'adresse habituelle :
   https://claus225.github.io/KOMI-Flow/

Le site statique ne fait pas tourner le bot Python. Il faudra confirmer le nom public Telegram du bot pour remplacer le lien générique Telegram dans le bouton de la page.

Ne place jamais de token Telegram ni de clé API Gemini dans le site ou dans GitHub.
