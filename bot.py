import os, asyncio
from telegram import Update, MenuButtonWebApp, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBAPP_URL = os.environ["WEBAPP_URL"]  # Must be public HTTPS URL

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("💋 Играть / Play", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text(
        "Добро пожаловать в KissMe Empire! Построй свою бизнес-империю.\\n\\n"
        "Welcome to KissMe Empire! Build your business empire.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def post_init(app: Application):
    await app.bot.set_chat_menu_button(menu_button=MenuButtonWebApp(
        text="Играть / Play", web_app=WebAppInfo(url=WEBAPP_URL)
    ))

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    print("KissMe Empire bot is running. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
