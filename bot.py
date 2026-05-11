import asyncio
import sqlite3
import random
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
import os

# =========================
# LOAD ENV
# =========================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =========================
# DATABASE
# =========================
conn = sqlite3.connect("/data/mith.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    user_code TEXT UNIQUE,
    username TEXT,
    points INTEGER DEFAULT 0,
    coins REAL DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    wallet TEXT,
    last_daily TEXT
)
""")
conn.commit()

# =========================
# LINKS
# =========================
INSTAGRAM_URL = "https://www.instagram.com/mith_coin?igsh=dmJnOXpibDVzeTF4"
TELEGRAM_GROUP_URL = "https://t.me/mith_coin_official"
TELEGRAM_COMMUNITY_URL = "https://t.me/mith_india"

# =========================
# FSM
# =========================
class TransferState(StatesGroup):
    waiting_for_user_code = State()
    waiting_for_amount = State()

# =========================
# MENU
# =========================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Balance", callback_data="balance")],
        [InlineKeyboardButton(text="🔁 Transfer", callback_data="transfer")],
        [InlineKeyboardButton(text="🎁 Daily", callback_data="daily")],
        [InlineKeyboardButton(text="💱 Convert", callback_data="convert")],
        [InlineKeyboardButton(text="👥 Referral", callback_data="referral")],
        [InlineKeyboardButton(text="🏆 Leaderboard", callback_data="leaderboard")]
    ])

# =========================
# START
# =========================
@dp.message(Command("start"))
async def start(message: types.Message):

    user_id = message.from_user.id
    username = message.from_user.username or "User"

    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None

    cursor.execute("SELECT * FROM users WHERE telegram_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:

        cursor.execute("SELECT MAX(CAST(user_code AS INTEGER)) FROM users")
        last = cursor.fetchone()[0]
        user_code = str(int(last) + 1) if last else "100001"

        cursor.execute("""
            INSERT INTO users (telegram_id, user_code, username, points)
            VALUES (?, ?, ?, ?)
        """, (user_id, user_code, username, 100))

        if referral_code:
            cursor.execute("SELECT telegram_id FROM users WHERE user_code=?", (referral_code,))
            ref = cursor.fetchone()

            if ref and ref[0] != user_id:
                cursor.execute("""
                    UPDATE users
                    SET points = points + 500,
                        referrals = referrals + 1
                    WHERE telegram_id=?
                """, (ref[0],))

        conn.commit()

    await message.answer(
        "🎁 MITH Bot Started Successfully\n\nChoose option:",
        reply_markup=main_menu()
    )

# =========================
# HELP / MENU
# =========================
@dp.message(Command("menu"))
async def menu(message: types.Message):
    await message.answer("📌 Main Menu:", reply_markup=main_menu())

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        "/start - Start bot\n"
        "/balance - Check balance\n"
        "/transfer - Send coins\n"
        "/daily - Daily reward\n"
        "/convert - Convert points\n"
        "/referral - Referral link\n"
        "/menu - Show menu",
        reply_markup=main_menu()
    )

# =========================
# BALANCE
# =========================
@dp.message(Command("balance"))
async def balance_cmd(message: types.Message):
    await balance(message)

async def balance(message: types.Message):

    cursor.execute("""
        SELECT user_code, points, coins, referrals
        FROM users
        WHERE telegram_id=?
    """, (message.from_user.id,))

    data = cursor.fetchone()

    if not data:
        return await message.answer("❌ Use /start first", reply_markup=main_menu())

    code, points, coins, refs = data

    await message.answer(
        f"🆔 {code}\n💰 {points}\n🪙 {coins}\n👥 {refs}",
        reply_markup=main_menu()
    )

# =========================
# DAILY
# =========================
@dp.message(Command("daily"))
async def daily_cmd(message: types.Message):
    await daily(message)

async def daily(message: types.Message):

    uid = message.from_user.id

    cursor.execute("SELECT last_daily FROM users WHERE telegram_id=?", (uid,))
    data = cursor.fetchone()

    if data and data[0]:
        last = datetime.fromisoformat(data[0])
        if datetime.now() - last < timedelta(hours=24):
            return await message.answer("⏳ Already claimed", reply_markup=main_menu())

    reward = random.randint(20, 50)

    cursor.execute("""
        UPDATE users
        SET points = points + ?,
            last_daily = ?
        WHERE telegram_id=?
    """, (reward, datetime.now().isoformat(), uid))

    conn.commit()

    await message.answer(f"🎁 +{reward} points", reply_markup=main_menu())

# =========================
# CONVERT
# =========================
@dp.message(Command("convert"))
async def convert_cmd(message: types.Message):
    await convert(message)

async def convert(message: types.Message):

    uid = message.from_user.id

    cursor.execute("SELECT points, coins FROM users WHERE telegram_id=?", (uid,))
    data = cursor.fetchone()

    if not data:
        return await message.answer("❌ Start first", reply_markup=main_menu())

    points, coins = data

    if points < 100:
        return await message.answer("❌ Not enough points", reply_markup=main_menu())

    add = points // 100
    rem = points % 100

    cursor.execute("""
        UPDATE users SET points=?, coins=? WHERE telegram_id=?
    """, (rem, coins + add, uid))

    conn.commit()

    await message.answer(f"💱 Converted {add}", reply_markup=main_menu())

# =========================
# REFERRAL
# =========================
@dp.message(Command("referral"))
async def referral(message: types.Message):

    uid = message.from_user.id

    cursor.execute("SELECT user_code FROM users WHERE telegram_id=?", (uid,))
    code = cursor.fetchone()

    if not code:
        return await message.answer("❌ Start first", reply_markup=main_menu())

    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={code[0]}"

    await message.answer(link, reply_markup=main_menu())

# =========================
# LEADERBOARD
# =========================
@dp.message(Command("leaderboard"))
async def leaderboard(message: types.Message):

    cursor.execute("""
        SELECT user_code, coins, points, referrals
        FROM users
        ORDER BY coins DESC
        LIMIT 10
    """)

    rows = cursor.fetchall()

    text = "🏆 LEADERBOARD\n\n"
    for i, r in enumerate(rows, 1):
        text += f"{i}. {r[0]} | 🪙{r[1]} | 💰{r[2]}\n"

    await message.answer(text, reply_markup=main_menu())

# =========================
# TRANSFER ENTRY FIX
# =========================
@dp.message(Command("transfer"))
async def transfer(message: types.Message, state: FSMContext):

    uid = message.from_user.id

    cursor.execute("SELECT coins FROM users WHERE telegram_id=?", (uid,))
    bal = cursor.fetchone()

    if not bal:
        return await message.answer("❌ Start first", reply_markup=main_menu())

    await state.set_state(TransferState.waiting_for_user_code)

    await message.answer(
        f"💰 Balance: {bal[0]}\nEnter USER CODE:",
        reply_markup=main_menu()
    )

# =========================
# CALLBACK ROUTER FIXED
# =========================
@dp.callback_query()
async def cb(callback: types.CallbackQuery, state: FSMContext):

    if callback.data == "balance":
        await balance(callback.message)

    elif callback.data == "daily":
        await daily(callback.message)

    elif callback.data == "convert":
        await convert(callback.message)

    elif callback.data == "referral":
        await referral(callback.message)

    elif callback.data == "leaderboard":
        await leaderboard(callback.message)

    elif callback.data == "transfer":
        await transfer(callback.message, state)

    await callback.answer()

# =========================
# MAIN
# =========================
async def main():
    print("MITH BOT RUNNING...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
