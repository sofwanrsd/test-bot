import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, CallbackQueryHandler
)
from datetime import datetime, timedelta

# Konfigurasi
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]  # Format: "123,456"
JSON_DB = "accounts.json"

# Inisialisasi database JSON
def init_db():
    if not os.path.exists(JSON_DB):
        with open(JSON_DB, "w") as f:
            json.dump([], f)

def load_db():
    with open(JSON_DB, "r") as f:
        return json.load(f)

def save_db(data):
    with open(JSON_DB, "w") as f:
        json.dump(data, f, indent=2)

# ====================== FUNGSI UTAMA ======================
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    if user.id in ADMIN_IDS:
        update.message.reply_text(
            f"👑 *ADMIN MODE* - Hai {user.first_name}!\n"
            "Gunakan perintah:\n"
            "/tambah_akun - Tambah akun baru\n"
            "/list_akun - Lihat stok",
            parse_mode="Markdown"
        )
    else:
        update.message.reply_text(
            f"👋 Hai {user.first_name}!\n"
            "💎 *TOKO AKUN PREMIUM*\n\n"
            "Cari akun dengan mengetik:\n"
            "Contoh: 'Netflix', 'Spotify', 'YouTube'",
            parse_mode="Markdown"
        )

def handle_search(update: Update, context: CallbackContext):
    text = update.message.text.lower()
    accounts = load_db()
    
    available = [acc for acc in accounts if acc["service"].lower() == text and acc["status"] == "available"]
    
    if not available:
        update.message.reply_text("😢 Stok kosong. Coba layanan lain!")
        return
    
    keyboard = []
    for acc in available[:3]:  # Tampilkan max 3 akun
        keyboard.append([
            InlineKeyboardButton(
                f"{acc['service']} ({acc['duration']}) - Rp{acc['price']}",
                callback_data=f"buy_{acc['id']}"
            )
        ])
    
    update.message.reply_text(
        f"🔍 *{text.upper()} PREMIUM* tersedia:\n"
        "Pilih paket:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

def process_payment(update: Update, context: CallbackContext):
    query = update.callback_query
    account_id = int(query.data.split("_")[1])
    
    accounts = load_db()
    account = next((acc for acc in accounts if acc["id"] == account_id), None)
    
    if not account:
        query.edit_message_text("❌ Akun tidak tersedia lagi")
        return
    
    # Simpan data pembelian sementara
    context.user_data["pending_payment"] = {
        "account_id": account_id,
        "expires": datetime.now() + timedelta(minutes=15)
    }
    
    query.edit_message_text(
        f"💳 *PEMBAYARAN*\n"
        f"Layanan: {account['service']} {account['duration']}\n"
        f"Harga: Rp{account['price']}\n\n"
        "🔄 Metode Pembayaran:\n"
        "1. QRIS: [Kode QR]\n"
        "2. Transfer: BCA 1234567890\n\n"
        "⚠️ Batas waktu: 15 menit\n\n"
        "Setelah bayar, klik tombol dibawah:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Konfirmasi Pembayaran", callback_data=f"confirm_{account_id}")],
            [InlineKeyboardButton("❌ Batalkan", callback_data="cancel")]
        ]),
        parse_mode="Markdown"
    )

def send_account(update: Update, context: CallbackContext):
    query = update.callback_query
    account_id = int(query.data.split("_")[1])
    
    accounts = load_db()
    account = next((acc for acc in accounts if acc["id"] == account_id), None)
    
    if not account:
        query.edit_message_text("❌ Akun tidak ditemukan")
        return
    
    # Update status akun
    account["status"] = "sold"
    account["sold_at"] = datetime.now().isoformat()
    save_db(accounts)
    
    # Kirim akun ke user
    query.edit_message_text(
        f"🎉 *PEMBELIAN BERHASIL!*\n\n"
        f"🔑 {account['service'].upper()} ACCOUNT:\n"
        f"📧 Email: {account['email']}\n"
        f"🔒 Password: {account['password']}\n\n"
        f"⏳ Berlaku hingga: {account['expiry_date']}\n\n"
        "⚠️ Segera ganti password setelah login!\n\n"
        "Gunakan /help jika ada masalah",
        parse_mode="Markdown"
    )

# ====================== ADMIN FUNCTIONS ======================
def add_account(update: Update, context: CallbackContext):
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ Akses ditolak!")
        return
    
    args = context.args
    if len(args) < 5:
        update.message.reply_text(
            "Format: /tambah_akun <layanan> <email> <password> <durasi> <harga>\n"
            "Contoh: /tambah_akun netflix acc1@mail.com pass123 \"1 Bulan\" 50000"
        )
        return
    
    accounts = load_db()
    new_id = max([acc["id"] for acc in accounts], default=0) + 1
    
    new_account = {
        "id": new_id,
        "service": args[0],
        "email": args[1],
        "password": args[2],
        "duration": args[3],
        "price": int(args[4]),
        "status": "available",
        "added_at": datetime.now().isoformat(),
        "expiry_date": (datetime.now() + timedelta(days=30)).isoformat()  # Contoh: 30 hari
    }
    
    accounts.append(new_account)
    save_db(accounts)
    
    update.message.reply_text(
        f"✅ Akun {new_account['service']} berhasil ditambahkan!\n"
        f"ID: {new_account['id']}\n"
        f"Email: {new_account['email']}\n"
        f"Harga: Rp{new_account['price']}"
    )

def list_accounts(update: Update, context: CallbackContext):
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ Akses ditolak!")
        return
    
    accounts = load_db()
    if not accounts:
        update.message.reply_text("📭 Database kosong")
        return
    
    text = "📦 DAFTAR AKUN TERSEDIA:\n\n"
    for acc in accounts:
        status = "✅ TERSEDIA" if acc["status"] == "available" else "❌ TERJUAL"
        text += (
            f"ID: {acc['id']}\n"
            f"Layanan: {acc['service']}\n"
            f"Email: {acc['email']}\n"
            f"Status: {status}\n"
            f"Ditambahkan: {acc['added_at'][:10]}\n\n"
        )
    
    update.message.reply_text(text)

# ====================== SETUP BOT ======================
def main():
    init_db()  # Pastikan file JSON ada
    
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    # Command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("tambah_akun", add_account))
    dp.add_handler(CommandHandler("list_akun", list_accounts))

    # Message handlers
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_search))

    # Callback handlers
    dp.add_handler(CallbackQueryHandler(process_payment, pattern="^buy_"))
    dp.add_handler(CallbackQueryHandler(send_account, pattern="^confirm_"))

    # Start bot
    print("Bot started...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
