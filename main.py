# Bot Telegram Jual Akun Premium Otomatis + Admin Web
# Dibuat dengan python-telegram-bot dan Flask

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from flask import Flask, request, render_template_string, redirect
import threading
import json
import time

# ====== KONFIGURASI ======
TOKEN = "YOUR_BOT_TOKEN"  # Ganti dengan token bot Anda
ADMIN_CHAT_ID = 123456789  # Ganti dengan chat ID admin
DATA_FILE = "produk.json"

# ====== FUNGSI DATA ======
def load_products():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_products(products):
    with open(DATA_FILE, 'w') as f:
        json.dump(products, f, indent=2)

# Simulasi cek pembayaran otomatis (dummy)
def cek_pembayaran(user_id, produk_id):
    time.sleep(5)  # simulasi delay pengecekan
    return True  # anggap selalu sukses

# ====== HANDLER TELEGRAM ======
def start(update: Update, context: CallbackContext):
    msg = (
        "Hallo, Selamat Datang di Store!\n\n"
        "Kami menjual akun premium seperti Netflix, Canva, dll.\n"
        "Silakan pilih produk yang tersedia."
    )
    keyboard = [[InlineKeyboardButton("Lihat Produk", callback_data="list_produk")]]
    update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

def list_produk(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    products = load_products()
    keyboard = []
    for key, item in products.items():
        keyboard.append([InlineKeyboardButton(f"{key}. {item['name']}", callback_data=f"produk_{key}")])
    query.edit_message_text("Pilih produk:", reply_markup=InlineKeyboardMarkup(keyboard))

def detail_produk(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    produk_id = query.data.split("_")[1]
    products = load_products()
    produk = products.get(produk_id)
    if not produk:
        query.edit_message_text("Produk tidak ditemukan.")
        return

    teks = (
        f"Nama Produk: {produk['name']}\n"
        f"Detail: {produk['detail']}\n"
        f"Stok: {produk['stok']}\n"
        f"Desk: {produk['deskripsi']}\n"
        f"Harga: Rp {produk['harga']}"
    )
    keyboard = [
        [InlineKeyboardButton(f"Beli ({produk['detail']} - Rp {produk['harga']})", callback_data=f"beli_{produk_id}")],
        [InlineKeyboardButton("Kembali", callback_data="list_produk")]
    ]
    query.edit_message_text(teks, reply_markup=InlineKeyboardMarkup(keyboard))

def beli_produk(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    produk_id = query.data.split("_")[1]
    user = query.from_user
    products = load_products()
    produk = products.get(produk_id)

    teks = (
        f"Silakan bayar sebesar Rp {produk['harga']} ke rekening berikut:\n"
        f"🏦 BCA 1234567890 a.n STORE\n\n"
        f"Bot akan otomatis mendeteksi pembayaran dalam beberapa menit."
    )
    query.edit_message_text(teks)

    if cek_pembayaran(user.id, produk_id):
        if produk['akun']:
            akun = produk['akun'].pop(0)
            produk['stok'] -= 1
            save_products(products)
            context.bot.send_message(user.id,
                f"✅ Pembayaran diterima!\n\n"
                f"Berikut akun Anda:\n👤 Email: {akun['email']}\n🔐 Password: {akun['pass']}"
            )
            context.bot.send_message(ADMIN_CHAT_ID,
                f"[ORDER] @{user.username} membeli {produk['name']} - {produk['detail']}\nStok tersisa: {produk['stok']}"
            )
        else:
            context.bot.send_message(user.id, "⚠️ Maaf, stok habis.")

# ====== FLASK WEB DASHBOARD ======
app = Flask(__name__)

TEMPLATE = '''
<h2>Dashboard Admin</h2>
<form method="post">
  {% for id, p in products.items() %}
  <h3>Produk ID {{ id }}</h3>
  Nama: <input name="name_{{ id }}" value="{{ p.name }}"><br>
  Detail: <input name="detail_{{ id }}" value="{{ p.detail }}"><br>
  Deskripsi: <input name="deskripsi_{{ id }}" value="{{ p.deskripsi }}"><br>
  Harga: <input name="harga_{{ id }}" value="{{ p.harga }}"><br>
  Stok: <input name="stok_{{ id }}" value="{{ p.stok }}"><br>
  <br>
  {% endfor %}
  <button type="submit">Simpan</button>
</form>
'''

@app.route('/', methods=['GET', 'POST'])
def admin_dashboard():
    products = load_products()
    if request.method == 'POST':
        for pid in products:
            products[pid]['name'] = request.form.get(f'name_{pid}')
            products[pid]['detail'] = request.form.get(f'detail_{pid}')
            products[pid]['deskripsi'] = request.form.get(f'deskripsi_{pid}')
            products[pid]['harga'] = int(request.form.get(f'harga_{pid}'))
            products[pid]['stok'] = int(request.form.get(f'stok_{pid}'))
        save_products(products)
        return redirect('/')
    return render_template_string(TEMPLATE, products=products)

# ====== JALANKAN BOT DAN WEB ======
def run_bot():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(list_produk, pattern="^list_produk$"))
    dp.add_handler(CallbackQueryHandler(detail_produk, pattern="^produk_\\d+$"))
    dp.add_handler(CallbackQueryHandler(beli_produk, pattern="^beli_\\d+$"))

    updater.start_polling()
    updater.idle()

def run_web():
    app.run(host='0.0.0.0', port=8080)

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    run_web()
