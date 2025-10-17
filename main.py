from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# --- Simple Flask web server for Render to stay alive ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✅ Telegram Bot is running on Render!"

def run_web():
    flask_app.run(host='0.0.0.0', port=8080)

Thread(target=run_web).start()
# --------------------------------------------------------


# --- BOT TOKEN ---
BOT_TOKEN = "8212545907:AAHp6rT8lyJnvR1zjXympN-ci0Q8D3cbitI"

# --- States for Conversation ---
PAIR, BALANCE, RISK, STOPLOSS, POSITIONS = range(5)

# --- Approximate exchange rates for dynamic pip calculation ---
EXCHANGE_RATES = {
    "EURUSD": 1.0,
    "GBPUSD": 1.0,
    "USDCHF": 0.90,
    "USDJPY": 150.0,
    "XAUUSD": 1.0,
}

# --- Start command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("EURUSD", callback_data="EURUSD")],
        [InlineKeyboardButton("XAUUSD", callback_data="XAUUSD")],
        [InlineKeyboardButton("USDCHF", callback_data="USDCHF")],
        [InlineKeyboardButton("USDJPY", callback_data="USDJPY")],
        [InlineKeyboardButton("GBPUSD", callback_data="GBPUSD")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("What are you trading?", reply_markup=reply_markup)
    return PAIR


# --- Handle pair selection ---
async def select_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["pair"] = query.data
    await query.edit_message_text(text=f"You selected {query.data}. Enter your account balance in USD:")
    return BALANCE


# --- Balance input ---
async def balance_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["balance"] = float(update.message.text)
    await update.message.reply_text("Enter your risk percentage (e.g. 1 for 1%):")
    return RISK


# --- Risk input ---
async def risk_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["risk_pct"] = float(update.message.text)
    await update.message.reply_text("Enter your stop loss size in pips:")
    return STOPLOSS


# --- Stop loss input ---
async def stoploss_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["stoploss"] = float(update.message.text)
    await update.message.reply_text("How many positions do you want to enter?")
    return POSITIONS


# --- Positions input ---
async def positions_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pair = context.user_data["pair"]
    balance = context.user_data["balance"]
    risk_pct = context.user_data["risk_pct"]
    stoploss = context.user_data["stoploss"]
    positions = float(update.message.text)

    rate = EXCHANGE_RATES.get(pair, 1.0)
    if pair.startswith("USD"):
        if "JPY" in pair:
            pip_value = (0.01 / rate) * 100000
        else:
            pip_value = (0.0001 / rate) * 100000
    else:
        pip_value = 10

    if pair == "XAUUSD":
        pip_value = 100

    risk_amount = balance * (risk_pct / 100.0)
    total_lots = risk_amount / (stoploss * pip_value)

    if pair == "XAUUSD":
        total_lots /= 10

    total_lots = round(total_lots, 2)
    per_position = round(total_lots / positions, 2)

    await update.message.reply_text(
        f"💰 *Position Size Calculation Complete*\n\n"
        f"**Pair:** {pair}\n"
        f"**Balance:** ${balance}\n"
        f"**Risk:** {risk_pct}%\n"
        f"**Stop Loss:** {stoploss} pips\n"
        f"**Positions:** {positions}\n\n"
        f"📏 *Total Lot Size:* {total_lots}\n"
        f"📊 *Per Position:* {per_position}\n\n"
        f"To start a new calculation, type /start",
        parse_mode="Markdown",
    )

    return ConversationHandler.END


# --- Cancel handler ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Calculation cancelled. Type /start to begin again.")
    return ConversationHandler.END


# --- Main ---
def main():
    print("🤖 Bot is running...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PAIR: [CallbackQueryHandler(select_pair)],
            BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, balance_input)],
            RISK: [MessageHandler(filters.TEXT & ~filters.COMMAND, risk_input)],
            STOPLOSS: [MessageHandler(filters.TEXT & ~filters.COMMAND, stoploss_input)],
            POSITIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, positions_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()


if __name__ == "__main__":
    main()
