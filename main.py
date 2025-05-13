import json
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile
import asyncio

# === SETUP LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# === LOAD CONFIG ===
try:
    with open("config.json") as f:
        config = json.load(f)
    BOT_TOKEN = config["BOT_TOKEN"]
    ADMIN_ID = config["ADMIN_ID"]
except Exception as e:
    logger.error(f"Gagal memuat config: {e}")
    exit()

# === SETUP BOT ===
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# === STATE CLASSES ===
class AddProductState(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_stock = State()
    waiting_for_file = State()

class OrderState(StatesGroup):
    waiting_for_payment = State()

# === UTILITY FUNCTIONS ===
def load_products():
    try:
        if not os.path.exists("products.json"):
            with open("products.json", "w") as f:
                json.dump([], f)
            return []
        
        with open("products.json", "r") as f:
            products = json.load(f)
            return products
    except Exception as e:
        logger.error(f"Error loading products: {e}")
        return []

def save_products(products):
    try:
        with open("products.json", "w") as f:
            json.dump(products, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving products: {e}")

def load_snk():
    try:
        if not os.path.exists("snk.txt"):
            return "Belum ada Syarat & Ketentuan yang ditetapkan."
        with open("snk.txt", "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading SNK: {e}")
        return "Belum ada Syarat & Ketentuan yang ditetapkan."

# === ADMIN COMMANDS ===
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Akses ditolak!")
        return
    
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Tambah Produk")
    kb.button(text="📝 Edit SNK")
    kb.button(text="📊 Lihat Produk")
    kb.adjust(2)
    
    await message.answer(
        "🛠️ **Panel Admin**\n"
        "Pilih opsi di bawah:",
        reply_markup=kb.as_markup(resize_keyboard=True)
    
# === ADD PRODUCT FLOW ===
@dp.message(F.text == "➕ Tambah Produk")
async def add_product_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.set_state(AddProductState.waiting_for_name)
    await message.answer("Masukkan nama produk:")

@dp.message(AddProductState.waiting_for_name)
async def process_product_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddProductState.waiting_for_description)
    await message.answer("Masukkan deskripsi produk:")

@dp.message(AddProductState.waiting_for_description)
async def process_product_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddProductState.waiting_for_price)
    await message.answer("Masukkan harga produk (contoh: Rp 50.000):")

@dp.message(AddProductState.waiting_for_price)
async def process_product_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await state.set_state(AddProductState.waiting_for_stock)
    await message.answer("Masukkan stok produk (angka):")

@dp.message(AddProductState.waiting_for_stock)
async def process_product_stock(message: types.Message, state: FSMContext):
    try:
        stock = int(message.text)
        await state.update_data(stock=stock)
        await state.set_state(AddProductState.waiting_for_file)
        await message.answer("Kirim file produk (document/photo):")
    except ValueError:
        await message.answer("Harap masukkan angka yang valid!")

@dp.message(AddProductState.waiting_for_file, F.document | F.photo)
async def process_product_file(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    products = load_products()
    new_id = max([p['id'] for p in products], default=0) + 1
    
    file_id = None
    if message.document:
        file_id = message.document.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id
    
    new_product = {
        "id": new_id,
        "name": data['name'],
        "description": data['description'],
        "price": data['price'],
        "stock": data['stock'],
        "file_id": file_id
    }
    
    products.append(new_product)
    save_products(products)
    
    await state.clear()
    await message.answer(f"✅ Produk {data['name']} berhasil ditambahkan!")

# === EDIT SNK ===
@dp.message(F.text == "📝 Edit SNK")
async def edit_snk_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await message.answer(
        "Kirim teks Syarat & Ketentuan baru:\n"
        f"SNK Saat Ini:\n{load_snk()}"
    )
    await state.set_state("waiting_for_snk")

@dp.message(F.text, state="waiting_for_snk")
async def save_snk(message: types.Message, state: FSMContext):
    try:
        with open("snk.txt", "w") as f:
            f.write(message.text)
        await message.answer("✅ SNK berhasil diperbarui!")
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ Gagal menyimpan SNK: {e}")

# === VIEW PRODUCTS ===
@dp.message(F.text == "📊 Lihat Produk")
async def view_products(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    products = load_products()
    if not products:
        await message.answer("Belum ada produk.")
        return
    
    text = "📦 Daftar Produk:\n\n"
    for p in products:
        text += f"🆔 {p['id']}\n📛 {p['name']}\n💵 {p['price']}\n🛒 Stok: {p['stock']}\n\n"
    
    await message.answer(text)

# === START COMMAND ===
@dp.message(CommandStart())
async def start(message: types.Message):
    products = [p for p in load_products() if p['stock'] > 0]
    
    if not products:
        await message.answer("😞 Maaf, stok produk sedang habis.")
        return
    
    kb = InlineKeyboardBuilder()
    for product in products:
        kb.add(types.InlineKeyboardButton(
            text=f"{product['name']} ({product['stock']})",
            callback_data=f"product_{product['id']}"
        ))
    kb.adjust(2)
    
    await message.answer(
        "👋 Selamat datang di Toko Digital!\n"
        "Silakan pilih produk yang tersedia:",
        reply_markup=kb.as_markup()
    )

# === SHOW PRODUCT DETAIL ===
@dp.callback_query(F.data.startswith("product_"))
async def show_product(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = next((p for p in load_products() if p["id"] == product_id), None)
    
    if not product:
        await callback.message.answer("Produk tidak ditemukan.")
        return
    
    text = (
        f"📛 <b>{product['name']}</b>\n\n"
        f"📝 Deskripsi:\n{product['description']}\n\n"
        f"💵 Harga: {product['price']}\n"
        f"🛒 Stok: {product['stock']}\n\n"
        "Jika berminat, klik tombol di bawah 👇"
    )
    
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(
        text="✅ Beli Sekarang",
        callback_data=f"order_{product_id}"
    ))
    kb.add(types.InlineKeyboardButton(
        text="📜 Syarat & Ketentuan",
        callback_data="show_snk"
    ))
    kb.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

# === SHOW SNK ===
@dp.callback_query(F.data == "show_snk")
async def show_snk(callback: types.CallbackQuery):
    snk_text = load_snk()
    await callback.message.answer(
        f"📜 <b>Syarat & Ketentuan</b>\n\n{snk_text}",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="🔙 Kembali", callback_data="back_to_menu")
        ]])
    )

