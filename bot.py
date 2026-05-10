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
    referrals INTEGER DEFAULT 0,
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
        "/balance\n"
        "/leaderboard\n"
        "/referral\n\n"
        "Invite friends and earn rewards!",
        reply_markup=keyboard
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
        "SELECT points, referrals FROM users WHERE telegram_id=?",
        (user_id,)
    )

    result = cursor.fetchone()

    if result:

        points, referrals = result

        await message.answer(
            f"💰 Balance: {points} MITH Points\n"
            f"👥 Referrals: {referrals}"
        )

    else:

        await message.answer(
            "❌ Use /start first"
        )


# LEADERBOARD
@dp.message(Command("leaderboard"))
async def leaderboard(message: types.Message):

    cursor.execute(
        "SELECT username, points FROM users ORDER BY points DESC LIMIT 10"
    )

    users = cursor.fetchall()

    text = "🏆 MITH Leaderboard\n\n"

    for index, user in enumerate(users, start=1):

        username, points = user

        text += f"{index}. @{username} — {points} points\n"

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
