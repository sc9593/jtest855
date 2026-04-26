import os
import json
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest

### CONFIGURATION ###
BOT_TOKEN = "8621046349:AAGPQQKQuFN8HU4YqfBrUtQVc2lBbBTU42Q"
ADMIN_ID = 123456789  # IMPORTANT: Change this to your numeric Telegram User ID
CHANNELS = ["@EarnBazaarrr", "@Sumanearningtrickk"] 
UPI_ID = "testing8565@try"
UPI_NAME = "suman"
QR_CODE_LINK = "https://your-qr-code-image-link.com/qr.png" # You can update this to your actual QR link later

# Local File Paths
DB_FILE = "users.json"
CONFIG_FILE = "config.json"
PAID_STOCK = "paid_stock.txt"
FREE_STOCK = "free_stock.txt"

# Flask setup for Keep-Alive
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running beautifully!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

### DATABASE HELPER FUNCTIONS ###
def load_json(filepath, default):
    if not os.path.exists(filepath):
        save_json(filepath, default)
        return default
    with open(filepath, 'r') as f:
        try:
            return json.load(f)
        except:
            return default

def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def load_db():
    return load_json(DB_FILE, {})

def save_db(db):
    save_json(DB_FILE, db)

def load_config():
    return load_json(CONFIG_FILE, {"price_per_code": 10})

def save_config(config):
    save_json(CONFIG_FILE, config)

def ensure_txt_files():
    for file in [PAID_STOCK, FREE_STOCK]:
        if not os.path.exists(file):
            open(file, 'w').close()

def get_stock_count(filepath):
    ensure_txt_files()
    with open(filepath, 'r') as f:
        return len([line for line in f.read().splitlines() if line.strip()])

def extract_codes(filepath, qty):
    ensure_txt_files()
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f.read().splitlines() if line.strip()]
    
    if len(lines) < qty:
        return None
    
    codes_to_give = lines[:qty]
    codes_to_keep = lines[qty:]
    
    with open(filepath, 'w') as f:
        f.write("\n".join(codes_to_keep) + ("\n" if codes_to_keep else ""))
        
    return codes_to_give

def add_codes(filepath, codes):
    ensure_txt_files()
    with open(filepath, 'a') as f:
        for code in codes:
            f.write(code + "\n")

### CORE BOT LOGIC ###

async def check_membership(user_id, bot):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except BadRequest:
            # Bot might not be admin or user hasn't interacted
            return False
    return True