# === ORDER PROCESS ===
@dp.callback_query(F.data.startswith("order_"))
async def order_product(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[1])
    product = next((p for p in load_products() if p["id"] == product_id), None)
    
    if not product:
        await callback.message.answer("Produk tidak ditemukan.")
        return
    
    if product['stock'] <= 0:
        await callback.message.answer("Maaf, stok produk ini habis.")
        return
    
    await state.set_state(OrderState.waiting_for_payment)
    await state.update_data(product_id=product_id, user_id=callback.from_user.id)
    
    payment_text = (
        f"📌 Kamu memesan <b>{product['name']}</b>\n"
        f"💵 Harga: {product['price']}\n\n"
        "Silakan transfer ke:\n\n"
        "<b>BCA 123456789 a.n. Toko Digital</b>\n"
        "atau Dana: 08123456789\n\n"
        "Setelah transfer, kirim bukti transfer di sini."
    )
    
    await callback.message.answer(payment_text)
    await callback.message.answer("📤 Kirim bukti transfer sekarang (foto/screenshot):")

# === PAYMENT PROOF HANDLER ===
@dp.message(OrderState.waiting_for_payment, F.photo | F.document)
async def handle_payment_proof(message: types.Message, state: FSMContext):
    data = await state.get_data()
    product_id = data['product_id']
    user_id = data['user_id']
    
    product = next((p for p in load_products() if p["id"] == product_id), None)
    if not product:
        await message.answer("Produk tidak ditemukan.")
        await state.clear()
        return
    
    # Get file_id from message
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id
    
    # Send to admin
    admin_caption = (
        f"🧾 <b>Bukti Pembayaran Baru</b>\n\n"
        f"🆔 Produk ID: {product_id}\n"
        f"📛 Produk: {product['name']}\n"
        f"💵 Harga: {product['price']}\n\n"
        f"👤 Pembeli: <a href='tg://user?id={user_id}'>{message.from_user.full_name}</a>\n"
        f"📱 Username: @{message.from_user.username or 'N/A'}\n"
        f"🆔 User ID: <code>{user_id}</code>"
    )
    
    admin_kb = InlineKeyboardBuilder()
    admin_kb.add(types.InlineKeyboardButton(
        text="✅ Verifikasi",
        callback_data=f"verify_{user_id}_{product_id}"
    ))
    admin_kb.add(types.InlineKeyboardButton(
        text="❌ Tolak",
        callback_data=f"reject_{user_id}"
    ))
    
    if file_id:
        if message.photo:
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=file_id,
                caption=admin_caption,
                reply_markup=admin_kb.as_markup()
            )
        else:
            await bot.send_document(
                chat_id=ADMIN_ID,
                document=file_id,
                caption=admin_caption,
                reply_markup=admin_kb.as_markup()
            )
    else:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_caption + "\n\n⚠️ Tidak ada bukti transfer terlampir!",
            reply_markup=admin_kb.as_markup()
        )
    
    await message.answer(
        "✅ Bukti pembayaran telah dikirim ke admin. "
        "Tunggu verifikasi dalam 1x24 jam.\n\n"
        "Jika ada pertanyaan, hubungi @admin"
    )
    await state.clear()

