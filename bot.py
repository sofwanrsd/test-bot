import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, CallbackQueryHandler
)
import pymongo  # Untuk database MongoDB
from datetime import datetime, timedelta

# Konfigurasi
TOKEN = "TOKEN_BOT_ANDA"
ADMIN_IDS = [123456789]  # Ganti dengan chat ID admin
PAYMENT_DURATION = 15  # Menit (batas waktu pembayaran)

# Koneksi MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["premium_accounts_bot"]

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== FUNGSI UTAMA ======================

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    if user.id in ADMIN_IDS:
        # Tampilan khusus admin
        keyboard = [
            [InlineKeyboardButton("➕ Tambah Akun", callback_data="admin_add")],
            [InlineKeyboardButton("📊 Laporan", callback_data="admin_report")]
        ]
        update.message.reply_text(
            f"👑 *MODE ADMIN* - Hai {user.first_name}!\n"
            "Gunakan menu di bawah:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        # Tampilan user biasa
        keyboard = [
            [InlineKeyboardButton("🎬 Netflix", callback_data="category_netflix")],
            [InlineKeyboardButton("🎵 Spotify", callback_data="category_spotify")],
            [InlineKeyboardButton("📺 YouTube", callback_data="category_youtube")]
        ]
        update.message.reply_text(
            f"👋 Hai {user.first_name}!\n"
            "💎 *TOKO AKUN PREMIUM*\n\n"
            "Pilih kategori:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

def handle_text(update: Update, context: CallbackContext):
    text = update.message.text.lower()
    
    # Cek jika user mengetik langsung nama layanan
    services = ["netflix", "spotify", "youtube", "zoom"]
    for service in services:
        if service in text:
            show_products(update, context, service)
            return
    
    update.message.reply_text("🔍 Ketik nama layanan (contoh: 'Netflix')")

def show_products(update: Update, context: CallbackContext, service: str):
    # Ambil produk dari database
    products = list(db.accounts.find({"service": service, "status": "available"}))
    
    if not products:
        update.message.reply_text(f"😢 Stok {service} kosong. Coba lain kali!")
        return
    
    # Buat tombol pilihan durasi
    keyboard = []
    for product in products[:3]:  # Tampilkan max 3 pilihan
        keyboard.append([
            InlineKeyboardButton(
                f"{product['duration']} - Rp{product['price']}",
                callback_data=f"select_{product['_id']}"
            )
        ])
    
    update.message.reply_text(
        f"🎯 *{service.upper()} PREMIUM*\n"
        "Pilih paket:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

def payment_confirmation(update: Update, context: CallbackContext, product_id: str):
    # Simpan data sementara
    product = db.accounts.find_one({"_id": product_id})
    context.user_data["pending_payment"] = {
        "product_id": product_id,
        "expires": datetime.now() + timedelta(minutes=PAYMENT_DURATION)
    }
    
    # Tampilkan instruksi pembayaran
    keyboard = [
        [InlineKeyboardButton("✅ Sudah Bayar", callback_data="confirm_payment")],
        [InlineKeyboardButton("❌ Batalkan", callback_data="cancel_payment")]
    ]
    
    update.callback_query.edit_message_text(
        f"💳 *PEMBAYARAN*\n"
        f"Produk: {product['service']} {product['duration']}\n"
        f"Total: Rp{product['price']}\n\n"
        "🔧 Metode Pembayaran:\n"
        "1. QRIS: https://qr-code-generator.com/example\n"
        "2. Transfer Bank: BCA 123-456-7890\n\n"
        f"⏳ Batas waktu: {PAYMENT_DURATION} menit",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

def send_account(update: Update, context: CallbackContext):
    query = update.callback_query
    user_data = context.user_data
    
    # Ambil akun dari database
    product = db.accounts.find_one({"_id": user_data["pending_payment"]["product_id"]})
    
    # Update status akun
    db.accounts.update_one(
        {"_id": product["_id"]},
        {"$set": {"status": "sold", "sold_to": query.from_user.id}}
    )
    
    # Kirim akun ke user
    query.edit_message_text(
        f"🎉 *PEMBELIAN BERHASIL!*\n\n"
        f"🔑 {product['service'].upper()} ACCOUNT:\n"
        f"📧 Email: {product['email']}\n"
        f"🔒 Password: {product['password']}\n\n"
        f"⏳ Berlaku hingga: {product['expiry_date']}\n\n"
        "⚠️ Segera ganti password setelah login!",
        parse_mode="Markdown"
    )
    
    # Hapus data sementara
    del context.user_data["pending_payment"]

# ====================== ADMIN FUNCTIONS ======================

def admin_add_account(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "📥 Format tambah akun:\n"
        "/tambah_akun <layanan> <email> <password> <durasi> <harga>\n\n"
        "Contoh:\n"
        "/tambah_akun netflix acc1@mail.com pass123 \"1 Bulan\" 50000"
    )

def tambah_akun(update: Update, context: CallbackContext):
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ Akses ditolak!")
        return
    
    try:
        args = context.args
        if len(args) != 5:
            raise ValueError("Format salah!")
        
        new_account = {
            "service": args[0].lower(),
            "email": args[1],
            "password": args[2],
            "duration": args[3],
            "price": int(args[4]),
            "status": "available",
            "added_at": datetime.now(),
            "expiry_date": datetime.now() + timedelta(days=30)  # Contoh: 30 hari
        }
        
        # Simpan ke database
        db.accounts.insert_one(new_account)
        
        update.message.reply_text(
            f"✅ Akun {new_account['service']} berhasil ditambahkan!\n"
            f"📧 {new_account['email']}\n"
            f"💰 Rp{new_account['price']}"
        )
    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}")

# ====================== HANDLER ======================

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    # Command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("tambah_akun", tambah_akun))

    # Message handlers
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    # Callback handlers
    dp.add_handler(CallbackQueryHandler(
        lambda update, ctx: show_products(update, ctx, update.callback_query.data.split("_")[1]),
        pattern="^category_"
    ))
    dp.add_handler(CallbackQueryHandler(
        lambda update, ctx: payment_confirmation(update, ctx, update.callback_query.data.split("_")[1]),
        pattern="^select_"
    ))
    dp.add_handler(CallbackQueryHandler(send_account, pattern="^confirm_payment$"))
    dp.add_handler(CallbackQueryHandler(admin_add_account, pattern="^admin_add$"))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
