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

# TASKS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    task_name TEXT,
    completed INTEGER DEFAULT 0,
    proof TEXT
)
""")

conn.commit()

# SOCIAL LINKS
INSTAGRAM_URL = "https://instagram.com/YOURPAGE"
TWITTER_URL = "https://x.com/YOURPAGE"
LINKEDIN_URL = "https://linkedin.com/company/YOURPAGE"


# START COMMAND
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

    await message.answer(
        "🎁 Welcome to MITH Rewards\n\n"
        "You received 100 MITH Points!\n\n"
        "Commands:\n"
        "/daily\n"
        "/balance\n"
        "/leaderboard\n"
        "/tasks"
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


# TASKS COMMAND
@dp.message(Command("tasks"))
async def tasks(message: types.Message):

    text = (
        "📋 MITH Social Tasks\n\n"
        "📸 Follow Instagram — 1000 Points\n"
        "🐦 Follow Twitter/X — 1000 Points\n"
        "💼 Follow LinkedIn — 1000 Points\n\n"
        "After completing tasks use:\n\n"
        "/verify instagram yourusername\n"
        "/verify twitter yourusername\n"
        "/verify linkedin yourusername"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📸 Instagram",
                    url=INSTAGRAM_URL
                )
            ],
            [
                InlineKeyboardButton(
                    text="🐦 Twitter/X",
                    url=TWITTER_URL
                )
            ],
            [
                InlineKeyboardButton(
                    text="💼 LinkedIn",
                    url=LINKEDIN_URL
                )
            ]
        ]
    )

    await message.answer(
        text,
        reply_markup=keyboard
    )


# VERIFY COMMAND
@dp.message(Command("verify"))
async def verify(message: types.Message):

    user_id = message.from_user.id

    args = message.text.split()

    if len(args) < 3:

        await message.answer(
            "❌ Usage:\n\n"
            "/verify instagram username\n"
            "/verify twitter username\n"
            "/verify linkedin username"
        )

        return

    task = args[1].lower()
    proof = args[2]

    rewards = {
        "instagram": 1000,
        "twitter": 1000,
        "linkedin": 1000
    }

    if task not in rewards:

        await message.answer(
            "❌ Invalid task"
        )

        return

    # CHECK DUPLICATE
    cursor.execute(
        "SELECT * FROM tasks WHERE telegram_id=? AND task_name=?",
        (user_id, task)
    )

    existing = cursor.fetchone()

    if existing:

        await message.answer(
            "✅ Task already completed"
        )

        return

    reward = rewards[task]

    # SAVE TASK
    cursor.execute(
        "INSERT INTO tasks (telegram_id, task_name, completed, proof) VALUES (?, ?, ?, ?)",
        (user_id, task, 1, proof)
    )

    # ADD REWARD
    cursor.execute(
        "UPDATE users SET points = points + ? WHERE telegram_id=?",
        (reward, user_id)
    )

    conn.commit()

    await message.answer(
        f"🎉 Verification Successful!\n\n"
        f"📌 Task: {task.capitalize()}\n"
        f"⭐ Reward: {reward} MITH Points"
    )


# MAIN
async def main():

    print("MITH Bot Running...")

    await dp.start_polling(bot)


# START BOT
if __name__ == "__main__":

    asyncio.run(main())
