import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

produk = {
    "1": {"nama": "Netflix Premium", "stok": 5, "harga": 23000},
    "2": {"nama": "Spotify Premium", "stok": 3, "harga": 15000},
    "3": {"nama": "YouTube Premium", "stok": 2, "harga": 20000},
    "4": {"nama": "ChatGPT Plus", "stok": 4, "harga": 18000},
}

# States
PILIH_PRODUK, PEMBAYARAN = range(2)

menu_utama = ReplyKeyboardMarkup(
    [["Lihat Produk"]],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Halo {user.first_name} 👋\n"
        "Selamat datang di *KoalaStoreBot*! Ketik atau pilih 'Lihat Produk' untuk mulai.",
        parse_mode="Markdown",
        reply_markup=menu_utama
    )
    return PILIH_PRODUK

async def tampilkan_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = "📦 *List Produk Tersedia:*\n\n"
    for kode, item in produk.items():
        pesan += (
            f"{kode}. *{item['nama']}*\n"
            f"   💰 Harga: Rp{item['harga']:,}\n"
            f"   📦 Stok: {item['stok']}\n\n"
        )
    pesan += "Ketik nomor produk (1 / 2 / 3 / 4) untuk melanjutkan."
    await update.message.reply_text(pesan, parse_mode="Markdown")
    return PILIH_PRODUK

async def pilih_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pilihan = update.message.text.strip()
    if pilihan not in produk:
        await update.message.reply_text("❌ Pilihan tidak valid. Silakan ketik 1, 2, 3, atau 4.")
        return PILIH_PRODUK

    item = produk[pilihan]
    context.user_data["produk_dipilih"] = pilihan

    await update.message.reply_text(
        f"📦 *{item['nama']}*\n"
        f"💰 Harga: Rp{item['harga']:,}\n"
        f"📦 Stok: {item['stok']}\n\n"
        f"Cara order:\nKetik `buy {pilihan}` untuk melanjutkan ke pembayaran.",
        parse_mode="Markdown"
    )
    return PEMBAYARAN

async def proses_pembayaran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if not text.startswith("buy"):
        await update.message.reply_text("Ketik `buy <nomor>` untuk melanjutkan pembelian.")
        return PEMBAYARAN

    kode = text.split(" ")[1] if len(text.split()) > 1 else None
    if kode not in produk:
        await update.message.reply_text("Produk tidak ditemukan.")
        return PILIH_PRODUK

    item = produk[kode]

    await update.message.reply_text(
        f"✅ *Pembayaran*\nSilakan transfer Rp{item['harga']:,} ke:\n"
        "`1234567890 (Bank ABC)`\n\n"
        "Setelah transfer, ketik `sudah bayar` untuk konfirmasi.",
        parse_mode="Markdown"
    )
    return "KONFIRMASI"

async def konfirmasi_pembayaran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() != "sudah bayar":
        await update.message.reply_text("Ketik `sudah bayar` setelah kamu transfer.")
        return "KONFIRMASI"

    kode = context.user_data.get("produk_dipilih")
    item = produk.get(kode)

    await update.message.reply_text(
        f"🎉 Terima kasih! Pembayaran untuk *{item['nama']}* diterima.\n"
        f"Akun akan dikirimkan segera...\n\n"
        f"🔑 Username: `user_{kode}`\n🔑 Password: `pass1234`",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def batal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Transaksi dibatalkan.")
    return ConversationHandler.END

if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PILIH_PRODUK: [
                MessageHandler(filters.Regex("(?i)^Lihat Produk$"), tampilkan_produk),
                MessageHandler(filters.TEXT & ~filters.COMMAND, pilih_produk)
            ],
            PEMBAYARAN: [
                MessageHandler(filters.Regex("^buy "), proses_pembayaran),
                MessageHandler(filters.TEXT & ~filters.COMMAND, proses_pembayaran),
            ],
            "KONFIRMASI": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, konfirmasi_pembayaran)
            ],
        },
        fallbacks=[CommandHandler("batal", batal)],
    )

    app.add_handler(conv_handler)
    print("Bot berjalan...")
    app.run_polling()
