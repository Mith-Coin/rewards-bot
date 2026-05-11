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

# LOAD ENV
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# BOT SETUP
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# DATABASE
conn = sqlite3.connect("/data/mith.db", check_same_thread=False)
cursor = conn.cursor()

# USERS TABLE
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

# SOCIAL LINKS
INSTAGRAM_URL = "https://www.instagram.com/mith_coin?igsh=dmJnOXpibDVzeTF4"
TELEGRAM_GROUP_URL = "https://t.me/mith_coin_official"
TELEGRAM_COMMUNITY_URL = "https://t.me/mith_india"


# =========================
# FSM STATES
# =========================
class TransferState(StatesGroup):
    waiting_for_user_code = State()
    waiting_for_amount = State()


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
            cursor.execute(
                "SELECT telegram_id FROM users WHERE user_code=?",
                (referral_code,)
            )
            ref = cursor.fetchone()

            if ref and ref[0] != user_id:
                cursor.execute("""
                    UPDATE users
                    SET points = points + 500,
                        referrals = referrals + 1
                    WHERE telegram_id=?
                """, (ref[0],))

        conn.commit()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Instagram", url=INSTAGRAM_URL)],
        [InlineKeyboardButton(text="💬 Telegram Group", url=TELEGRAM_GROUP_URL)],
        [InlineKeyboardButton(text="🚀 Community", url=TELEGRAM_COMMUNITY_URL)]
    ])

    await message.answer(
        "🎁 Welcome to MITH Rewards\n\n"
        "Commands:\n"
        "/daily\n"
        "/convert\n"
        "/balance\n"
        "/leaderboard\n"
        "/referral\n"
        "/transfer\n",
        reply_markup=keyboard
    )


# =========================
# BALANCE
# =========================
@dp.message(Command("balance"))
async def balance(message: types.Message):

    user_id = message.from_user.id

    cursor.execute("""
        SELECT user_code, points, coins, referrals
        FROM users
        WHERE telegram_id=?
    """, (user_id,))

    data = cursor.fetchone()

    if not data:
        return await message.answer("❌ Use /start first")

    code, points, coins, refs = data

    await message.answer(
        f"🆔 ID: {code}\n"
        f"💰 Points: {points}\n"
        f"🪙 Coins: {coins}\n"
        f"👥 Referrals: {refs}"
    )


# =========================
# CONVERT
# =========================
@dp.message(Command("convert"))
async def convert(message: types.Message):

    user_id = message.from_user.id

    cursor.execute("SELECT points, coins FROM users WHERE telegram_id=?", (user_id,))
    data = cursor.fetchone()

    if not data:
        return await message.answer("❌ Use /start first")

    points, coins = data

    if points < 100:
        return await message.answer("❌ Minimum 100 points required")

    coins_added = points // 100
    remaining = points % 100

    cursor.execute("""
        UPDATE users
        SET points=?, coins=?
        WHERE telegram_id=?
    """, (remaining, coins + coins_added, user_id))

    conn.commit()

    await message.answer(
        f"🎉 Converted {coins_added * 100} points → {coins_added} MITH Coins"
    )


# =========================
# DAILY
# =========================
@dp.message(Command("daily"))
async def daily(message: types.Message):

    user_id = message.from_user.id

    cursor.execute("SELECT last_daily FROM users WHERE telegram_id=?", (user_id,))
    data = cursor.fetchone()

    if data and data[0]:
        last = datetime.fromisoformat(data[0])
        if datetime.now() - last < timedelta(hours=24):
            return await message.answer("⏳ Already claimed today")

    reward = random.randint(20, 50)

    cursor.execute("""
        UPDATE users
        SET points = points + ?,
            last_daily = ?
        WHERE telegram_id=?
    """, (reward, datetime.now().isoformat(), user_id))

    conn.commit()

    await message.answer(f"🎁 You earned {reward} MITH Points")