def get_main_menu():
    keyboard = [
        [KeyboardButton("🛒 Buy Code"), KeyboardButton("💰 Balance")],
        [KeyboardButton("👥 Refer Earn"), KeyboardButton("🎁 Bonus")],
        [KeyboardButton("💸 Free Withdraw"), KeyboardButton("🆘 Support")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_force_sub_keyboard():
    buttons = [[InlineKeyboardButton(f"Join {ch}", url=f"https://t.me/{ch[1:]}")] for ch in CHANNELS]
    buttons.append([InlineKeyboardButton("✅ Verify Joined", callback_data="verify_joined")])
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()
    
    args = context.args
    referrer_id = args[0] if args and args[0] != user_id else None

    if user_id not in db:
        db[user_id] = {
            "balance": 0,
            "referred_by": referrer_id,
            "verified": False
        }
        save_db(db)

    is_member = await check_membership(update.effective_user.id, context.bot)
    
    if is_member:
        if not db[user_id]["verified"]:
            db[user_id]["verified"] = True
            save_db(db)
        await update.message.reply_text("Welcome back to the bot!", reply_markup=get_main_menu())
    else:
        text = "⚠️ **Action Required**\nYou must join our channels to use this bot!"
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_force_sub_keyboard())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    db = load_db()
    
    await query.answer()

    if query.data == "verify_joined":
        is_member = await check_membership(query.from_user.id, context.bot)
        if is_member:
            if not db[user_id].get("verified", False):
                db[user_id]["verified"] = True
                referrer = db[user_id].get("referred_by")
                if referrer and referrer in db:
                    db[referrer]["balance"] += 1
                    try:
                        await context.bot.send_message(chat_id=int(referrer), text="🎉 You got 1 coin from a new referral!")
                    except:
                        pass
                save_db(db)
            
            await query.message.delete()
            await context.bot.send_message(chat_id=query.from_user.id, text="✅ Verification successful! Welcome to the main menu.", reply_markup=get_main_menu())
        else:
            await query.message.reply_text("❌ You haven't joined all channels yet. Please join and try again.")
            
    elif query.data.startswith("buy_qty_"):
        qty = int(query.data.split("_")[2])
        config = load_config()
        price = config["price_per_code"]
        total = qty * price
        
        context.user_data['pending_qty'] = qty
        context.user_data['pending_amount'] = total
        
        text = (f"💳 **Payment Details**\n\n"
                f"Quantity: {qty} Code(s)\n"
                f"Total Amount: ₹{total}\n"
                f"UPI ID: `{UPI_ID}`\n"
                f"Name: {UPI_NAME}\n\n"
                f"[🔗 Scan QR Code Here]({QR_CODE_LINK})\n\n"
                f"Please pay exactly ₹{total} and click the button below.")
        
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ I Paid", callback_data="i_paid")]])
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif query.data == "i_paid":
        context.user_data['state'] = 'WAITING_UTR'
        await query.message.reply_text("✏️ Please send your 12-digit UTR/Reference number for verification:")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    db = load_db()

    # Check Force Sub first
    if not await check_membership(update.effective_user.id, context.bot):
        await update.message.reply_text("⚠️ You must join our channels first!", reply_markup=get_force_sub_keyboard())
        return

    # Handle UTR Input State
    if context.user_data.get('state') == 'WAITING_UTR':
        if len(text) == 12 and text.isdigit():
            qty = context.user_data.get('pending_qty', 0)
            amt = context.user_data.get('pending_amount', 0)
            
            admin_text = (f"🔔 **New Payment Verification**\n\n"
                          f"User ID: `{user_id}`\n"
                          f"Username: @{update.effective_user.username}\n"
                          f"Amount: ₹{amt}\n"
                          f"Quantity Requested: {qty}\n"
                          f"UTR: `{text}`\n\n"
                          f"Commands:\n`/approve {user_id} {qty}`\n`/reject {user_id}`")
            
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="Markdown")
            await update.message.reply_text("✅ Your payment is being verified by the admin. Please wait.")
            
            # Clear state
            context.user_data['state'] = None
            context.user_data['pending_qty'] = None
            context.user_data['pending_amount'] = None
        else:
            await update.message.reply_text("❌ Invalid UTR. Please send exactly 12 digits.")
        return

    # Main Menu Handling
    if text == "🛒 Buy Code":
        config = load_config()
        price = config["price_per_code"]
        stock = get_stock_count(PAID_STOCK)
        
        msg = f"🛒 **Buy Codes**\n\nPrice per code: ₹{price}\nAvailable Stock: {stock}\n\nSelect quantity:"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("1", callback_data="buy_qty_1"), InlineKeyboardButton("2", callback_data="buy_qty_2")],
            [InlineKeyboardButton("3", callback_data="buy_qty_3"), InlineKeyboardButton("5", callback_data="buy_qty_5")]
        ])
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)

    elif text == "💰 Balance":
        bal = db.get(user_id, {}).get("balance", 0)
        await update.message.reply_text(f"💰 Your Referral Balance: {bal} coins")

    elif text == "👥 Refer Earn":
        bot_username = context.bot.username
        link = f"https://t.me/{bot_username}?start={user_id}"
        await update.message.reply_text(f"👥 **Refer & Earn**\n\nShare your link to earn 1 coin per verified user.\n\nYour Link: {link}", parse_mode="Markdown")

    elif text == "🎁 Bonus":
        await update.message.reply_text("🎁 Bonus feature coming soon! Keep an eye on the channels.")

    elif text == "💸 Free Withdraw":
        bal = db.get(user_id, {}).get("balance", 0)
        cost_of_free_code = 5 # Example: 5 coins for 1 free code
        
        if bal >= cost_of_free_code:
            codes = extract_codes(FREE_STOCK, 1)
            if codes:
                db[user_id]["balance"] -= cost_of_free_code
                save_db(db)
                await update.message.reply_text(f"🎉 Success! Here is your free code:\n\n`{codes[0]}`", parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Sorry, free stock is currently empty. Try again later.")
        else:
            await update.message.reply_text(f"❌ You need {cost_of_free_code} coins to withdraw a free code. Current balance: {bal}")

    elif text == "🆘 Support":
        await update.message.reply_text("💬 Need help? Contact our admin for assistance.")

### ADMIN COMMANDS ###

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        user_id = context.args[0]
        qty = int(context.args[1])
        
        codes = extract_codes(PAID_STOCK, qty)
        if not codes:
            await update.message.reply_text(f"❌ Not enough stock! Current stock: {get_stock_count(PAID_STOCK)}")
            return
            
        code_str = "\n".join([f"`{c}`" for c in codes])
        await context.bot.send_message(chat_id=int(user_id), text=f"✅ Payment Approved! Here are your codes:\n\n{code_str}", parse_mode="Markdown")
        await update.message.reply_text(f"✅ Sent {qty} codes to {user_id}.")
    except Exception as e:
        await update.message.reply_text(f"Format: /approve [USER_ID] [QTY]\nError: {e}")

async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        user_id = context.args[0]
        await context.bot.send_message(chat_id=int(user_id), text="❌ Your payment verification was rejected. Please contact support.")
        await update.message.reply_text(f"✅ Rejection sent to {user_id}.")
    except Exception as e:
        await update.message.reply_text("Format: /reject [USER_ID]")

async def admin_addpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    codes = update.message.text.split()[1:]
    if not codes:
        await update.message.reply_text("Format: /addpaid code1 code2 code3")
        return
    add_codes(PAID_STOCK, codes)
    await update.message.reply_text(f"✅ Added {len(codes)} codes to Paid Stock. Total: {get_stock_count(PAID_STOCK)}")

async def admin_addfree(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    codes = update.message.text.split()[1:]
    if not codes:
        await update.message.reply_text("Format: /addfree code1 code2 code3")
        return
    add_codes(FREE_STOCK, codes)
    await update.message.reply_text(f"✅ Added {len(codes)} codes to Free Stock. Total: {get_stock_count(FREE_STOCK)}")

async def admin_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    paid = get_stock_count(PAID_STOCK)
    free = get_stock_count(FREE_STOCK)
    await update.message.reply_text(f"📦 **Current Stock:**\n\nPaid Codes: {paid}\nFree Codes: {free}", parse_mode="Markdown")

async def admin_setprice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        new_price = int(context.args[0])
        config = load_config()
        config["price_per_code"] = new_price
        save_config(config)
        await update.message.reply_text(f"✅ Price updated to ₹{new_price} per code.")
    except:
        await update.message.reply_text("Format: /setprice [AMOUNT]")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = update.message.text.replace("/broadcast", "").strip()
    if not msg:
        await update.message.reply_text("Format: /broadcast [MESSAGE]")
        return
        
    db = load_db()
    success, fail = 0, 0
    await update.message.reply_text("📢 Broadcast started...")
    
    for user_id in db.keys():
        try:
            await context.bot.send_message(chat_id=int(user_id), text=msg, parse_mode="Markdown")
            success += 1
            await asyncio.sleep(0.05) # Prevent flood limits
        except:
            fail += 1
            
    await update.message.reply_text(f"✅ Broadcast Finished!\nSuccess: {success}\nFailed: {fail}")

### MAIN DEPLOYMENT ###

def main():
    # Ensure config and DB exist
    ensure_txt_files()
    load_db()
    load_config()

    # Start Flask Server on a new thread
    t = Thread(target=run_flask)
    t.start()

    # Build Application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Admin Commands
    application.add_handler(CommandHandler("approve", admin_approve))
    application.add_handler(CommandHandler("reject", admin_reject))
    application.add_handler(CommandHandler("addpaid", admin_addpaid))
    application.add_handler(CommandHandler("addfree", admin_addfree))
    application.add_handler(CommandHandler("stock", admin_stock))
    application.add_handler(CommandHandler("setprice", admin_setprice))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))
    
    # Text Handler (For Menus and UTRs)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Run polling
    application.run_polling()

if __name__ == '__main__':
    main()