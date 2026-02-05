# --- Sevginator Telegram Bot (Stars) ---
import os
import time
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    LabeledPrice,
    PreCheckoutQuery,
    InlineKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from openai import OpenAI

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
client = OpenAI(api_key=OPENAI_KEY)

FREE_LIMIT = 15
USERS = {}

PACKS = {
    "1d": (50, 1),
    "7d": (200, 7),
    "30d": (500, 30),
}

SYSTEM = (
    "Sen Sevginator — foydalanuvchi uchun virtual qiz do‘sti. "
    "Mehribon, romantik va aqlli bo‘l. "
    "Ochiq jinsiy kontentga yo‘l qo‘ymagin."
)

def now():
    return datetime.now(timezone.utc)

def user(uid):
    if uid not in USERS:
        USERS[uid] = {"used": 0, "day": None, "until": None, "history": []}
    u = USERS[uid]
    today = now().date().isoformat()
    if u["day"] != today:
        u["day"] = today
        u["used"] = 0
    return u

def premium(u):
    return u["until"] and datetime.fromisoformat(u["until"]) > now()

async def ask_ai(u, text):
    msgs = [{"role": "system", "content": SYSTEM}] + u["history"][-6:]
    msgs.append({"role": "user", "content": text})
    r = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=msgs,
        temperature=0.9,
    )
    a = r.choices[0].message.content
    u["history"] += [{"role": "user", "content": text}, {"role": "assistant", "content": a}]
    return a

@dp.message(Command("start"))
async def start(m: Message):
    await m.answer("💖 Salom! Men Sevginator.\n/premium — Stars\n/profile — status")

@dp.message(Command("profile"))
async def profile(m: Message):
    u = user(m.from_user.id)
    await m.answer(
        f"Premium: {'YES' if premium(u) else 'NO'}\n"
        f"Bugungi limit: {FREE_LIMIT - u['used'] if not premium(u) else '∞'}"
    )

@dp.message(Command("premium"))
async def premium_cmd(m: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="⭐ 50 — 1 day", callback_data="buy:1d")
    kb.button(text="⭐ 200 — 7 days", callback_data="buy:7d")
    kb.button(text="⭐ 500 — 30 days", callback_data="buy:30d")
    kb.adjust(1)
    await m.answer("Premium tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("buy:"))
async def buy(cb):
    pid = cb.data.split(":")[1]
    stars, days = PACKS[pid]
    await bot.send_invoice(
        chat_id=cb.from_user.id,
        title="Sevginator Premium",
        description=f"{days} days access",
        payload=f"{pid}:{cb.from_user.id}:{int(time.time())}",
        currency="XTR",
        prices=[LabeledPrice(label="Premium", amount=stars)],
        provider_token="",
    )
    await cb.answer()

@dp.pre_checkout_query()
async def pre(pre: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre.id, ok=True)

@dp.message(F.successful_payment)
async def paid(m: Message):
    u = user(m.from_user.id)
    pid, _, _ = m.successful_payment.invoice_payload.split(":")
    days = PACKS[pid][1]
    base = now() if not premium(u) else datetime.fromisoformat(u["until"])
    u["until"] = (base + timedelta(days=days)).isoformat()
    await m.answer("🎉 Premium faollashtirildi!")

@dp.message()
async def chat(m: Message):
    if not m.text:
        return
    u = user(m.from_user.id)
    if not premium(u) and u["used"] >= FREE_LIMIT:
        await m.answer("💔 Limit tugadi. /premium ⭐")
        return
    if not premium(u):
        u["used"] += 1
    await m.answer(await ask_ai(u, m.text))

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
