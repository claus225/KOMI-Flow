import logging
import os
from collections import defaultdict, deque

from dotenv import load_dotenv
from google import genai
from google.genai import types
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
BOT_NAME = os.getenv("BOT_NAME", "KOMI Flow").strip()

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("La variable TELEGRAM_BOT_TOKEN est manquante.")
if not GEMINI_API_KEY:
    raise RuntimeError("La variable GEMINI_API_KEY est manquante.")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

client = genai.Client(api_key=GEMINI_API_KEY)
# Historique temporaire en mémoire : il est perdu au redémarrage du bot.
histories = defaultdict(lambda: deque(maxlen=12))

SYSTEM_PROMPT = (
    f"Tu es {BOT_NAME}, un assistant IA utile, poli et clair. "
    "Réponds dans la langue utilisée par la personne. "
    "Explique les choses simplement, signale les incertitudes et "
    "n'invente pas de faits. Si une demande est ambiguë, demande une précision."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👋 Bonjour ! Je suis {BOT_NAME}, ton assistant intelligent.\n\n"
        "Envoie-moi une question pour discuter avec moi.\n\n"
        "Commandes :\n"
        "/start — démarrer\n"
        "/help — aide\n"
        "/reset — effacer le contexte de cette discussion\n"
        "/about — à propos"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Pose simplement ta question dans le chat.\n"
        "Utilise /reset pour recommencer une conversation sans l'ancien contexte."
    )


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"{BOT_NAME} fonctionne avec Python, Telegram et Google Gemini."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    histories.pop(update.effective_chat.id, None)
    await update.message.reply_text("🧹 Contexte de cette discussion réinitialisé.")


async def answer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_text = update.message.text.strip()
    if not user_text:
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    history = histories[chat_id]
    contents = [
        types.Content(role=role, parts=[types.Part(text=text)])
        for role, text in history
    ]
    contents.append(types.Content(role="user", parts=[types.Part(text=user_text)]))

    try:
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=1200,
            ),
        )
        reply = (response.text or "").strip()
        if not reply:
            reply = "Je n'ai pas réussi à formuler une réponse. Peux-tu reformuler ?"

        history.append(("user", user_text))
        history.append(("model", reply))

        # Telegram limite la longueur d'un message ; découpage simple.
        for start_index in range(0, len(reply), 4000):
            await update.message.reply_text(reply[start_index:start_index + 4000])

    except Exception:
        logger.exception("Erreur pendant la génération IA")
        await update.message.reply_text(
            "Désolé, je rencontre un problème technique. Réessaie dans un instant."
        )


def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer_message))
    logger.info("%s démarre…", BOT_NAME)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