# === ADMIN VERIFICATION ===
@dp.callback_query(F.data.startswith("verify_"))
async def verify_payment(callback: types.CallbackQuery):
    _, user_id, product_id = callback.data.split("_")
    user_id = int(user_id)
    product_id = int(product_id)
    
    product = next((p for p in load_products() if p["id"] == product_id), None)
    if not product:
        await callback.message.answer("Produk tidak ditemukan!")
        return
    
    # Update stock
    products = load_products()
    for p in products:
        if p['id'] == product_id:
            p['stock'] -= 1
            break
    save_products(products)
    
    # Send product to user
    try:
        if product['file_id']:
            if product['file_id'].startswith("AgAC"):  # Photo
                await bot.send_photo(
                    chat_id=user_id,
                    photo=product['file_id'],
                    caption=f"🎉 Pembayaran telah diverifikasi!\n\n"
                          f"📛 Produk: {product['name']}\n"
                          f"💵 Harga: {product['price']}\n\n"
                          f"Terima kasih telah berbelanja!"
                )
            else:  # Document
                await bot.send_document(
                    chat_id=user_id,
                    document=product['file_id'],
                    caption=f"🎉 Pembayaran telah diverifikasi!\n\n"
                          f"📛 Produk: {product['name']}\n"
                          f"💵 Harga: {product['price']}\n\n"
                          f"Terima kasih telah berbelanja!"
                )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=f"🎉 Pembayaran telah diverifikasi!\n\n"
                     f"📛 Produk: {product['name']}\n"
                     f"💵 Harga: {product['price']}\n\n"
                     f"Namun, produk tidak tersedia. Hubungi admin @admin"
            )
        
        await callback.message.edit_text(
            f"✅ Pembayaran telah diverifikasi dan produk dikirim ke user.",
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Error sending product: {e}")
        await callback.message.answer(
            f"❌ Gagal mengirim produk ke user: {e}\n"
            f"Silakan kirim manual ke user ID: {user_id}"
        )

# === ADMIN REJECT ===
@dp.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text="❌ Maaf, pembayaran Anda ditolak oleh admin.\n"
                 "Silakan hubungi @admin untuk informasi lebih lanjut."
        )
        await callback.message.edit_text(
            "❌ Pembayaran telah ditolak dan user telah diberitahu.",
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Error rejecting payment: {e}")
        await callback.message.answer(
            f"Gagal mengirim notifikasi ke user. Silakan hubungi manual: {user_id}"
        )

# === BACK TO MENU ===
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    products = [p for p in load_products() if p['stock'] > 0]
    
    if not products:
        await callback.message.answer("😞 Maaf, stok produk sedang habis.")
        return
    
    kb = InlineKeyboardBuilder()
    for product in products:
        kb.add(types.InlineKeyboardButton(
            text=f"{product['name']} ({product['stock']})",
            callback_data=f"product_{product['id']}"
        ))
    kb.adjust(2)
    
    await callback.message.edit_text(
        "Silakan pilih produk yang tersedia:",
        reply_markup=kb.as_markup()
    )

# === RUN BOT ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
