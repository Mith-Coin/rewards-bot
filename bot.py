import asyncio
import sqlite3
import random
from datetime import datetime, timedelta, time
from urllib.parse import quote
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os

# =========================
# LOAD ENV
# =========================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# =========================
# BOT SETUP
# =========================
bot = Bot(token=BOT_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# =========================
# DATABASE
# =========================
conn = sqlite3.connect("/data/mith.db", check_same_thread=False)
cursor = conn.cursor()

# =========================
# IST TIMEZONE
# =========================
IST = ZoneInfo("Asia/Kolkata")

# =========================
# USERS TABLE
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    user_code TEXT UNIQUE,
    username TEXT,
    coins REAL DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    wallet TEXT,
    last_daily TEXT
)
""")

conn.commit()

# =========================
# SOCIAL LINKS
# =========================
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
# START BUTTON
# =========================
def start_button():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏠 Start",
                    callback_data="show_menu"
                )
            ]
        ]
    )

# =========================
# CANCEL BUTTON
# =========================
def cancel_button():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_transfer"
                )
            ]
        ]
    )

# =========================
# CHECK DAILY ELIGIBILITY
# =========================
def can_claim_daily(last_daily):

    if not last_daily:
        return True

    try:

        last_claim = datetime.fromisoformat(last_daily).astimezone(IST)

        now = datetime.now(IST)

        return now.date() > last_claim.date()

    except:
        return True

# =========================
# TIME LEFT FOR NEXT RESET
# =========================
def time_until_midnight_ist():

    now = datetime.now(IST)

    tomorrow = now.date() + timedelta(days=1)

    midnight = datetime.combine(
        tomorrow,
        time.min,
        tzinfo=IST
    )

    remaining = midnight - now

    hours = int(
        remaining.total_seconds() // 3600
    )

    minutes = int(
        (remaining.total_seconds() % 3600) // 60
    )

    return hours, minutes

# =========================
# MAIN MENU
# =========================
def main_menu(user_id):

    buttons = [

        # SOCIAL BUTTONS
        [
            InlineKeyboardButton(
                text="📸 Instagram",
                url=INSTAGRAM_URL
            ),

            InlineKeyboardButton(
                text="💬 Community",
                url=TELEGRAM_COMMUNITY_URL
            ),

            InlineKeyboardButton(
                text="📢 Group",
                url=TELEGRAM_GROUP_URL
            )
        ],

        [
            InlineKeyboardButton(
                text="💰 Balance",
                callback_data="balance"
            ),

            InlineKeyboardButton(
                text="🔁 Transfer",
                callback_data="transfer"
            )
        ],

        [
            InlineKeyboardButton(
                text="👥 Referral",
                callback_data="referral"
            )
        ],

        [
            InlineKeyboardButton(
                text="🏆 Leaderboard",
                callback_data="leaderboard"
            )
        ]
    ]

    # DAILY BUTTON VISIBILITY
    cursor.execute(
        "SELECT last_daily FROM users WHERE telegram_id=?",
        (user_id,)
    )

    data = cursor.fetchone()

    show_daily = True

    if data and data[0]:

        if not can_claim_daily(data[0]):
            show_daily = False

    if show_daily:

        buttons.insert(
            3,
            [
                InlineKeyboardButton(
                    text="🎁 Daily Reward",
                    callback_data="daily"
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

# =========================
# START
# =========================
@dp.message(Command("start"))
async def start(message: types.Message):

    user_id = message.from_user.id
    username = message.from_user.username or "User"

    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None

    cursor.execute(
        "SELECT * FROM users WHERE telegram_id=?",
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:

        cursor.execute(
            "SELECT MAX(CAST(user_code AS INTEGER)) FROM users"
        )

        last = cursor.fetchone()[0]

        user_code = (
            str(int(last) + 1)
            if last else "100001"
        )

        cursor.execute("""
            INSERT INTO users (
                telegram_id,
                user_code,
                username,
                coins
            )
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            user_code,
            username,
            100
        ))

        # REFERRAL REWARD
        if referral_code:

            cursor.execute(
                "SELECT telegram_id FROM users WHERE user_code=?",
                (referral_code,)
            )

            ref = cursor.fetchone()

            if ref and ref[0] != user_id:

                cursor.execute("""
                    UPDATE users
                    SET coins = coins + 300,
                        referrals = referrals + 1
                    WHERE telegram_id=?
                """, (ref[0],))

        conn.commit()

    await message.answer(
        "🎁 Welcome to MITH Rewards\n\n"
        "Select an option below 👇",
        reply_markup=main_menu(user_id)
    )

