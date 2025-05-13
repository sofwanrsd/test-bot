import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize bot
TOKEN = os.getenv('TOKEN')
bot = telebot.TeleBot(TOKEN)

# Database produk (bisa diganti dengan database eksternal nanti)
produk = {
    'app1': {
        'nama': 'Aplikasi Produktivitas Premium',
        'harga': 'Rp 50.000',
        'deskripsi': 'Fitur lengkap untuk meningkatkan produktivitas harian Anda',
        'fitur': [
            'Task management',
            'Kalender pintar',
            'Analisis produktivitas',
            'Sync multi-device'
        ]
    },
    'app2': {
        'nama': 'Aplikasi Foto Pro',
        'harga': 'Rp 75.000',
        'deskripsi': 'Edit foto profesional dengan mudah',
        'fitur': [
            '100+ filter eksklusif',
            'Tools edit profesional',
            'Export kualitas tinggi',
            'Preset khusus'
        ]
    }
}

# Database pesanan (simpan di memory, bisa hilang saat restart)
orders = {}

# Handler perintah /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("📱 Lihat Produk", callback_data="lihat_produk"),
        InlineKeyboardButton("ℹ️ Tentang Kami", callback_data="tentang"),
        InlineKeyboardButton("🛒 Keranjang", callback_data="keranjang"),
        InlineKeyboardButton("❓ Bantuan", callback_data="bantuan")
    )
    bot.send_message(
        message.chat.id,
        "🛍️ *Selamat datang di Toko Aplikasi Premium* 🛍️\n\n"
        "Kami menyediakan berbagai aplikasi premium berkualitas dengan harga terjangkau.\n\n"
        "Silakan pilih menu di bawah:",
        parse_mode='Markdown',
        reply_markup=markup
    )

# Handler callback query
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        if call.data == "lihat_produk":
            show_products(call.message)
        elif call.data == "tentang":
            show_about(call.message)
        elif call.data == "bantuan":
            show_help(call.message)
        elif call.data == "keranjang":
            show_cart(call.message)
        elif call.data == "kembali":
            send_welcome(call.message)
        elif call.data.startswith("detail_"):
            product_id = call.data.split("_")[1]
            show_product_detail(call.message, product_id)
        elif call.data.startswith("beli_"):
            product_id = call.data.split("_")[1]
            add_to_cart(call.message, product_id)
        elif call.data == "checkout":
            process_checkout(call.message)
        elif call.data.startswith("hapus_"):
            product_id = call.data.split("_")[1]
            remove_from_cart(call.message, product_id)
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error: {e}")
        bot.send_message(call.message.chat.id, "⚠️ Terjadi kesalahan. Silakan coba lagi.")

def show_products(message):
    markup = InlineKeyboardMarkup()
    for product_id, product in produk.items():
        markup.add(
            InlineKeyboardButton(
                f"{product['nama']} - {product['harga']}",
                callback_data=f"detail_{product_id}"
            )
        )
    markup.add(InlineKeyboardButton("🔙 Kembali", callback_data="kembali"))
    
    bot.send_message(
        message.chat.id,
        "📋 *Daftar Aplikasi Premium Kami*:\n\n"
        "Pilih aplikasi untuk melihat detail:",
        parse_mode='Markdown',
        reply_markup=markup
    )

def show_product_detail(message, product_id):
    product = produk.get(product_id)
    if not product:
        bot.send_message(message.chat.id, "Produk tidak ditemukan")
        return
    
    features = "\n".join([f"✔️ {fitur}" for fitur in product['fitur']])
    
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("🛒 Tambah ke Keranjang", callback_data=f"beli_{product_id}"),
        InlineKeyboardButton("🔙 Kembali ke Produk", callback_data="lihat_produk")
    )
    
    bot.send_message(
        message.chat.id,
        f"*{product['nama']}*\n\n"
        f"💵 *Harga*: {product['harga']}\n\n"
        f"📝 *Deskripsi*: {product['deskripsi']}\n\n"
        f"✨ *Fitur Unggulan*:\n{features}\n\n"
        "Pilih opsi di bawah:",
        parse_mode='Markdown',
        reply_markup=markup
    )

