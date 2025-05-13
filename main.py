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
from aiogram.client.default import DefaultBotProperties
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
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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

class RestockState(StatesGroup):
    input_accounts = State()

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
            json.dump(products, f, indent=4, ensure_ascii=False)
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
    kb.button(text="📦 Restock")
    kb.adjust(2)
    
    await message.answer(
        "🛠️ **Panel Admin**\n"
        "Pilih opsi di bawah:",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )
    
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

@dp.message(F.text, F.state == "waiting_for_snk")
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
@dp.callback_query(F.data.startswith("verify_"))
async def verify_payment(callback: types.CallbackQuery):
    try:
        _, user_id, product_id = callback.data.split("_")
        user_id = int(user_id)
        product_id = int(product_id)
        
        # Memberitahu admin bahwa proses verifikasi sedang berjalan
        await callback.answer("Memproses verifikasi...")
        
        products = load_products()
        product = next((p for p in products if p["id"] == product_id), None)
        
        if not product:
            await callback.message.reply("❌ Produk tidak ditemukan!")
            return
        
        # Periksa ketersediaan akun
        if "accounts" not in product or not product["accounts"]:
            await callback.message.reply(
                "❌ Tidak ada akun tersedia untuk produk ini.\n"
                "Silakan tambahkan akun terlebih dahulu dengan /restock"
            )
            return
        
        # Ambil akun pertama
        account = product["accounts"].pop(0)
        
        # Update stok produk berdasarkan jumlah akun yang tersisa
        product["stock"] = len(product["accounts"])
        
        # Simpan perubahan
        save_products(products)
        
        # Buat pesan konfirmasi untuk pengguna
        confirmation_text = (
            f"🎉 Pembayaran diverifikasi!\n\n"
            f"📛 Produk: {product['name']}\n"
            f"💵 Harga: {product['price']}\n\n"
            f"🔑 Login details:\n"
            f"👤 Username: <code>{account['username']}</code>\n"
            f"🔒 Password: <code>{account['password']}</code>\n\n"
            "⚠️ Jangan bagikan data login ke siapapun!"
        )
        
        # Kirim pesan konfirmasi ke pengguna
        sent_message = await bot.send_message(
            chat_id=user_id,
            text=confirmation_text,
            parse_mode=ParseMode.HTML
        )
        
        # Beri tahu admin bahwa konfirmasi berhasil dikirim
        admin_response = (
            f"✅ Akun berhasil dikirim ke user!\n"
            f"🔸 Sisa akun: {len(product['accounts'])}\n"
            f"🔸 Stok diperbarui: {product['stock']}"
        )
        
        # Gunakan reply untuk membuat pesan baru, bukan edit pesan lama
        await callback.message.reply(admin_response)
        
        # Kirim file produk ke pengguna jika ada
        if product['file_id']:
            try:
                # Teks caption untuk file
                caption_text = (
                    f"📦 Produk Anda: {product['name']}\n"
                    f"Terima kasih telah berbelanja!"
                )
                
                # Kirim file sesuai tipenya
                if product['file_id'].startswith("AgAC"):  # Photo
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=product['file_id'],
                        caption=caption_text
                    )
                else:  # Document
                    await bot.send_document(
                        chat_id=user_id,
                        document=product['file_id'],
                        caption=caption_text
                    )
                
                # Beri tahu admin bahwa file berhasil dikirim
                await callback.message.reply("✅ File produk berhasil dikirim ke user!")
                
            except Exception as e:
                logger.error(f"Error saat mengirim file produk: {e}")
                error_message = (
                    f"❌ Gagal mengirim file produk ke user: {str(e)}\n"
                    f"Silakan kirim manual ke user ID: {user_id}"
                )
                await callback.message.reply(error_message)
    
    except Exception as e:
        logger.error(f"Error dalam proses verifikasi: {e}")
        error_message = f"❌ Terjadi kesalahan dalam proses verifikasi: {str(e)}"
        if 'user_id' in locals() and 'account' in locals() and account:
            error_message += f"\nKirim manual: {account['username']}:{account['password']} ke user ID: {user_id}"
        await callback.message.reply(error_message)

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

