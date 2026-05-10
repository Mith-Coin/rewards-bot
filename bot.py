import asyncio
import sqlite3
import random
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("mith.db")
cursor = conn.cursor()

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


@dp.message(Command("start"))
async def start(message: types.Message):

    user_id = message.from_user.id
    username = message.from_user.username or "User"

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

        conn.commit()

    await message.answer("🎁 Welcome to MITH Rewards\n\n"
        "You received 100 MITH Points!\n\n"
        "Commands:\n"
        "/daily\n"
        "/balance\n"
        "/leaderboard"
    )


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


@dp.message(Command("balance"))
async def balance(message: types.Message):

    user_id = message.from_user.id

    cursor.execute(
        "SELECT points FROM users WHERE telegram_id=?",
        (user_id,)
    )

    result = cursor.fetchone()

    if result:

        await message.answer(
            f"💰 Your Balance: {result[0]} MITH Points"
        )

    else:

        await message.answer(
            "Use /start first"
        )


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


async def main():

    print("MITH Bot Running...")

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())