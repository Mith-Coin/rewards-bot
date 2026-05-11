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
conn = sqlite3.connect("/data/mith.db")
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

# ADD user_code COLUMN IF MISSING
try:
    cursor.execute(
        "ALTER TABLE users ADD COLUMN user_code TEXT"
    )
    conn.commit()
except:
    pass

# GENERATE USER CODES FOR OLD USERS
cursor.execute(
    """
    SELECT telegram_id
    FROM users
    WHERE user_code IS NULL
    """
)

old_users = cursor.fetchall()

cursor.execute(
    "SELECT MAX(CAST(user_code AS INTEGER)) FROM users"
)

last_code = cursor.fetchone()[0]

if last_code:
    counter = int(last_code) + 1
else:
    counter = 100001

for old_user in old_users:

    telegram_id = old_user[0]

    cursor.execute(
        """
        UPDATE users
        SET user_code=?
        WHERE telegram_id=?
        """,
        (
            str(counter),
            telegram_id
        )
    )

    counter += 1

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

    referral_code = None

    if len(args) > 1:
        referral_code = args[1]

    # CHECK USER
    cursor.execute(
        "SELECT * FROM users WHERE telegram_id=?",
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:

        # GENERATE NUMERIC USER CODE
        cursor.execute(
            "SELECT MAX(CAST(user_code AS INTEGER)) FROM users"
        )

        last_user = cursor.fetchone()[0]

        if last_user:
            user_code = str(int(last_user) + 1)
        else:
            user_code = "100001"

        # CREATE USER
        cursor.execute(
            """
            INSERT INTO users (
                telegram_id,
                user_code,
                username,
                points
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                user_code,
                username,
                100
            )
        )

        # REFERRAL REWARD
        if referral_code:

            cursor.execute(
                "SELECT telegram_id FROM users WHERE user_code=?",
                (referral_code,)
            )

            ref_user = cursor.fetchone()

            if ref_user:

                ref_telegram_id = ref_user[0]

                if ref_telegram_id != user_id:

                    cursor.execute(
                        """
                        UPDATE users
                        SET points = points + 500,
                            referrals = referrals + 1
                        WHERE telegram_id=?
                        """,
                        (ref_telegram_id,)
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

        await message.answer(
            "❌ Use /start first"
        )

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
        """
        UPDATE users
        SET points=?, coins=?
        WHERE telegram_id=?
        """,
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
        """
        UPDATE users
        SET points = points + ?,
            last_daily=?
        WHERE telegram_id=?
        """,
        (
            reward,
            datetime.now().isoformat(),
            user_id
        )
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
        """
        SELECT user_code, points, coins, referrals
        FROM users
        WHERE telegram_id=?
        """,
        (user_id,)
    )

    result = cursor.fetchone()

    if result:

        user_code, points, coins, referrals = result

        await message.answer(
            f"🆔 User ID: {user_code}\n"
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

    cursor.execute(
        """
        SELECT telegram_id,
               user_code,
               username,
               coins,
               points,
               referrals
        FROM users
        ORDER BY coins DESC,
                 points DESC,
                 referrals DESC
        LIMIT 10
        """
    )

    top_users = cursor.fetchall()

    text = "🏆 MITH Leaderboard\n\n"

    for index, user in enumerate(top_users, start=1):

        (
            telegram_id,
            user_code,
            username,
            coins,
            points,
            referrals
        ) = user

        text += (
            f"{index}. "
            f"{user_code} | "
            f"@{username} | "
            f"🪙 {coins} | "
            f"💰 {points} | "
            f"👥 {referrals}\n"
        )

    # USER RANK
    cursor.execute(
        """
        SELECT telegram_id
        FROM users
        ORDER BY coins DESC,
                 points DESC,
                 referrals DESC
        """
    )

    all_users = cursor.fetchall()

    user_rank = None

    for index, user in enumerate(all_users, start=1):

        if user[0] == user_id:

            user_rank = index
            break

    # SHOW USER POSITION
    if user_rank and user_rank > 10:

        cursor.execute(
            """
            SELECT user_code,
                   username,
                   coins,
                   points,
                   referrals
            FROM users
            WHERE telegram_id=?
            """,
            (user_id,)
        )

        current_user = cursor.fetchone()

        if current_user:

            (
                user_code,
                username,
                coins,
                points,
                referrals
            ) = current_user

            text += (
                f"\n━━━━━━━━━━━━━━\n"
                f"📍 Rank #{user_rank}\n"
                f"{user_code} | "
                f"@{username} | "
                f"🪙 {coins} | "
                f"💰 {points} | "
                f"👥 {referrals}"
            )

    await message.answer(text)


# REFERRAL COMMAND
@dp.message(Command("referral"))
async def referral(message: types.Message):

    user_id = message.from_user.id

    cursor.execute(
        "SELECT user_code FROM users WHERE telegram_id=?",
        (user_id,)
    )

    result = cursor.fetchone()

    if not result:

        await message.answer(
            "❌ Use /start first"
        )

        return

    user_code = result[0]

    bot_info = await bot.get_me()

    referral_link = (
        f"https://t.me/{bot_info.username}?start={user_code}"
    )

    await message.answer(
        f"🆔 Your User ID: {user_code}\n\n"
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