def add_to_cart(message, product_id):
    chat_id = message.chat.id
    if chat_id not in orders:
        orders[chat_id] = {'items': [], 'total': 0}
    
    product = produk.get(product_id)
    if not product:
        bot.send_message(chat_id, "Produk tidak ditemukan")
        return
    
    # Simpan harga sebagai angka untuk perhitungan
    harga_num = int(product['harga'].replace('Rp ', '').replace('.', ''))
    
    orders[chat_id]['items'].append({
        'id': product_id,
        'nama': product['nama'],
        'harga': harga_num
    })
    orders[chat_id]['total'] += harga_num
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🛒 Lihat Keranjang", callback_data="keranjang"),
        InlineKeyboardButton("📱 Lanjut Belanja", callback_data="lihat_produk")
    )
    
    bot.send_message(
        chat_id,
        f"✅ *{product['nama']}* telah ditambahkan ke keranjang!\n\n"
        f"Harga: {product['harga']}",
        parse_mode='Markdown',
        reply_markup=markup
    )

def show_cart(message):
    chat_id = message.chat.id
    if chat_id not in orders or not orders[chat_id]['items']:
        bot.send_message(chat_id, "🛒 Keranjang Anda kosong")
        return
    
    items_text = ""
    for idx, item in enumerate(orders[chat_id]['items'], 1):
        items_text += f"{idx}. {item['nama']} - Rp {item['harga']:,}\n"
    
    total = orders[chat_id]['total']
    
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    buttons = []
    for idx, item in enumerate(orders[chat_id]['items'], 1):
        buttons.append(InlineKeyboardButton(f"❌ Hapus {idx}", callback_data=f"hapus_{item['id']}"))
    
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("💳 Checkout", callback_data="checkout"))
    markup.add(InlineKeyboardButton("🔙 Kembali", callback_data="kembali"))
    
    bot.send_message(
        chat_id,
        f"🛒 *Keranjang Belanja*\n\n"
        f"{items_text}\n"
        f"💵 *Total*: Rp {total:,}",
        parse_mode='Markdown',
        reply_markup=markup
    )

def remove_from_cart(message, product_id):
    chat_id = message.chat.id
    if chat_id not in orders:
        bot.send_message(chat_id, "Keranjang kosong")
        return
    
    for idx, item in enumerate(orders[chat_id]['items']):
        if item['id'] == product_id:
            removed_item = orders[chat_id]['items'].pop(idx)
            orders[chat_id]['total'] -= removed_item['harga']
            break
    
    show_cart(message)

def process_checkout(message):
    chat_id = message.chat.id
    if chat_id not in orders or not orders[chat_id]['items']:
        bot.send_message(chat_id, "Keranjang kosong, tidak bisa checkout")
        return
    
    total = orders[chat_id]['total']
    
    # Informasi pembayaran (sesuaikan dengan metode pembayaran Anda)
    payment_info = (
        "🚀 *Proses Checkout*\n\n"
        "Silakan lakukan pembayaran ke:\n\n"
        "💳 *Bank*: BCA (Bank Central Asia)\n"
        "📌 *Nomor Rekening*: 1234 5678 9012\n"
        "👤 *Atas Nama*: Nama Toko Anda\n\n"
        f"💵 *Total Pembayaran*: Rp {total:,}\n\n"
        "Setelah melakukan pembayaran, silakan konfirmasi dengan mengirim bukti transfer ke @admin.\n\n"
        "Terima kasih telah berbelanja di toko kami!"
    )
    
    # Kosongkan keranjang setelah checkout
    orders[chat_id] = {'items': [], 'total': 0}
    
    bot.send_message(
        chat_id,
        payment_info,
        parse_mode='Markdown'
    )

def show_about(message):
    bot.send_message(
        message.chat.id,
        "🏢 *Tentang Kami*\n\n"
        "Kami adalah penyedia aplikasi premium berkualitas sejak 2023.\n\n"
        "📱 *Visi*: Memberikan solusi aplikasi terbaik dengan harga terjangkau\n"
        "🌟 *Misi*: Membantu produktivitas dan kreativitas pengguna\n\n"
        "Untuk informasi lebih lanjut, hubungi @admin",
        parse_mode='Markdown'
    )

def show_help(message):
    bot.send_message(
        message.chat.id,
        "❓ *Bantuan*\n\n"
        "Berikut panduan penggunaan bot:\n\n"
        "1. Pilih 'Lihat Produk' untuk melihat daftar aplikasi\n"
        "2. Klik produk untuk melihat detail\n"
        "3. Tambahkan ke keranjang jika ingin membeli\n"
        "4. Lakukan checkout dari menu keranjang\n"
        "5. Ikuti instruksi pembayaran\n\n"
        "Jika ada pertanyaan, silakan hubungi @admin",
        parse_mode='Markdown'
    )

# Handle errors
@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    bot.send_message(
        message.chat.id,
        "Maaf, saya tidak mengerti perintah itu.\n"
        "Silakan gunakan menu yang tersedia atau ketik /start untuk memulai."
    )

# Jalankan bot
if __name__ == '__main__':
    print("Bot berjalan...")
    bot.infinity_polling()
