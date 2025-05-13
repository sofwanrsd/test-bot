import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
ADMIN_IDS = [5678748710]  # Ganti dengan Telegram user ID admin

# Inisialisasi database jika belum ada
if not os.path.exists("database.json"):
    with open("database.json", "w") as f:
        json.dump({"services": {}, "accounts": {}, "referrals": {}}, f)

def load_db():
    with open("database.json", "r") as f:
        return json.load(f)

def save_db(data):
    with open("database.json", "w") as f:
        json.dump(data, f, indent=2)

# /start dan /akun
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 Streaming", callback_data="kategori_Streaming")],
        [InlineKeyboardButton("💻 Software", callback_data="kategori_Software")],
        [InlineKeyboardButton("🎮 Game", callback_data="kategori_Game")],
        [InlineKeyboardButton("ℹ️ Cara Order", callback_data="cara_order")],
    ]
    await update.message.reply_text("Silakan pilih layanan di bawah ini:", reply_markup=InlineKeyboardMarkup(keyboard))

akun = start

# Kategori handler
async def kategori_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kategori = query.data.split("_")[1]
    db = load_db()
    layanan = [name for name, val in db["services"].items() if val.get("kategori") == kategori]
    if not layanan:
        await query.edit_message_text("Belum ada layanan untuk kategori ini.")
        return
    keyboard = [[InlineKeyboardButton(name, callback_data=f"layanan_{name}")] for name in layanan]
    await query.edit_message_text(f"Pilih layanan {kategori}:", reply_markup=InlineKeyboardMarkup(keyboard))

# Layanan handler
async def layanan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    layanan = query.data.split("_")[1]
    db = load_db()
    if layanan not in db["services"]:
        await query.edit_message_text("Layanan tidak ditemukan.")
        return

    text = f"{layanan.upper()}\n"
    keyboard = []
    for paket, info in db["services"][layanan].items():
        if paket == "kategori":
            continue
        stok = info["stock"]
        status = "✅" if stok > 0 else "❌"
        text += f"{paket.capitalize()} - Rp{info['price']} (Stok: {stok}) {status}\n"
        keyboard.append([InlineKeyboardButton(f"{paket.capitalize()} {status}", callback_data=f"paket_{layanan}_{paket}")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# Paket handler
async def paket_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, layanan, paket = query.data.split("_")
    db = load_db()
    stok = db["services"][layanan][paket]["stock"]
    if stok <= 0:
        await query.edit_message_text("❌ STOK HABIS!\nSilakan pilih paket lain atau cek kembali nanti.")
        return
    akun_key = f"{layanan}_{paket}"
    akun_list = db["accounts"].get(akun_key, [])
    if not akun_list:
        await query.edit_message_text("❌ Akun kosong! Silakan hubungi admin.")
        return
    akun_dikirim = akun_list.pop(0)
    db["services"][layanan][paket]["stock"] -= 1
    db["accounts"][akun_key] = akun_list
    save_db(db)
    email, password = akun_dikirim.split(":")
    await query.edit_message_text(f"✅ AKUN {layanan.upper()}\nEmail: {email}\nPassword: {password}\nMasa aktif: {paket}")

# Admin - tambah layanan
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
        await update.message.reply_text("Format: /tambah_layanan nama \"deskripsi\" kategori")

# Admin - tambah stok
async def tambah_stok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 Akses ditolak!")
        return
    try:
        layanan, paket, jumlah = context.args[0], context.args[1], int(context.args[2])
        akun_list = context.args[3:]
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
        await update.message.reply_text(f"✅ Stok untuk {layanan} {paket} ditambah {jumlah} akun.")
    except:
        await update.message.reply_text("Format: /tambah_stok layanan paket jumlah akun1:pass1 akun2:pass2 ...")

# Admin - cek stok
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
        text = f"📊 STOK {layanan.upper()}:\n"
        for paket, info in db["services"][layanan].items():
            if paket == "kategori": continue
            text += f"{paket.capitalize()}: {info['stock']} akun\n"
        await update.message.reply_text(text)
    except:
        await update.message.reply_text("Format: /stok layanan")

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