# =========================
# REFERRAL
# =========================
@dp.message(Command("referral"))
async def referral(message: types.Message):

    user_id = message.from_user.id

    cursor.execute("SELECT user_code FROM users WHERE telegram_id=?", (user_id,))
    data = cursor.fetchone()

    if not data:
        return await message.answer("❌ Use /start first")

    code = data[0]

    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={code}"

    await message.answer(
        f"👥 Referral Link:\n{link}\n\n"
        f"🎁 Earn 500 points per referral!"
    )


# =========================
# LEADERBOARD
# =========================
@dp.message(Command("leaderboard"))
async def leaderboard(message: types.Message):

    text = "🏆 MITH LEADERBOARD\nID | Coins | Points | Referrals\n\n"

    cursor.execute("""
        SELECT user_code, username, coins, points, referrals
        FROM users
        ORDER BY coins DESC, points DESC, referrals DESC
        LIMIT 10
    """)

    top = cursor.fetchall()

    for i, u in enumerate(top, 1):
        code, username, coins, points, refs = u
        text += f"{i}. {code} | 🪙{coins} | 💰{points} | 👥{refs}\n"

    await message.answer(text)


# =========================
# 🔥 TRANSFER SYSTEM (UPDATED FLOW)
# =========================

@dp.message(Command("transfer"))
async def transfer_start(message: types.Message, state: FSMContext):

    user_id = message.from_user.id

    # show balance first
    cursor.execute("""
        SELECT coins, user_code
        FROM users
        WHERE telegram_id=?
    """, (user_id,))
    user = cursor.fetchone()

    if not user:
        return await message.answer("❌ Use /start first")

    balance, code = user

    await state.set_state(TransferState.waiting_for_user_code)

    await message.answer(
        f"💰 Your Balance: {balance} MITH Coins\n\n"
        "👤 Enter receiver USER CODE:"
    )


@dp.message(TransferState.waiting_for_user_code)
async def get_user_code(message: types.Message, state: FSMContext):

    receiver_code = message.text.strip()

    cursor.execute(
        "SELECT telegram_id FROM users WHERE user_code=?",
        (receiver_code,)
    )
    receiver = cursor.fetchone()

    if not receiver:
        return await message.answer("❌ Invalid user code. Try again:")

    await state.update_data(receiver_code=receiver_code)

    await state.set_state(TransferState.waiting_for_amount)

    await message.answer(
        "💰 Enter the number of MITH Coins to transfer:"
    )


@dp.message(TransferState.waiting_for_amount)
async def execute_transfer(message: types.Message, state: FSMContext):

    sender_id = message.from_user.id

    try:
        amount = float(message.text.strip())
    except ValueError:
        return await message.answer("❌ Enter valid number")

    if amount <= 0:
        return await message.answer("❌ Amount must be greater than 0")

    data = await state.get_data()
    receiver_code = data["receiver_code"]

    cursor.execute("""
        SELECT coins, user_code
        FROM users
        WHERE telegram_id=?
    """, (sender_id,))
    sender = cursor.fetchone()

    if not sender:
        await state.clear()
        return await message.answer("❌ Use /start first")

    sender_balance, sender_code = sender

    if sender_code == receiver_code:
        await state.clear()
        return await message.answer("❌ Cannot transfer to yourself")

    # 🔴 INSIDE BALANCE CHECK
    if sender_balance < amount:
        await state.clear()
        return await message.answer(
            "❌ Insufficient balance\n"
            "🚫 Transfer cancelled"
        )

    cursor.execute(
        "SELECT telegram_id FROM users WHERE user_code=?",
        (receiver_code,)
    )
    receiver = cursor.fetchone()

    if not receiver:
        await state.clear()
        return await message.answer("❌ Receiver not found")

    receiver_id = receiver[0]

    # transfer
    cursor.execute("""
        UPDATE users
        SET coins = coins - ?
        WHERE telegram_id=?
    """, (amount, sender_id))

    cursor.execute("""
        UPDATE users
        SET coins = coins + ?
        WHERE telegram_id=?
    """, (amount, receiver_id))

    conn.commit()

    await state.clear()

    await message.answer(
        f"✅ Transfer successful!\n"
        f"🪙 Sent: {amount} MITH Coins\n"
        f"👤 To: {receiver_code}"
    )


# =========================
# MAIN
# =========================
async def main():
    print("MITH Bot Running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