# === RESTOK AKUN === #
@dp.message(F.text == "📦 Restock")
async def restock_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    products = load_products()
    if not products:
        await message.answer("❌ Tidak ada produk yang tersedia.")
        return
    
    # Buat keyboard pilihan produk
    builder = InlineKeyboardBuilder()
    for product in products:
        # Tampilkan info stok akun
        account_count = len(product.get('accounts', []))
        builder.button(
            text=f"{product['name']} (Stok: {product['stock']}, Akun: {account_count})", 
            callback_data=f"restock_{product['id']}"
        )
    builder.adjust(1)
    
    await message.answer("📦 Pilih produk yang akan di-restock:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("restock_"))
async def select_restock_method(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[1])
    product = next((p for p in load_products() if p["id"] == product_id), None)
    
    if not product:
        await callback.answer("❌ Produk tidak ditemukan!")
        return
    
    await state.set_state(RestockState.input_accounts)
    await state.update_data(product_id=product_id)
    
    current_stock = product.get('stock', 0)
    current_accounts = len(product.get('accounts', []))
    
    await callback.message.edit_text(
        f"📥 Restock {product['name']}\n\n"
        f"🔸 Stok saat ini: {current_stock}\n"
        f"🔸 Akun tersedia: {current_accounts}\n\n"
        "🔹 Format restock:\n"
        "<code>username:password</code>\n"
        "<code>username2:password2</code>\n\n"
        "Contoh:\n"
        "<code>spotifyuser:spotifypass123</code>\n"
        "<code>premiumacc:password456</code>",
        parse_mode=ParseMode.HTML
    )

@dp.message(RestockState.input_accounts)
async def process_restock(message: types.Message, state: FSMContext):
    data = await state.get_data()
    product_id = data["product_id"]
    
    products = load_products()
    product = next((p for p in products if p["id"] == product_id), None)
    
    if not product:
        await message.answer("❌ Produk tidak ditemukan!")
        await state.clear()
        return
    
    # Parsing akun baru (support baris atau koma)
    accounts = []

    # Gabungkan semua teks menjadi satu string
    text = message.text.strip()

    # Pisahkan berdasarkan koma atau baris
    if '\n' in text:
        raw_lines = text.split('\n')
    elif ',' in text:
        raw_lines = text.split(',')
    else:
        raw_lines = [text]

    # Parsing akun
    for line in raw_lines:
        line = line.strip()
        if ":" in line:
            username, password = line.split(":", 1)
            accounts.append({"username": username.strip(), "password": password.strip()})

    # Validasi apakah ada akun
    if not accounts:
        await message.answer("❌ Format salah! Gunakan username:password, pisahkan dengan baris atau koma.")
        return
    
    # Tambahkan ke produk
    if "accounts" not in product:
        product["accounts"] = []
    
    product["accounts"].extend(accounts)
    
    # Update stok produk berdasarkan jumlah akun
    product["stock"] = len(product["accounts"])
    
    save_products(products)
    
    await message.answer(
        f"✅ {len(accounts)} akun berhasil ditambahkan ke {product['name']}!\n"
        f"🔸 Total akun: {len(product['accounts'])}\n"
        f"🔸 Stok diperbarui menjadi: {product['stock']}"
    )
    await state.clear()
    
# === KIRIM ULANG DATA === #
@dp.message(Command("kirimulang"))
async def resend_account(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Akses ditolak!")
        return
        
    # Cek apakah perintah memiliki format yang benar
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "❌ Format salah!\n\n"
            "Gunakan: /kirimulang <user_id> <product_id>"
        )
        return
        
    try:
        user_id = int(args[1])
        product_id = int(args[2])
        
        products = load_products()
        product = next((p for p in products if p["id"] == product_id), None)
        
        if not product:
            await message.answer("❌ Produk tidak ditemukan!")
            return
            
        # Cek apakah ada akun tersedia
        if "accounts" not in product or not product["accounts"]:
            await message.answer(
                "❌ Tidak ada akun tersedia untuk produk ini.\n"
                "Silakan tambahkan akun terlebih dahulu dengan /restock"
            )
            return
            
        # Ambil akun pertama
        account = product["accounts"].pop(0)
        save_products(products)
        
        # Kirim akun ke user
        await bot.send_message(
            chat_id=user_id,
            text=f"🎉 Pembayaran diverifikasi!\n\n"
                 f"📛 Produk: {product['name']}\n"
                 f"💵 Harga: {product['price']}\n\n"
                 f"🔑 Login details:\n"
                 f"👤 Username: <code>{account['username']}</code>\n"
                 f"🔒 Password: <code>{account['password']}</code>\n\n"
                 "⚠️ Jangan bagikan data login ke siapapun!",
            parse_mode=ParseMode.HTML
        )
        
        # Kirim produk jika ada
        if product['file_id']:
            if product['file_id'].startswith("AgAC"):  # Photo
                await bot.send_photo(
                    chat_id=user_id,
                    photo=product['file_id'],
                    caption=f"📦 Produk Anda: {product['name']}\nTerima kasih telah berbelanja!"
                )
            else:  # Document
                await bot.send_document(
                    chat_id=user_id,
                    document=product['file_id'],
                    caption=f"📦 Produk Anda: {product['name']}\nTerima kasih telah berbelanja!"
                )
        
        await message.answer(f"✅ Akun dan produk berhasil dikirim ulang ke user ID: {user_id}")
        
    except Exception as e:
        logger.error(f"Error dalam pengiriman ulang: {e}")
        await message.answer(f"❌ Gagal mengirim ulang: {str(e)}")
        
# === mengirim akun secara manual === #
@dp.message(Command("kirimakun"))
async def send_manual_account(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Akses ditolak!")
        return
        
    # Cek format perintah
    args = message.get_args().split()
    if len(args) < 3:
        await message.answer(
            "❌ Format salah!\n\n"
            "Gunakan: /kirimakun <user_id> <username> <password>"
        )
        return
        
    try:
        user_id = int(args[0])
        username = args[1]
        password = args[2]
        
        await bot.send_message(
            chat_id=user_id,
            text=f"🔑 Login details:\n"
                 f"👤 Username: <code>{username}</code>\n"
                 f"🔒 Password: <code>{password}</code>\n\n"
                 "⚠️ Jangan bagikan data login ke siapapun!",
            parse_mode=ParseMode.HTML
        )
        
        await message.answer(f"✅ Akun berhasil dikirim ke user ID: {user_id}")
        
    except Exception as e:
        logger.error(f"Error dalam pengiriman akun manual: {e}")
        await message.answer(f"❌ Gagal mengirim akun: {str(e)}")
# CEK STOCK #
@dp.message(Command("cekstok"))
async def check_account_stock(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Akses ditolak!")
        return
    
    products = load_products()
    if not products:
        await message.answer("❌ Tidak ada produk tersedia.")
        return
    
    text = "📊 <b>Stok Produk & Akun</b>\n\n"
    
    for product in products:
        account_count = len(product.get('accounts', []))
        
        # Sinkronkan stok dengan jumlah akun jika berbeda
        if product.get('stock', 0) != account_count:
            product['stock'] = account_count
            
        text += (
            f"📛 <b>{product['name']}</b>\n"
            f"💵 {product['price']}\n"
            f"🛒 Stok: {product['stock']}\n"
            f"👤 Akun tersedia: {account_count}\n\n"
        )
    
    # Simpan perubahan jika ada penyesuaian stok
    save_products(products)
    
    await message.answer(text, parse_mode=ParseMode.HTML)

# Hapus Akun + Stock #
@dp.message(Command("hapusakun"))
async def remove_account_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Akses ditolak!")
        return
        
    products = load_products()
    if not products:
        await message.answer("❌ Tidak ada produk tersedia.")
        return
    
    # Pilih produk untuk menghapus akun
    builder = InlineKeyboardBuilder()
    for product in products:
        account_count = len(product.get('accounts', []))
        if account_count > 0:
            builder.button(
                text=f"{product['name']} ({account_count} akun)", 
                callback_data=f"rmaccount_{product['id']}"
            )
    builder.adjust(1)
    
    if len(builder.buttons) == 0:
        await message.answer("❌ Tidak ada produk yang memiliki akun.")
        return
    
    await message.answer("🗑️ Pilih produk untuk mengelola akun:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("rmaccount_"))
async def show_account_list(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[1])
    products = load_products()
    product = next((p for p in products if p["id"] == product_id), None)
    
    if not product or not product.get('accounts', []):
        await callback.message.edit_text("❌ Tidak ada akun tersedia.")
        return
    
    # Tampilkan 5 akun pertama dengan tombol hapus
    text = f"🗑️ <b>Hapus Akun - {product['name']}</b>\n\n"
    
    builder = InlineKeyboardBuilder()
    
    # Hanya tampilkan maksimal 10 akun untuk menghindari tombol terlalu banyak
    shown_accounts = product['accounts'][:10]
    
    for i, account in enumerate(shown_accounts):
        text += f"{i+1}. Username: <code>{account['username']}</code>\n"
        builder.button(
            text=f"🗑️ Hapus #{i+1}", 
            callback_data=f"delaccount_{product_id}_{i}"
        )
    
    total_accounts = len(product['accounts'])
    if total_accounts > 10:
        text += f"\n... dan {total_accounts - 10} akun lainnya"
    
    # Tambahkan tombol untuk menghapus semua akun
    builder.button(
        text="🗑️ Hapus Semua Akun", 
        callback_data=f"delallaccount_{product_id}"
    )
    
    builder.button(
        text="🔙 Kembali", 
        callback_data="admin_menu"
    )
    
    builder.adjust(2)
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("delaccount_"))
async def delete_account(callback: types.CallbackQuery):
    _, product_id, account_index = callback.data.split("_")
    product_id = int(product_id)
    account_index = int(account_index)
    
    products = load_products()
    product = next((p for p in products if p["id"] == product_id), None)
    
    if not product or not product.get('accounts', []) or account_index >= len(product['accounts']):
        await callback.answer("❌ Akun tidak ditemukan!")
        return
    
    # Hapus akun
    deleted_account = product['accounts'].pop(account_index)
    
    # Update stok
    product['stock'] = len(product['accounts'])
    
    # Simpan perubahan
    save_products(products)
    
    await callback.answer(f"✅ Akun {deleted_account['username']} dihapus!")
    
    # Tampilkan ulang daftar akun
    await show_account_list(callback, None)

@dp.callback_query(F.data.startswith("delallaccount_"))
async def delete_all_accounts(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    
    products = load_products()
    product = next((p for p in products if p["id"] == product_id), None)
    
    if not product:
        await callback.answer("❌ Produk tidak ditemukan!")
        return
    
    # Konfirmasi penghapusan
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Ya, Hapus Semua", 
        callback_data=f"confirmdelall_{product_id}"
    )
    builder.button(
        text="❌ Batal", 
        callback_data=f"rmaccount_{product_id}"
    )
    
    await callback.message.edit_text(
        f"⚠️ <b>KONFIRMASI</b> ⚠️\n\n"
        f"Anda akan menghapus SEMUA akun untuk produk <b>{product['name']}</b>.\n"
        f"Total {len(product.get('accounts', []))} akun akan dihapus.\n\n"
        f"Apakah Anda yakin?",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("confirmdelall_"))
async def confirm_delete_all(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    
    products = load_products()
    product = next((p for p in products if p["id"] == product_id), None)
    
    if not product:
        await callback.answer("❌ Produk tidak ditemukan!")
        return
    
    account_count = len(product.get('accounts', []))
    
    # Hapus semua akun
    product['accounts'] = []
    
    # Update stok
    product['stock'] = 0
    
    # Simpan perubahan
    save_products(products)
    
    await callback.message.edit_text(
        f"✅ Berhasil menghapus {account_count} akun dari produk <b>{product['name']}</b>.\n"
        f"Stok diperbarui menjadi 0.",
        parse_mode=ParseMode.HTML
    )

# Tombol kembali ke menu admin
@dp.callback_query(F.data == "admin_menu")
async def back_to_admin_menu(callback: types.CallbackQuery):
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Tambah Produk")
    kb.button(text="📝 Edit SNK")
    kb.button(text="📊 Lihat Produk")
    kb.adjust(2)
    
    await callback.message.reply(
        "🛠️ **Panel Admin**\n"
        "Pilih opsi di bawah:",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )
    await callback.message.delete()
    
# === BACK TO MENU === #
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
