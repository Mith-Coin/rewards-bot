import asyncio
import sqlite3
import random
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import os

# LOAD ENV
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# BOT SETUP
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# DATABASE (Railway persistent volume)
conn = sqlite3.connect("/data/mith.db", check_same_thread=False)
cursor = conn.cursor()

# CREATE USERS TABLE
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


# START COMMAND
@dp.message(Command("start"))
async def start(message: types.Message):

    user_id = message.from_user.id
    username = message.from_user.username or "User"

    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None

    cursor.execute("SELECT * FROM users WHERE telegram_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:

        # generate numeric user_code
        cursor.execute("SELECT MAX(CAST(user_code AS INTEGER)) FROM users")
        last = cursor.fetchone()[0]

        user_code = str(int(last) + 1) if last else "100001"

        cursor.execute("""
            INSERT INTO users (telegram_id, user_code, username, points)
            VALUES (?, ?, ?, ?)
        """, (user_id, user_code, username, 100))

        # referral reward
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
        "You received 100 MITH Points!\n\n"
        "Commands:\n"
        "/daily\n"
        "/convert\n"
        "/balance\n"
        "/leaderboard\n"
        "/referral\n",
        reply_markup=keyboard
    )


# CONVERT
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


# DAILY
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


# BALANCE
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


# LEADERBOARD
@dp.message(Command("leaderboard"))
async def leaderboard(message: types.Message):

    user_id = message.from_user.id

    # header
    text = (
        "🏆 MITH LEADERBOARD\n"
        "ID | Coins | Points | Referrals\n\n"
    )

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

    # user rank
    cursor.execute("""
        SELECT telegram_id, user_code, coins, points, referrals
        FROM users
        ORDER BY coins DESC, points DESC, referrals DESC
    """)

    all_users = cursor.fetchall()

    rank = None
    for i, u in enumerate(all_users, 1):
        if u[0] == user_id:
            rank = i
            break

    if rank and rank > 10:
        cursor.execute("""
            SELECT user_code, coins, points, referrals
            FROM users
            WHERE telegram_id=?
        """, (user_id,))

        me = cursor.fetchone()

        if me:
            code, coins, points, refs = me
            text += f"\n📍 Your Rank #{rank}\n{code} | 🪙{coins} | 💰{points} | 👥{refs}"

    await message.answer(text)


# REFERRAL
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


# MAIN
async def main():
    print("MITH Bot Running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
