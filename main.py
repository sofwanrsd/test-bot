import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Load env variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))

# Data files
SERVICES_FILE = "data/services.json"
ACCOUNTS_FILE = "data/accounts.json"
SNK_TEXT = "1. Akun hanya dapat digunakan oleh 1 orang.\n2. Tidak dapat ditukar atau dikembalikan.\n3. Bot tidak bertanggung jawab atas pemblokiran akun."

# Helper functions
def load_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Selamat datang, {update.effective_user.first_name}!\n\n"
        "Silakan ketik /layanan untuk melihat daftar layanan yang tersedia."
    )

async def layanan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    services = load_json(SERVICES_FILE)
    if not services:
        await update.message.reply_text("Belum ada layanan tersedia.")
        return
    reply = "📦 Layanan Tersedia:\n"
    for svc, detail in services.items():
        reply += f"- {svc}: {detail['deskripsi']}\n"
    await update.message.reply_text(reply)

async def paket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Gunakan: /paket <NamaLayanan>")
        return

    layanan = args[0]
    services = load_json(SERVICES_FILE)
    if layanan not in services:
        await update.message.reply_text("Layanan tidak ditemukan.")
        return

    akun = load_json(ACCOUNTS_FILE)
    reply = f"📦 Paket untuk {layanan}:\n"
    for paket, akun_list in akun.get(layanan, {}).items():
        stok = len(akun_list)
        status = "✅" if stok > 0 else "❌"
        harga = services[layanan]["paket"].get(paket, "Rp -")
        reply += f"- {paket} - {harga} (Stok: {stok}) {status}\n"

    await update.message.reply_text(reply)

async def beli(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Gunakan: /beli <Layanan> <Paket>")
        return

    layanan, paket = args[0], args[1]
    akun = load_json(ACCOUNTS_FILE)

    if layanan not in akun or paket not in akun[layanan] or not akun[layanan][paket]:
        await update.message.reply_text("❌ STOK HABIS atau layanan tidak ditemukan.")
        return

    akun_terpilih = akun[layanan][paket].pop(0)
    save_json(ACCOUNTS_FILE, akun)

    await update.message.reply_text(
        f"✅ Akun {layanan.upper()}:\n{akun_terpilih}\n\n📝 Syarat dan Ketentuan:\n{SNK_TEXT}"
    )

# ADMIN FUNCTIONS
async def tambah_layanan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Gunakan: /tambah_layanan <Nama> <Deskripsi> <Kategori>")
        return

    nama, deskripsi, kategori = args[0], args[1], args[2]
    data = load_json(SERVICES_FILE)
    data[nama] = {"deskripsi": deskripsi, "kategori": kategori, "paket": {}}
    save_json(SERVICES_FILE, data)
    await update.message.reply_text(f"Layanan {nama} berhasil ditambahkan.")

async def tambah_paket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Gunakan: /tambah_paket <Layanan> <Paket> <Harga>")
        return
    layanan, paket, harga = args[0], args[1], args[2]

    data = load_json(SERVICES_FILE)
    if layanan not in data:
        await update.message.reply_text("Layanan tidak ditemukan.")
        return
    data[layanan]["paket"][paket] = harga
    save_json(SERVICES_FILE, data)
    await update.message.reply_text("Paket berhasil ditambahkan.")

async def tambah_akun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Gunakan: /tambah_akun <Layanan> <Paket> <Email:Password>")
        return
    layanan, paket, akun_str = args[0], args[1], args[2]
    data = load_json(ACCOUNTS_FILE)
    data.setdefault(layanan, {}).setdefault(paket, []).append(akun_str)
    save_json(ACCOUNTS_FILE, data)
    await update.message.reply_text("✅ Akun berhasil ditambahkan.")

# MAIN
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("layanan", layanan))
    app.add_handler(CommandHandler("paket", paket))
    app.add_handler(CommandHandler("beli", beli))

    # Admin commands
    app.add_handler(CommandHandler("tambah_layanan", tambah_layanan))
    app.add_handler(CommandHandler("tambah_paket", tambah_paket))
    app.add_handler(CommandHandler("tambah_akun", tambah_akun))

    print("Bot started...")
    app.run_polling()
