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
conn = sqlite3.connect("/data/mith.db")
cursor = conn.cursor()

# CREATE TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    user_code TEXT UNIQUE,
    username TEXT,
    points INTEGER DEFAULT 0,
    coins REAL DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    last_daily TEXT
)
""")
conn.commit()

# SOCIAL LINKS
INSTAGRAM_URL = "https://www.instagram.com/mith_coin?igsh=dmJnOXpibDVzeTF4"
TELEGRAM_GROUP_URL = "https://t.me/mith_coin_official"
TELEGRAM_COMMUNITY_URL = "https://t.me/mith_india"


# START
@dp.message(Command("start"))
async def start(message: types.Message):

    user_id = message.from_user.id
    username = message.from_user.username or "User"

    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None

    cursor.execute("SELECT * FROM users WHERE telegram_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:

        # GENERATE USER CODE
        cursor.execute("SELECT MAX(CAST(user_code AS INTEGER)) FROM users")
        last = cursor.fetchone()[0]

        user_code = str(int(last) + 1) if last else "100001"

        cursor.execute("""
            INSERT INTO users (telegram_id, user_code, username, points)
            VALUES (?, ?, ?, ?)
        """, (user_id, user_code, username, 100))

        # REFERRAL
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

    # KEYBOARD
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📸 Instagram", url=INSTAGRAM_URL)],
            [InlineKeyboardButton(text="💬 Telegram Group", url=TELEGRAM_GROUP_URL)],
            [InlineKeyboardButton(text="🚀 Community", url=TELEGRAM_COMMUNITY_URL)]
        ]
    )

    await message.answer(
        "🎁 Welcome to MITH Rewards\n\n"
        "You received 100 MITH Points\n\n"
        "Commands:\n"
        "/daily\n"
        "/convert\n"
        "/balance\n"
        "/leaderboard\n"
        "/referral",
        reply_markup=keyboard
    )


# CONVERT
@dp.message(Command("convert"))
async def convert(message: types.Message):

    user_id = message.from_user.id

    cursor.execute("SELECT points, coins FROM users WHERE telegram_id=?", (user_id,))
    result = cursor.fetchone()

    if not result:
        return await message.answer("❌ Use /start first")

    points, coins = result

    if points < 100:
        return await message.answer("❌ Minimum 100 points required")

    minted = points // 100
    remaining = points % 100

    cursor.execute("""
        UPDATE users
        SET points=?, coins=?
        WHERE telegram_id=?
    """, (remaining, coins + minted, user_id))

    conn.commit()

    await message.answer(f"🎉 Converted {minted * 100} points → {minted} MITH Coins")


# DAILY
@dp.message(Command("daily"))
async def daily(message: types.Message):

    user_id = message.from_user.id

    cursor.execute("SELECT last_daily FROM users WHERE telegram_id=?", (user_id,))
    result = cursor.fetchone()

    if result and result[0]:

        last = datetime.fromisoformat(result[0])

        if datetime.now() - last < timedelta(hours=24):
            return await message.answer("⏳ Already claimed daily reward")

    reward = random.randint(20, 50)

    cursor.execute("""
        UPDATE users
        SET points = points + ?,
            last_daily=?
        WHERE telegram_id=?
    """, (reward, datetime.now().isoformat(), user_id))

    conn.commit()

    await message.answer(f"🎉 +{reward} MITH Points")


# BALANCE
@dp.message(Command("balance"))
async def balance(message: types.Message):

    user_id = message.from_user.id

    cursor.execute("""
        SELECT user_code, points, coins, referrals
        FROM users
        WHERE telegram_id=?
    """, (user_id,))

    user = cursor.fetchone()

    if not user:
        return await message.answer("❌ Use /start first")

    user_code, points, coins, referrals = user

    await message.answer(
        f"🆔 {user_code}\n"
        f"💰 Points: {points}\n"
        f"🪙 Coins: {coins}\n"
        f"👥 Referrals: {referrals}"
    )


# LEADERBOARD (CLEAN)
@dp.message(Command("leaderboard"))
async def leaderboard(message: types.Message):

    user_id = message.from_user.id

    cursor.execute("""
        SELECT user_code, coins, points, referrals
        FROM users
        ORDER BY coins DESC, points DESC, referrals DESC
        LIMIT 10
    """)

    top = cursor.fetchall()

    text = "🏆 MITH Leaderboard\n\n"

    for i, u in enumerate(top, 1):
        user_code, coins, points, refs = u
        text += f"{i}. {user_code} | 🪙{coins} | 💰{points} | 👥{refs}\n"

    # RANK
    cursor.execute("""
        SELECT telegram_id FROM users
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

        text += f"\n━━━━━━━━━━\n📍 Your Rank #{rank}\n{me[0]} | 🪙{me[1]} | 💰{me[2]} | 👥{me[3]}"

    await message.answer(text)


# REFERRAL
@dp.message(Command("referral"))
async def referral(message: types.Message):

    user_id = message.from_user.id

    cursor.execute("SELECT user_code FROM users WHERE telegram_id=?", (user_id,))
    code = cursor.fetchone()

    if not code:
        return await message.answer("❌ Use /start first")

    bot_info = await bot.get_me()

    link = f"https://t.me/{bot_info.username}?start={code[0]}"

    await message.answer(
        f"🆔 {code[0]}\n\n"
        f"👥 Referral Link:\n{link}\n\n"
        f"🎁 Earn 500 Points per referral"
    )


# RUN
async def main():
    print("MITH Bot Running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
