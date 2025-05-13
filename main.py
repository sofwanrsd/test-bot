import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Ganti dengan token asli
BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_IDS = [5678748710]  # Ganti dengan ID admin

# Inisialisasi data jika belum ada
if not os.path.exists("database.json"):
    with open("database.json", "w") as f:
        json.dump({"services": {}, "accounts": {}, "referrals": {}}, f)

# Load database
def load_db():
    with open("database.json", "r") as f:
        return json.load(f)

def save_db(data):
    with open("database.json", "w") as f:
        json.dump(data, f, indent=2)

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 Streaming", callback_data="kategori_Streaming")],
        [InlineKeyboardButton("💻 Software", callback_data="kategori_Software")],
        [InlineKeyboardButton("🎮 Game", callback_data="kategori_Game")],
        [InlineKeyboardButton("ℹ️ Cara Order", callback_data="cara_order")],
    ]
    await update.message.reply_text("Selamat datang! Pilih layanan di bawah ini:", reply_markup=InlineKeyboardMarkup(keyboard))

# Command /akun (alias menu)
async def akun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# Callback untuk kategori
async def kategori_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kategori = query.data.split("_")[1]
    db = load_db()
    layanan = [nama for nama, val in db["services"].items() if val.get("kategori") == kategori]
    if not layanan:
        await query.edit_message_text("Belum ada layanan di kategori ini.")
        return
    keyboard = [[InlineKeyboardButton(name, callback_data=f"layanan_{name}")] for name in layanan]
    await query.edit_message_text(f"Pilih layanan {kategori}:", reply_markup=InlineKeyboardMarkup(keyboard))

# Callback untuk layanan
async def layanan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    layanan = query.data.split("_")[1]
    db = load_db()
    if layanan not in db["services"]:
        await query.edit_message_text("Layanan tidak ditemukan.")
        return

    text = f"🎬 {layanan.upper()} PREMIUM\\n"
    keyboard = []
    for paket, info in db["services"][layanan].items():
        stok = info["stock"]
        status = "✅" if stok > 0 else "❌"
        text += f"{paket.capitalize()} - Rp{info['price']} (Stok: {stok}) {status}\\n"
        keyboard.append([InlineKeyboardButton(f"{paket.capitalize()} {status}", callback_data=f"paket_{layanan}_{paket}")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# Callback untuk paket
async def paket_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, layanan, paket = query.data.split("_")
    db = load_db()
    stok = db["services"][layanan][paket]["stock"]
    if stok <= 0:
        await query.edit_message_text("❌ STOK HABIS!\\nSilakan pilih paket lain atau cek kembali nanti.")
        return
    # Simulasi pembayaran (otomatis)
    akun_key = f"{layanan}_{paket}"
    akun = db["accounts"].get(akun_key, [])
    if not akun:
        await query.edit_message_text("❌ Akun kosong! Silakan hubungi admin.")
        return
    akun_dikirim = akun.pop(0)
    db["services"][layanan][paket]["stock"] -= 1
    db["accounts"][akun_key] = akun
    save_db(db)
    email, password = akun_dikirim.split(":")
    await query.edit_message_text(f"✅ AKUN {layanan.upper()}:\\nEmail: {email}\\nPassword: {password}\\nMasa aktif: {paket}")

# Tambah layanan (admin)
async def tambah_layanan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 Akses ditolak!")
        return
    try:
        nama, deskripsi, kategori = context.args[0], context.args[1], context.args[2]
        db = load_db()
        db["services"][nama] = {"deskripsi": deskripsi, "kategori": kategori}
        save_db(db)
        await update.message.reply_text(f"✅ Layanan {nama} ditambahkan.")
    except:
        await update.message.reply_text("Format salah. Gunakan: /tambah_layanan NAMA \"DESKRIPSI\" KATEGORI")

# Tambah stok (admin)
async def tambah_stok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 Akses ditolak!")
        return
    try:
        layanan, paket, jumlah = context.args[0], context.args[1], int(context.args[2])
        akun_list = context.args[3:]  # akun1:pass1 akun2:pass2 ...
        db = load_db()
        if layanan not in db["services"]:
            await update.message.reply_text("Layanan tidak ditemukan.")
            return
        if paket not in db["services"][layanan]:
            db["services"][layanan][paket] = {"price": 0, "stock": 0}
        db["services"][layanan][paket]["stock"] += jumlah
        akun_key = f"{layanan}_{paket}"
        if akun_key not in db["accounts"]:
            db["accounts"][akun_key] = []
        db["accounts"][akun_key] += akun_list
        save_db(db)
        await update.message.reply_text(f"✅ Stok untuk {layanan} paket {paket} ditambah {jumlah} akun.")
    except:
        await update.message.reply_text("Format salah. Gunakan: /tambah_stok LAYANAN PAKET JUMLAH akun1:pass1 akun2:pass2 ...")

# Cek stok (admin)
async def cek_stok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 Akses ditolak!")
        return
    try:
        layanan = context.args[0]
        db = load_db()
        if layanan not in db["services"]:
            await update.message.reply_text("Layanan tidak ditemukan.")
            return
        text = f"📊 STOK {layanan.upper()}:\\n"
        for paket, info in db["services"][layanan].items():
            text += f"{paket.capitalize()}: {info['stock']} akun\\n"
        await update.message.reply_text(text)
    except:
        await update.message.reply_text("Format: /stok LAYANAN")

# Main function
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("akun", akun))
    app.add_handler(CommandHandler("tambah_layanan", tambah_layanan))
    app.add_handler(CommandHandler("tambah_stok", tambah_stok))
    app.add_handler(CommandHandler("stok", cek_stok))
    app.add_handler(CallbackQueryHandler(kategori_handler, pattern="^kategori_"))
    app.add_handler(CallbackQueryHandler(layanan_handler, pattern="^layanan_"))
    app.add_handler(CallbackQueryHandler(paket_handler, pattern="^paket_"))
    app.run_polling()

if __name__ == "__main__":
    main()
    """
}
