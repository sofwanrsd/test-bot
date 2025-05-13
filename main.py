import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart, Command
from aiogram import F
import asyncio

# === CONFIG ===
BOT_TOKEN = "ISI_TOKEN_BOT_MU"
ADMIN_ID = 123456789  # Ganti dengan ID Admin

# === LOAD PRODUK ===
def load_products():
    with open("products.json", "r") as f:
        return json.load(f)

# === BOT SETUP ===
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# === START ===
@dp.message(CommandStart())
async def start(message: types.Message):
    products = load_products()
    kb = InlineKeyboardBuilder()
    for product in products:
        kb.add(InlineKeyboardButton(text=product["name"], callback_data=f"product_{product['id']}"))
    await message.answer("👋 Selamat datang di Store Premium!\nSilakan pilih produk yang tersedia:", reply_markup=kb.as_markup())

# === PRODUK DETAIL ===
@dp.callback_query(F.data.startswith("product_"))
async def show_product(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = next((p for p in load_products() if p["id"] == product_id), None)
    if not product:
        await callback.message.answer("Produk tidak ditemukan.")
        return

    text = f"<b>{product['name']}</b>\n\n{product['description']}\nHarga: {product['price']}\n\nJika berminat, klik tombol di bawah 👇"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Saya Mau Order", callback_data=f"order_{product_id}")],
        [InlineKeyboardButton(text="🔙 Kembali", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)

# === ORDER MULAI ===
@dp.callback_query(F.data.startswith("order_"))
async def order_product(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = next((p for p in load_products() if p["id"] == product_id), None)

    if product:
        await callback.message.answer(
            f"📌 Kamu memesan <b>{product['name']}</b>\n"
            f"Harga: {product['price']}\n\n"
            "Silakan transfer ke:\n\n"
            "<b>BCA 123456789 a.n. Store Premium</b>\n"
            "atau Dana: 08xxxxxxx\n\n"
            "Setelah transfer, kirim bukti transfer di sini.",
        )
        await callback.message.answer("📤 Kirim bukti transfer sekarang:")

# === KIRIM BUKTI BAYAR ===
@dp.message(F.photo)
async def handle_payment_proof(message: types.Message):
    caption = (
        f"🧾 Bukti Pembayaran dari <a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a>\n"
        f"Username: @{message.from_user.username or '-'}\n"
        f"User ID: <code>{message.from_user.id}</code>"
    )
    await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=caption,
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                             [InlineKeyboardButton(text="💬 Balas User", url=f"tg://user?id={message.from_user.id}")]
                         ]))
    await message.answer("✅ Bukti pembayaran sudah dikirim ke admin. Tunggu proses verifikasi maksimal 5-10 menit.")

# === KEMBALI KE MENU ===
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    products = load_products()
    kb = InlineKeyboardBuilder()
    for product in products:
        kb.add(InlineKeyboardButton(text=product["name"], callback_data=f"product_{product['id']}"))
    await callback.message.edit_text("Silakan pilih produk:", reply_markup=kb.as_markup())

# === RUN ===
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
