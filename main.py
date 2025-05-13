import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Ganti dengan token bot Telegram Anda
TOKEN = 'TOKEN_BOT_ANDA'
bot = telebot.TeleBot(TOKEN)

# Daftar aplikasi premium yang dijual
produk = {
    'app1': {
        'nama': 'Aplikasi Produktivitas Premium',
        'harga': 'Rp 50.000',
        'deskripsi': 'Fitur lengkap untuk meningkatkan produktivitas harian Anda'
    },
    'app2': {
        'nama': 'Aplikasi Foto Pro',
        'harga': 'Rp 75.000',
        'deskripsi': 'Edit foto profesional dengan mudah'
    }
}

# Handler untuk perintah /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("Lihat Produk", callback_data="lihat_produk"),
        InlineKeyboardButton("Bantuan", callback_data="bantuan")
    )
    bot.send_message(
        message.chat.id,
        "Halo! Selamat datang di toko aplikasi premium kami.\n\n" +
        "Silakan pilih menu di bawah:",
        reply_markup=markup
    )

# Handler untuk callback query
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "lihat_produk":
        show_products(call.message)
    elif call.data == "bantuan":
        bot.send_message(call.message.chat.id, "Untuk bantuan, silakan hubungi @admin")
    elif call.data.startswith("beli_"):
        product_id = call.data.split("_")[1]
        process_order(call.message, product_id)

def show_products(message):
    markup = InlineKeyboardMarkup()
    for product_id, product in produk.items():
        markup.add(
            InlineKeyboardButton(
                f"{product['nama']} - {product['harga']}",
                callback_data=f"beli_{product_id}"
            )
        )
    markup.add(InlineKeyboardButton("Kembali", callback_data="kembali"))
    
    bot.send_message(
        message.chat.id,
        "Daftar Aplikasi Premium Kami:",
        reply_markup=markup
    )

def process_order(message, product_id):
    product = produk.get(product_id)
    if product:
        bot.send_message(
            message.chat.id,
            f"Anda akan membeli:\n\n" +
            f"📱 {product['nama']}\n" +
            f"💵 Harga: {product['harga']}\n\n" +
            f"Silakan transfer ke:\n" +
            "Bank: BCA\n" +
            "No Rek: 1234567890\n" +
            "a.n: Nama Anda\n\n" +
            "Setelah transfer, kirim bukti pembayaran ke admin @admin"
        )
    else:
        bot.send_message(message.chat.id, "Produk tidak ditemukan")

# Jalankan bot
print("Bot berjalan...")
bot.polling()