# =========================
# BALANCE
# =========================
async def balance(message: types.Message, user_id=None):

    if not user_id:
        user_id = message.from_user.id

    cursor.execute("""
        SELECT
            user_code,
            coins,
            referrals
        FROM users
        WHERE telegram_id=?
    """, (user_id,))

    data = cursor.fetchone()

    if not data:

        return await message.answer(
            "❌ Use /start first",
            reply_markup=start_button()
        )

    code, coins, refs = data

    await message.answer(
        f"🆔 ID: {code}\n"
        f"🪙 MITH Coins: {coins}\n"
        f"👥 Referrals: {refs}",
        reply_markup=start_button()
    )

# =========================
# DAILY
# =========================
async def daily(message: types.Message, user_id=None):

    if not user_id:
        user_id = message.from_user.id

    cursor.execute(
        "SELECT last_daily FROM users WHERE telegram_id=?",
        (user_id,)
    )

    data = cursor.fetchone()

    if data and data[0]:

        if not can_claim_daily(data[0]):

            hours, minutes = time_until_midnight_ist()

            return await message.answer(
                f"⏳ Next reward at 12:00 AM IST\n"
                f"Time remaining: {hours}h {minutes}m",
                reply_markup=start_button()
            )

    reward = random.randint(50, 100)

    cursor.execute("""
        UPDATE users
        SET coins = coins + ?,
            last_daily = ?
        WHERE telegram_id=?
    """, (
        reward,
        datetime.now(IST).isoformat(),
        user_id
    ))

    conn.commit()

    await message.answer(
        f"🎁 You earned {reward} MITH Coins",
        reply_markup=start_button()
    )

# =========================
# REFERRAL
# =========================
async def referral(message: types.Message, user_id=None):

    if not user_id:
        user_id = message.from_user.id

    cursor.execute(
        "SELECT user_code FROM users WHERE telegram_id=?",
        (user_id,)
    )

    data = cursor.fetchone()

    if not data:

        return await message.answer(
            "❌ Use /start first",
            reply_markup=start_button()
        )

    code = data[0]

    bot_info = await bot.get_me()

    link = (
        f"https://t.me/"
        f"{bot_info.username}?start={code}"
    )

    share_text = (
        "🚀 Join MITH Rewards and earn FREE MITH Coins!\n\n"
        f"{link}"
    )

    share_url = (
        "https://t.me/share/url?"
        f"url={quote(link)}"
        f"&text={quote(share_text)}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏠 Start",
                    callback_data="show_menu"
                ),

                InlineKeyboardButton(
                    text="📤 Share",
                    url=share_url
                )
            ]
        ]
    )

    await message.answer(
        f"👥 Referral Link:\n\n"
        f"{link}\n\n"
        f"🎁 Earn 300 MITH Coins per referral!",
        reply_markup=keyboard
    )

# =========================
# LEADERBOARD
# =========================
async def leaderboard(message: types.Message, user_id=None):

    if not user_id:
        user_id = message.from_user.id

    text = "🏆 MITH LEADERBOARD\n\n"

    cursor.execute("""
        SELECT
            user_code,
            coins
        FROM users
        ORDER BY
            coins DESC
        LIMIT 10
    """)

    top = cursor.fetchall()

    for i, u in enumerate(top, 1):

        code, coins = u

        text += (
            f"{i}. {code} | "
            f"🪙 {coins}\n"
        )

    await message.answer(
        text,
        reply_markup=start_button()
    )

