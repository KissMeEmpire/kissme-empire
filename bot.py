import os
from telegram import Update,WebAppInfo,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import Application,CommandHandler,ContextTypes
TOKEN=os.getenv("BOT_TOKEN","")
URL=os.getenv("WEBAPP_URL","")
async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not URL:
        await update.message.reply_text("WEBAPP_URL is not configured yet.")
        return
    kb=[[InlineKeyboardButton("👑 Играть в KissMe Empire",web_app=WebAppInfo(url=URL))]]
    await update.message.reply_text("Добро пожаловать в KissMe Empire! Построй свою империю.",reply_markup=InlineKeyboardMarkup(kb))
def main():
    if not TOKEN: raise RuntimeError("Set BOT_TOKEN in environment variables")
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.run_polling()
if __name__=="__main__": main()
