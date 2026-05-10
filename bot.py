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

# DATABASE
conn = sqlite3.connect("mith.db")
cursor = conn.cursor()

# USERS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
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

    referral_id = None

    if len(args) > 1:
        referral_id = args[1]

    cursor.execute(
        "SELECT * FROM users WHERE telegram_id=?",
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:

        cursor.execute(
            "INSERT INTO users (telegram_id, username, points) VALUES (?, ?, ?)",
            (user_id, username, 100)
        )

        # REFERRAL REWARD
        if referral_id and str(referral_id) != str(user_id):

            cursor.execute(
                "UPDATE users SET points = points + 500, referrals = referrals + 1 WHERE telegram_id=?",
                (referral_id,)
            )

        conn.commit()

    # KEYBOARD
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📸 Follow Instagram",
                    url=INSTAGRAM_URL
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Join Telegram Group",
                    url=TELEGRAM_GROUP_URL
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚀 Join Telegram Community",
                    url=TELEGRAM_COMMUNITY_URL
                )
            ]
        ]
    )

    await message.answer(
        "🎁 Welcome to MITH Rewards\n\n"
        "You received 100 MITH Points!\n\n"
        "Commands:\n"
        "/daily\n"
        "/convert\n"
        "/balance\n"
        "/leaderboard\n"
        "/referral\n\n"
        "Invite friends and earn rewards!",
        reply_markup=keyboard
    )


# CONVERT POINTS TO COINS
@dp.message(Command("convert"))
async def convert(message: types.Message):

    user_id = message.from_user.id

    cursor.execute(
        "SELECT points, coins FROM users WHERE telegram_id=?",
        (user_id,)
    )

    result = cursor.fetchone()

    if not result:
        await message.answer("❌ Use /start first")
        return

    points, coins = result

    if points < 100:
        await message.answer(
            "❌ Minimum 100 points required."
        )
        return

    mith_coins = points // 100

    remaining_points = points % 100

    updated_coins = coins + mith_coins

    cursor.execute(
        "UPDATE users SET points=?, coins=? WHERE telegram_id=?",
        (
            remaining_points,
            updated_coins,
            user_id
        )
    )

    conn.commit()

    await message.answer(
        f"🎉 Converted {mith_coins * 100} points into {mith_coins} MITH Coins!"
    )


# DAILY REWARD
@dp.message(Command("daily"))
async def daily(message: types.Message):

    user_id = message.from_user.id

    cursor.execute(
        "SELECT last_daily FROM users WHERE telegram_id=?",
        (user_id,)
    )

    result = cursor.fetchone()

    if result and result[0]:

        last_claim = datetime.fromisoformat(result[0])

        if datetime.now() - last_claim < timedelta(hours=24):

            await message.answer(
                "⏳ You already claimed your daily reward."
            )

            return

    reward = random.randint(20, 50)

    cursor.execute(
        "UPDATE users SET points = points + ?, last_daily=? WHERE telegram_id=?",
        (reward, datetime.now().isoformat(), user_id)
    )

    conn.commit()

    await message.answer(
        f"🎉 You earned {reward} MITH Points!"
    )


# BALANCE COMMAND
@dp.message(Command("balance"))
async def balance(message: types.Message):

    user_id = message.from_user.id

    cursor.execute(
        "SELECT points, coins, referrals FROM users WHERE telegram_id=?",
        (user_id,)
    )

    result = cursor.fetchone()

    if result:

        points, coins, referrals = result

        await message.answer(
            f"💰 MITH Points: {points}\n"
            f"🪙 MITH Coins: {coins}\n"
            f"👥 Referrals: {referrals}"
        )

    else:

        await message.answer(
            "❌ Use /start first"
        )


# LEADERBOARD
@dp.message(Command("leaderboard"))
async def leaderboard(message: types.Message):

    user_id = message.from_user.id

    # TOP 10 USERS
    cursor.execute(
        """
        SELECT telegram_id, username, coins, points, referrals
        FROM users
        ORDER BY coins DESC, points DESC, referrals DESC
        LIMIT 10
        """
    )

    top_users = cursor.fetchall()

    text = "🏆 MITH Leaderboard\n\n"

    for index, user in enumerate(top_users, start=1):

        telegram_id, username, coins, points, referrals = user

        text += (
            f"{index}. @{username}\n"
            f"🪙 MITH Coins: {coins}\n"
            f"💰 MITH Points: {points}\n"
            f"👥 Referrals: {referrals}\n\n"
        )

    # GET ALL USERS FOR RANKING
    cursor.execute(
        """
        SELECT telegram_id
        FROM users
        ORDER BY coins DESC, points DESC, referrals DESC
        """
    )

    all_users = cursor.fetchall()

    user_rank = None

    for index, user in enumerate(all_users, start=1):

        if user[0] == user_id:
            user_rank = index
            break

    # SHOW USER POSITION IF NOT IN TOP 10
    if user_rank and user_rank > 10:

        cursor.execute(
            """
            SELECT username, coins, points, referrals
            FROM users
            WHERE telegram_id=?
            """,
            (user_id,)
        )

        current_user = cursor.fetchone()

        if current_user:

            username, coins, points, referrals = current_user

            text += (
                f"━━━━━━━━━━━━━━\n"
                f"📍 Your Position: #{user_rank}\n\n"
                f"@{username}\n"
                f"🪙 MITH Coins: {coins}\n"
                f"💰 MITH Points: {points}\n"
                f"👥 Referrals: {referrals}"
            )

    await message.answer(text)


# REFERRAL COMMAND
@dp.message(Command("referral"))
async def referral(message: types.Message):

    user_id = message.from_user.id

    bot_info = await bot.get_me()

    referral_link = f"https://t.me/{bot_info.username}?start={user_id}"

    await message.answer(
        f"👥 Your Referral Link:\n\n"
        f"{referral_link}\n\n"
        f"🎁 Earn 500 MITH Points per referral!"
    )


# MAIN
async def main():

    print("MITH Bot Running...")

    await dp.start_polling(bot)


# START BOT
if __name__ == "__main__":

    asyncio.run(main())