# =========================
# TRANSFER START
# =========================
async def transfer_start(
    message: types.Message,
    state: FSMContext,
    user_id=None
):

    if not user_id:
        user_id = message.from_user.id

    cursor.execute(
        "SELECT coins FROM users WHERE telegram_id=?",
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:

        return await message.answer(
            "❌ Use /start first",
            reply_markup=start_button()
        )

    balance_value = user[0]

    await state.set_state(
        TransferState.waiting_for_user_code
    )

    await message.answer(
        f"💰 Your Balance: "
        f"{balance_value} MITH Coins\n\n"
        f"👤 Enter receiver USER CODE:",
        reply_markup=cancel_button()
    )

# =========================
# GET USER CODE
# =========================
@dp.message(TransferState.waiting_for_user_code)
async def get_user_code(
    message: types.Message,
    state: FSMContext
):

    receiver_code = message.text.strip()

    cursor.execute(
        "SELECT telegram_id FROM users WHERE user_code=?",
        (receiver_code,)
    )

    receiver = cursor.fetchone()

    if not receiver:

        return await message.answer(
            "❌ Invalid user code. Try again:",
            reply_markup=cancel_button()
        )

    await state.update_data(
        receiver_code=receiver_code
    )

    await state.set_state(
        TransferState.waiting_for_amount
    )

    await message.answer(
        "💰 Enter the number of "
        "MITH Coins to transfer:",
        reply_markup=cancel_button()
    )

# =========================
# EXECUTE TRANSFER
# =========================
@dp.message(TransferState.waiting_for_amount)
async def execute_transfer(
    message: types.Message,
    state: FSMContext
):

    sender_id = message.from_user.id

    try:

        amount = float(
            message.text.strip()
        )

    except ValueError:

        return await message.answer(
            "❌ Enter valid number",
            reply_markup=cancel_button()
        )

    if amount <= 0:

        return await message.answer(
            "❌ Invalid amount",
            reply_markup=cancel_button()
        )

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

        return await message.answer(
            "❌ Use /start first",
            reply_markup=start_button()
        )

    sender_balance, sender_code = sender

    if sender_code == receiver_code:

        await state.clear()

        return await message.answer(
            "❌ Cannot transfer to yourself",
            reply_markup=start_button()
        )

    if sender_balance < amount:

        await state.clear()

        return await message.answer(
            "❌ Insufficient balance\n"
            "🚫 Transfer cancelled",
            reply_markup=start_button()
        )

    cursor.execute(
        "SELECT telegram_id FROM users WHERE user_code=?",
        (receiver_code,)
    )

    receiver = cursor.fetchone()

    if not receiver:

        await state.clear()

        return await message.answer(
            "❌ Receiver not found",
            reply_markup=start_button()
        )

    receiver_id = receiver[0]

    # TRANSFER
    cursor.execute("""
        UPDATE users
        SET coins = coins - ?
        WHERE telegram_id=?
    """, (
        amount,
        sender_id
    ))

    cursor.execute("""
        UPDATE users
        SET coins = coins + ?
        WHERE telegram_id=?
    """, (
        amount,
        receiver_id
    ))

    conn.commit()

    await state.clear()

    await message.answer(
        f"✅ Transfer successful!\n\n"
        f"🪙 Sent: {amount} MITH Coins\n"
        f"👤 To: {receiver_code}",
        reply_markup=start_button()
    )

# =========================
# COMMANDS
# =========================
@dp.message(Command("balance"))
async def balance_command(message: types.Message):
    await balance(message, message.from_user.id)

@dp.message(Command("daily"))
async def daily_command(message: types.Message):
    await daily(message, message.from_user.id)

@dp.message(Command("leaderboard"))
async def leaderboard_command(message: types.Message):
    await leaderboard(message, message.from_user.id)

@dp.message(Command("referral"))
async def referral_command(message: types.Message):
    await referral(message, message.from_user.id)

@dp.message(Command("transfer"))
async def transfer_command(
    message: types.Message,
    state: FSMContext
):
    await transfer_start(
        message,
        state,
        message.from_user.id
    )

# =========================
# CALLBACK ROUTER
# =========================
@dp.callback_query()
async def callback_router(
    callback: types.CallbackQuery,
    state: FSMContext
):

    data = callback.data
    user_id = callback.from_user.id

    try:

        if data == "show_menu":

            await callback.message.answer(
                "🏠 Main Menu",
                reply_markup=main_menu(user_id)
            )

        elif data == "cancel_transfer":

            await state.clear()

            await callback.message.answer(
                "❌ Transfer Cancelled",
                reply_markup=main_menu(user_id)
            )

        elif data == "balance":

            await balance(
                callback.message,
                user_id
            )

        elif data == "daily":

            await daily(
                callback.message,
                user_id
            )

        elif data == "referral":

            await referral(
                callback.message,
                user_id
            )

        elif data == "leaderboard":

            await leaderboard(
                callback.message,
                user_id
            )

        elif data == "transfer":

            await transfer_start(
                callback.message,
                state,
                user_id
            )

        await callback.answer()

    except Exception as e:

        print("Callback Error:", e)

        await callback.message.answer(
            "❌ Something went wrong",
            reply_markup=start_button()
        )

# =========================
# MAIN
# =========================
async def main():

    print("🚀 MITH Bot Running...")

    await dp.start_polling(bot)

# =========================
# RUN BOT
# =========================
if __name__ == "__main__":
    asyncio.run(main())
