import os
import json
import asyncio
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest

# Logs enable karein taaki Render me error dikhe
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

### CONFIGURATION ###
# APNA SAHI TOKEN YAHAN DALO
BOT_TOKEN = "8621046349:AAGPQQKQuFN8HU4YqfBrUtQVc2lBbBTU42Q"
# APNI SAHI NUMERIC ID YAHAN DALO (Check @userinfobot)
ADMIN_ID = 1655373100
CHANNELS = ["@EarnBazaarrr", "@Sumanearningtrickk"] 
UPI_ID = "testing8565@try"
UPI_NAME = "suman"
QR_CODE_LINK = "https://your-qr-code-image-link.com/qr.png"

# Local File Paths
DB_FILE = "users.json"
CONFIG_FILE = "config.json"
PAID_STOCK = "paid_stock.txt"
FREE_STOCK = "free_stock.txt"

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is Alive!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

def load_json(filepath, default):
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f: json.dump(default, f)
        return default
    with open(filepath, 'r') as f:
        try: return json.load(f)
        except: return default

def save_json(filepath, data):
    with open(filepath, 'w') as f: json.dump(data, f, indent=4)

def ensure_files():
    for file in [PAID_STOCK, FREE_STOCK]:
        if not os.path.exists(file): open(file, 'w').close()

async def check_membership(user_id, bot):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ['left', 'kicked']: return False
        except: return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_json(DB_FILE, {})
    
    if user_id not in db:
        referrer = context.args[0] if context.args else None
        db[user_id] = {"balance": 0, "referred_by": referrer, "verified": False}
        save_json(DB_FILE, db)

    is_member = await check_membership(update.effective_user.id, context.bot)
    if is_member:
        keyboard = [[KeyboardButton("🛒 Buy Code"), KeyboardButton("💰 Balance")],
                    [KeyboardButton("👥 Refer Earn"), KeyboardButton("🎁 Bonus")],
                    [KeyboardButton("💸 Free Withdraw"), KeyboardButton("🆘 Support")]]
        await update.message.reply_text("✅ Welcome!", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    else:
        buttons = [[InlineKeyboardButton(f"Join {ch}", url=f"https://t.me/{ch[1:]}")] for ch in CHANNELS]
        buttons.append([InlineKeyboardButton("✅ Verify Joined", callback_data="verify")])
        await update.message.reply_text("⚠️ Join channels first:", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🛒 Buy Code":
        await update.message.reply_text("Select Quantity (Coming Soon)")
    elif text == "💰 Balance":
        db = load_json(DB_FILE, {})
        bal = db.get(str(update.effective_user.id), {}).get("balance", 0)
        await update.message.reply_text(f"Balance: {bal}")

def main():
    ensure_files()
    Thread(target=run_flask).start()
    
    # Bot build
    print("Starting Bot...")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    
    print("Bot is polling...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
