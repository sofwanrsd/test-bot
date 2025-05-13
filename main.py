# main.py
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from dotenv import load_dotenv  # Tambahkan di bagian atas

# Konfigurasi
# Load .env file jika ada (hanya untuk development)
load_dotenv()

# Ambil variabel environment dengan error handling
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN harus diset di environment variables!")

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))  # Default: 0 (tidak ada admin)
PORT = int(os.getenv("PORT", "8080"))  # Default: 8080

# Inisialisasi Flask
app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('accounts.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def dashboard():
    conn = get_db_connection()
    accounts = conn.execute('SELECT * FROM accounts').fetchall()
    conn.close()
    return render_template('dashboard.html', accounts=accounts)

@app.route('/add', methods=('GET', 'POST'))
def add_account():
    if request.method == 'POST':
        service = request.form['service'].lower()
        email = request.form['email']
        password = request.form['password']
        duration = request.form['duration']

        conn = get_db_connection()
        conn.execute('INSERT INTO accounts (service, email, password, duration) VALUES (?, ?, ?, ?)',
                     (service, email, password, duration))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('add_account.html')

# Telegram Bot
accounts_by_service = {}

def load_accounts():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM accounts').fetchall()
    conn.close()
    accounts_by_service.clear()
    for row in rows:
        accounts_by_service.setdefault(row['service'], []).append(dict(row))

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    update.message.reply_text(
        f"\U0001F44B Hai {user.first_name}!\n\n"
        "\U0001F48E *PREMIUM ACCOUNT STORE*\n"
        "Bot otomatis 24/7 untuk pembelian akun:\n"
        "• Netflix, Spotify, YouTube Premium\n"
        "• Windows, Adobe, Steam, dll\n\n"
        "\u2728 *INSTANT DELIVERY* setelah pembayaran!\n\n"
        "Ketik nama layanan seperti `Netflix`, `Spotify`, dll.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("\U0001F3AC Netflix", callback_data='netflix')],
            [InlineKeyboardButton("\U0001F3B5 Spotify", callback_data='spotify')]
        ])
    )

def handle_query(update: Update, context: CallbackContext):
    query = update.callback_query
    service = query.data
    show_accounts(query.message, service)

def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.lower()
    if text in accounts_by_service:
        show_accounts(update.message, text)

def show_accounts(msg, service):
    load_accounts()
    if service not in accounts_by_service or not accounts_by_service[service]:
        msg.reply_text(f"\u274C Stok {service.capitalize()} kosong.")
        return

    keyboard = []
    for idx, acc in enumerate(accounts_by_service[service]):
        label = f"{acc['duration']} - {acc['email'].split('@')[0]}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"buy|{service}|{acc['id']}")])

    msg.reply_text(f"\U0001F4E6 *{service.upper()}* tersedia:",
                   parse_mode='Markdown',
                   reply_markup=InlineKeyboardMarkup(keyboard))

def handle_buy(update: Update, context: CallbackContext):
    query = update.callback_query
    _, service, acc_id = query.data.split("|")
    acc_id = int(acc_id)

    conn = get_db_connection()
    acc = conn.execute('SELECT * FROM accounts WHERE id = ?', (acc_id,)).fetchone()
    if acc:
        conn.execute('DELETE FROM accounts WHERE id = ?', (acc_id,))
        conn.commit()
        conn.close()
        # Kirim ke user
        query.message.reply_text(
            f"\u2705 *PEMBELIAN BERHASIL*\n"
            f"Layanan: {acc['service'].capitalize()} {acc['duration']}\n"
            f"Email: `{acc['email']}`\nPassword: `{acc['password']}`\n",
            parse_mode="Markdown")
        # Notifikasi ke admin
        context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"\U0001F4E2 ORDER: {acc['service']} {acc['duration']} oleh @{query.from_user.username}"
        )
    else:
        query.message.reply_text("\u274C Maaf, akun sudah dibeli orang lain.")

# Web server thread
Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))).start()

# Telegram bot start
updater = Updater(BOT_TOKEN)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(CallbackQueryHandler(handle_query, pattern="^(netflix|spotify)$"))
dp.add_handler(CallbackQueryHandler(handle_buy, pattern="^buy\\|"))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

load_accounts()
updater.start_polling()
updater.idle()
