import asyncio
import hashlib
import hmac
import json
import logging
import os
import sqlite3
import time
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from urllib.parse import parse_qsl

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MenuButtonWebApp
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("komi-flow")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
BOT_NAME = os.getenv("BOT_NAME", "KOMI Flow")
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip().rstrip("/")
DATABASE_PATH = os.getenv("DATABASE_PATH", "komi_flow.db")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", "15"))
PREMIUM_DAILY_LIMIT = int(os.getenv("PREMIUM_DAILY_LIMIT", "200"))
BASE_DIR = Path(__file__).resolve().parent

if not BOT_TOKEN or not GEMINI_KEY:
    raise RuntimeError("Configure TELEGRAM_BOT_TOKEN et GEMINI_API_KEY dans les variables d'environnement.")

client = genai.Client(api_key=GEMINI_KEY)
telegram_app = Application.builder().token(BOT_TOKEN).build()

@contextmanager
def db():
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with db() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, first_name TEXT DEFAULT '',
            plan TEXT DEFAULT 'free', premium_until INTEGER DEFAULT 0,
            created_at INTEGER NOT NULL, usage_day TEXT DEFAULT '',
            daily_count INTEGER DEFAULT 0)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS usage_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            usage_day TEXT NOT NULL, status TEXT NOT NULL,
            created_at INTEGER NOT NULL)""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_events_user_day ON usage_events(user_id, usage_day, status)")
        conn.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            role TEXT NOT NULL, content TEXT NOT NULL, created_at INTEGER NOT NULL)""")

def register_user(user):
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO users(user_id, first_name, created_at) VALUES(?,?,?)",
                     (user.id, user.first_name or "", int(time.time())))
        conn.execute("UPDATE users SET first_name=? WHERE user_id=?", (user.first_name or "", user.id))

def get_user(user_id):
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None

def telegram_init_data_valid(init_data: str) -> dict:
    if not init_data:
        raise HTTPException(401, "Ouvre KOMI Flow depuis Telegram.")
    pairs = parse_qsl(init_data, keep_blank_values=True)
    if len({key for key, _ in pairs}) != len(pairs):
        raise HTTPException(401, "Données Telegram invalides.")
    values = dict(pairs)
    received_hash = values.pop("hash", None)
    try:
        auth_date = int(values.get("auth_date", "0") or 0)
    except ValueError:
        raise HTTPException(401, "Date de session Telegram invalide.")
    now = int(time.time())
    if not received_hash or auth_date > now + 60 or now - auth_date > 3600:
        raise HTTPException(401, "Session Telegram expirée. Rouvre la Mini App.")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise HTTPException(401, "Signature Telegram invalide.")
    try:
        user = json.loads(values["user"])
    except Exception:
        raise HTTPException(401, "Profil Telegram introuvable.")
    return user

async def current_user(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    tg_user = telegram_init_data_valid(init_data)
    register_user(type("TelegramUser", (), {
        "id": int(tg_user["id"]), "first_name": tg_user.get("first_name", "")
    })())
    return get_user(int(tg_user["id"]))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    register_user(update.effective_user)
    if WEBAPP_URL:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(
            "🚀 Ouvrir KOMI Flow", web_app=WebAppInfo(url=WEBAPP_URL + "/app")
        )]])
        await update.message.reply_text(
            f"Bienvenue sur {BOT_NAME} !\nTon assistant IA dans Telegram.\n\n"
            "Appuie ci-dessous pour ouvrir ta Mini App.",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            "Bienvenue sur KOMI Flow ! La Mini App n'est pas encore configurée. "
            "L'administrateur doit définir WEBAPP_URL."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Utilise /start pour ouvrir KOMI Flow. Dans la Mini App, tu peux discuter avec l'IA et consulter ton quota.\n/plan — voir les offres et les quotas.") 

async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
    register_user(user)
    record = get_user(user.id)
    premium = record["plan"] == "premium" and record["premium_until"] > int(time.time())
    plan = "Premium" if premium else "Gratuit"
    quota = PREMIUM_DAILY_LIMIT if premium else FREE_DAILY_LIMIT
    await update.message.reply_text(
        f"Ton offre : {plan}\nQuota : {quota} messages par jour.\n"
        "Le passage Premium est actuellement activé par l'administrateur. "
        "Les paiements automatiques ne sont pas encore disponibles."
    )

async def grant_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Commande réservée à l'administrateur.")
        return
    if len(context.args) != 2 or not all(x.isdigit() for x in context.args):
        await update.message.reply_text("Usage : /grantpremium ID_UTILISATEUR JOURS")
        return
    user_id, days = map(int, context.args)
    if days < 1 or days > 365:
        await update.message.reply_text("La durée doit être comprise entre 1 et 365 jours.")
        return
    with db() as conn:
        row = conn.execute("SELECT premium_until FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            await update.message.reply_text("Utilisateur introuvable. Il doit d'abord lancer /start.")
            return
        until = max(int(time.time()), int(row["premium_until"] or 0)) + days * 86400
        conn.execute("UPDATE users SET plan='premium', premium_until=? WHERE user_id=?", (until, user_id))
    await update.message.reply_text(f"Premium activé pour {user_id} pendant {days} jour(s).")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("plan", plan_command))
telegram_app.add_handler(CommandHandler("grantpremium", grant_premium))

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await telegram_app.initialize()
    if WEBAPP_URL:
        await telegram_app.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="KOMI Flow", web_app=WebAppInfo(url=WEBAPP_URL + "/app")
            )
        )
    if not WEBAPP_URL or not TELEGRAM_WEBHOOK_SECRET:
        raise RuntimeError("Configure WEBAPP_URL et TELEGRAM_WEBHOOK_SECRET pour activer le webhook.")
    await telegram_app.start()
    if WEBAPP_URL:
        await telegram_app.bot.set_webhook(
            url=WEBAPP_URL + "/telegram/webhook",
            secret_token=TELEGRAM_WEBHOOK_SECRET or None,
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
        )
        log.info("Webhook Telegram configuré")
    else:
        log.warning("WEBAPP_URL absent : webhook Telegram non configuré")
    log.info("KOMI Flow démarré")
    yield
    if WEBAPP_URL:
        await telegram_app.bot.delete_webhook(drop_pending_updates=False)
    await telegram_app.stop()
    await telegram_app.shutdown()

app = FastAPI(title="KOMI Flow API", lifespan=lifespan)

class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=6000)

@app.get("/")
async def home():
    return {"name": BOT_NAME, "status": "online", "mini_app": "/app"}

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    if TELEGRAM_WEBHOOK_SECRET:
        supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(supplied, TELEGRAM_WEBHOOK_SECRET):
            raise HTTPException(403, "Webhook non autorisé.")
    try:
        payload = await request.json()
        update = Update.de_json(payload, telegram_app.bot)
        await telegram_app.update_queue.put(update)
    except Exception:
        log.exception("Mise à jour Telegram invalide")
        raise HTTPException(400, "Mise à jour Telegram invalide.")
    return {"ok": True}

@app.get("/app")
async def mini_app():
    return FileResponse(BASE_DIR / "webapp" / "index.html")

@app.get("/api/me")
async def me(request: Request):
    user = await current_user(request)
    premium_active = user["plan"] == "premium" and user["premium_until"] > int(time.time())
    plan = "premium" if premium_active else "free"
    limit = PREMIUM_DAILY_LIMIT if premium_active else FREE_DAILY_LIMIT
    today = time.strftime("%Y-%m-%d", time.gmtime())
    with db() as conn:
        conn.execute("UPDATE usage_events SET status='expired' WHERE user_id=? AND usage_day=? AND status='reserved' AND created_at<?",
                     (user["user_id"], today, int(time.time()) - 300))
        used = conn.execute(
            "SELECT COUNT(*) FROM usage_events WHERE user_id=? AND usage_day=? AND status IN ('reserved','used')",
            (user["user_id"], today)
        ).fetchone()[0]
    return {"id": user["user_id"], "first_name": user["first_name"], "plan": plan,
            "used": used, "limit": limit, "remaining": max(0, limit-used)}

@app.get("/api/history")
async def history(request: Request):
    user = await current_user(request)
    with db() as conn:
        rows = conn.execute("SELECT role, content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT 30",
                            (user["user_id"],)).fetchall()
    return {"messages": [dict(r) for r in reversed(rows)]}

@app.post("/api/chat")
async def chat(payload: ChatInput, request: Request):
    user = await current_user(request)
    user_id = user["user_id"]
    now = int(time.time())
    today = time.strftime("%Y-%m-%d", time.gmtime(now))
    premium_active = user["plan"] == "premium" and user["premium_until"] > now
    limit = PREMIUM_DAILY_LIMIT if premium_active else FREE_DAILY_LIMIT

    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE usage_events SET status='expired' WHERE user_id=? AND usage_day=? AND status='reserved' AND created_at<?",
                     (user_id, today, now - 300))
        used = conn.execute(
            "SELECT COUNT(*) FROM usage_events WHERE user_id=? AND usage_day=? AND status IN ('reserved','used')",
            (user_id, today)
        ).fetchone()[0]
        if used >= limit:
            conn.rollback()
            raise HTTPException(429, "QUOTA_REACHED")
        reservation = conn.execute(
            "INSERT INTO usage_events(user_id, usage_day, status, created_at) VALUES(?,?,?,?)",
            (user_id, today, "reserved", now)
        ).lastrowid
        previous = conn.execute("SELECT role, content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT 12",
                                (user_id,)).fetchall()
        conn.commit()

    contents = [types.Content(role=r["role"], parts=[types.Part(text=r["content"])])
                for r in reversed(previous)]
    contents.append(types.Content(role="user", parts=[types.Part(text=payload.message)]))
    try:
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL, contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=f"Tu es {BOT_NAME}, assistant IA utile et clair. Réponds dans la langue de l'utilisateur.",
                temperature=0.7, max_output_tokens=1200))
        answer = (response.text or "").strip() or "Je n'ai pas pu générer de réponse. Reformule ta question."
    except Exception:
        log.exception("Erreur Gemini")
        with db() as conn:
            conn.execute("UPDATE usage_events SET status='refunded' WHERE id=? AND user_id=? AND status='reserved'",
                         (reservation, user_id))
        raise HTTPException(502, "Le service IA est temporairement indisponible.")

    with db() as conn:
        conn.execute("UPDATE usage_events SET status='used' WHERE id=? AND user_id=? AND status='reserved'",
                     (reservation, user_id))
        conn.executemany("INSERT INTO messages(user_id, role, content, created_at) VALUES(?,?,?,?)",
                         [(user_id, "user", payload.message, now), (user_id, "model", answer, int(time.time()))])
    return {"answer": answer, "used": used + 1, "limit": limit, "plan": "premium" if premium_active else "free"}

@app.post("/api/reset")
async def reset_history(request: Request):
    user = await current_user(request)
    with db() as conn:
        conn.execute("DELETE FROM messages WHERE user_id=?", (user["user_id"],))
    return {"ok": True}
