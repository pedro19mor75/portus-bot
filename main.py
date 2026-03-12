import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
CAPITAL = float(os.environ.get("CAPITAL", "900"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "Ola! Sou o Portus - o teu assistente Turtle Trading!\n\n"
        "Comandos disponiveis:\n"
        "/scan - Correr o scanner agora\n"
        "/capital - Ver o teu capital\n"
        "/regras - Regras Turtle Trading\n"
        "/help - Ajuda\n\n"
        f"Capital atual: {CAPITAL:.0f} euros\n"
        "Scanner automatico: todos os dias as 12:00 UTC"
    )
    await update.message.reply_text(msg)

async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("A analisar os mercados... aguarda!")
    try:
        from scanner import correr_scanner
        sinais, proximos, neutros, resumo = correr_scanner(CAPITAL)
        await update.message.reply_text(resumo[:4000])
    except Exception as e:
        await update.message.reply_text(f"Erro no scanner: {e}")

async def cmd_capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CAPITAL
    args = context.args
    if args:
        try:
            CAPITAL = float(args[0])
            await update.message.reply_text(f"Capital atualizado: {CAPITAL:.0f} euros\nRisco por trade: {CAPITAL*0.01:.2f} euros")
        except:
            await update.message.reply_text("Uso: /capital 900")
    else:
        await update.message.reply_text(f"Capital atual: {CAPITAL:.0f} euros\nRisco por trade: {CAPITAL*0.01:.2f} euros")

async def cmd_regras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "REGRAS TURTLE TRADING\n\n"
        "ENTRADAS:\n"
        "- Sistema 1: Rompe maxima de 20 dias\n"
        "- Sistema 2: Rompe maxima de 55 dias\n\n"
        f"TAMANHO DA POSICAO:\n"
        f"- Risco = 1% = {CAPITAL*0.01:.2f} euros\n"
        "- Unidade = Risco dividido por ATR\n"
        "- Maximo: 4 unidades por ativo\n\n"
        "STOP LOSS:\n"
        "- Sempre 2xATR abaixo da entrada\n"
        "- NUNCA mover contra a posicao\n\n"
        "SAIDAS:\n"
        "- S1: minima de 10 dias\n"
        "- S2: minima de 20 dias"
    )
    await update.message.reply_text(msg)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos disponiveis:\n"
        "/start - Boas vindas\n"
        "/scan - Correr scanner\n"
        "/capital 900 - Ver/alterar capital\n"
        "/regras - Regras Turtle\n"
        "/help - Esta mensagem"
    )

async def resposta_generica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Usa /help para ver os comandos!")

async def scan_automatico(app):
    logger.info("Scanner automatico a correr...")
    try:
        from scanner import correr_scanner
        sinais, proximos, neutros, resumo = correr_scanner(CAPITAL)
        if sinais:
            await app.bot.send_message(chat_id=CHAT_ID, text=f"ALERTA TURTLE! {len(sinais)} sinal(is)!\n\n{resumo[:4000]}")
        elif proximos:
            nomes = ", ".join([r["nome"] for r in proximos])
            await app.bot.send_message(chat_id=CHAT_ID, text=f"Atencao! Proximos do rompimento: {nomes}\nUsa /scan para detalhes.")
        else:
            await app.bot.send_message(chat_id=CHAT_ID, text="Scanner diario: Sem sinais hoje. Mercado neutro.")
    except Exception as e:
        logger.error(f"Erro scanner: {e}")

def main():
    if not TOKEN:
        raise Exception("TELEGRAM_TOKEN nao definido!")
    if not CHAT_ID:
        raise Exception("TELEGRAM_CHAT_ID nao definido!")

    print(f"A iniciar Portus Bot...")
    print(f"Token: {TOKEN[:15]}...")
    print(f"Chat ID: {CHAT_ID}")
    print(f"Capital: {CAPITAL} euros")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("capital", cmd_capital))
    app.add_handler(CommandHandler("regras", cmd_regras))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, resposta_generica))

    scheduler = AsyncIOScheduler(timezone=pytz.utc)
    scheduler.add_job(scan_automatico, trigger="cron", hour=12, minute=0, args=[app])
    scheduler.start()

    print("Portus Bot iniciado com sucesso!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
