import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import load_dotenv

# Load .env (optional kalau mau aman taruh token dan ID admin)
load_dotenv()

# Ganti dengan token bot kamu
TOKEN = os.getenv("BOT_TOKEN", "PASTE_TOKEN_DI_SINI")

# Ganti dengan ID admin kamu
admin_ids = [int(os.getenv("ADMIN_ID", "123456789"))]

# ===== Database Sementara (In-Memory) =====
services = {
    "Netflix": {
        "1bulan": {"price": 25000, "stock": 3},
        "3bulan": {"price": 60000, "stock": 0}
    }
}
accounts = {
    "Netflix_1bulan": [
        "netflix_1@mail.com:pass1",
        "netflix_2@mail.com:pass2",
        "netflix_3@mail.com:pass3"
    ]
}
snk = "1. Akun hanya dapat digunakan oleh 1 orang.\n2. Tidak dapat ditukar atau dikembalikan.\n3. Bot tidak bertanggung jawab atas pemblokiran akun."

# ===== Fungsi Utama =====
def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    update.message.reply_text(
        f"Selamat datang, {user.first_name}! Silakan pilih layanan yang tersedia:\n"
        f"1. 🎬 Streaming: Netflix, Spotify\n"
        f"2. 💻 Software: Office, Windows\n"
        f"3. 🎮 Game: Steam, Riot Points\n\n"
        f"Ketik /akun untuk melihat daftar layanan."
    )

def akun(update: Update, context: CallbackContext):
    daftar = "\n".join([f"- {k}" for k in services.keys()])
    update.message.reply_text(f"Pilih layanan yang tersedia:\n{daftar}")

def pilih_layanan(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Gunakan format: /pilih_layanan <nama_layanan>")
        return
    service = context.args[0]
    if service not in services:
        update.message.reply_text("Layanan tidak ditemukan.")
        return
    
    msg = f"📦 {service.upper()}:\n"
    for paket, info in services[service].items():
        status = "✅" if info["stock"] > 0 else "❌"
        msg += f"- {paket} - Rp{info['price']} (Stok: {info['stock']}) {status}\n"
    update.message.reply_text(msg)

def beli_akun(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        update.message.reply_text("Gunakan format: /beli_akun <layanan> <paket>")
        return

    service = context.args[0]
    package = context.args[1]

    if service not in services or package not in services[service]:
        update.message.reply_text("Layanan atau paket tidak valid.")
        return

    if services[service][package]["stock"] > 0:
        key = f"{service}_{package}"
        if key not in accounts or not accounts[key]:
            update.message.reply_text("❌ STOK HABIS! Silakan pilih paket lain.")
            return

        akun = accounts[key].pop(0)
        services[service][package]["stock"] -= 1

        update.message.reply_text(
            f"✅ AKUN {service.upper()}:\n"
            f"{akun}\n\n"
            f"📝 Syarat dan Ketentuan:\n{snk}"
        )
    else:
        update.message.reply_text("❌ STOK HABIS! Silakan pilih paket lain.")

# ===== ADMIN =====

def is_admin(user_id):
    return user_id in admin_ids

def tambah_layanan(update: Update, context: CallbackContext):
    if not is_admin(update.message.from_user.id):
        return
    try:
        nama = context.args[0]
        deskripsi = context.args[1]
        kategori = context.args[2]
        services[nama] = {}
        update.message.reply_text(f"Layanan {nama} berhasil ditambahkan.")
    except:
        update.message.reply_text("Format: /tambah_layanan <nama> <deskripsi> <kategori>")

def tambah_akun(update: Update, context: CallbackContext):
    if not is_admin(update.message.from_user.id):
        return
    try:
        layanan = context.args[0]
        paket = context.args[1]
        data = context.args[2]

        key = f"{layanan}_{paket}"
        if key not in accounts:
            accounts[key] = []
        accounts[key].append(data)
        update.message.reply_text(f"Akun berhasil ditambahkan ke {layanan} paket {paket}.")
    except:
        update.message.reply_text("Format: /tambah_akun <layanan> <paket> <email:password>")

def tambah_stok(update: Update, context: CallbackContext):
    if not is_admin(update.message.from_user.id):
        return
    try:
        layanan = context.args[0]
        paket = context.args[1]
        jumlah = int(context.args[2])

        services[layanan][paket]["stock"] += jumlah
        update.message.reply_text(f"Stok {layanan} paket {paket} ditambah sebanyak {jumlah}.")
    except:
        update.message.reply_text("Format: /tambah_stok <layanan> <paket> <jumlah>")

def cek_stok(update: Update, context: CallbackContext):
    if not is_admin(update.message.from_user.id):
        return
    try:
        layanan = context.args[0]
        msg = f"📊 STOK {layanan.upper()}:\n"
        for paket, info in services[layanan].items():
            msg += f"- {paket}: {info['stock']} akun\n"
        update.message.reply_text(msg)
    except:
        update.message.reply_text("Format: /stok <layanan>")

def tambah_snk(update: Update, context: CallbackContext):
    if not is_admin(update.message.from_user.id):
        return
    global snk
    snk = " ".join(context.args)
    update.message.reply_text("Syarat dan Ketentuan berhasil diperbarui.")

# ===== Set Up Bot =====
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("akun", akun))
    dp.add_handler(CommandHandler("pilih_layanan", pilih_layanan))
    dp.add_handler(CommandHandler("beli_akun", beli_akun))

    # Admin Commands
    dp.add_handler(CommandHandler("tambah_layanan", tambah_layanan))
    dp.add_handler(CommandHandler("tambah_akun", tambah_akun))
    dp.add_handler(CommandHandler("tambah_stok", tambah_stok))
    dp.add_handler(CommandHandler("stok", cek_stok))
    dp.add_handler(CommandHandler("tambah_snk", tambah_snk))

    port = int(os.environ.get("PORT", 8443))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
