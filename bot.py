from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

produk = {
    "net1": {"nama": "Netflix Premium", "harga": 23000, "terjual": 2},
    "cc7d": {"nama": "ChatGPT Plus Akun", "harga": 15000, "terjual": 1},
}

menu_utama = ReplyKeyboardMarkup(
    [["List Produk", "Cara Order"]],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛍️ Selamat datang di *KoalaStoreBot*! Silakan pilih menu:",
        parse_mode="Markdown",
        reply_markup=menu_utama
    )

async def list_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = "🔥 *Top Produk Kami:*\n\n"
    for idx, (kode, item) in enumerate(produk.items(), start=1):
        total = item["harga"] * item["terjual"]
        pesan += (
            f"{idx}. 📦 *{item['nama']}*\n"
            f"🔖 Kode: `{kode}`\n"
            f"🛒 Terjual: {item['terjual']}\n"
            f"💰 Pendapatan: Rp{total:,}\n\n"
        )
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def cara_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_link = "https://t.me/your_channel/123"  # Ganti dengan link video kamu
    pesan = (
        f"📽️ [TUTORIAL PEMESANAN]({video_link})\n\n"
        "Klik link di atas jika kamu belum tahu cara order."
    )
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def handle_pesan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "List Produk":
        await list_produk(update, context)
    elif text == "Cara Order":
        await cara_order(update, context)
    else:
        await update.message.reply_text("Silakan pilih menu yang tersedia.")

# Ganti dengan Token Bot dari BotFather
TOKEN = "ISI_TOKEN_BOT_MU"

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pesan))
app.run_polling()
