import asyncio
import random
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# === НАСТРОЙКИ ===
API_TOKEN = '8255936453:AAEfRCrQV5Iqno5aFjGevWzO4uBqg5NJYKg' 
ADMIN_ID = 681384042  # Твой ID (для работы команды /fill)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# База данных
conn = sqlite3.connect('roulette.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS players 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   user_id TEXT, 
                   username TEXT, 
                   room_price INTEGER)''')
conn.commit()

ROOM_PRICES = [10, 30, 50, 100, 200]
TARGET_PLAYERS = 30 

# Постоянная кнопка "Играть"
main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Играть 🎲")]],
    resize_keyboard=True,
    is_persistent=True
)

# Функция генерации кнопок комнат
def get_rooms_kb():
    builder = InlineKeyboardBuilder()
    for price in ROOM_PRICES:
        builder.button(text=f"Войти: {price} ⭐", callback_data=f"join_{price}")
    builder.adjust(1)
    return builder.as_markup()

# === КОМАНДЫ ===

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"💎 Привет, {message.from_user.first_name}!\n"
        f"Нажми кнопку «Играть 🎲» или выбери комнату ниже.",
        reply_markup=main_kb
    )
    await message.answer("Выберите ставку:", reply_markup=get_rooms_kb())

@dp.message(F.text == "Играть 🎲")
async def play_button(message: types.Message):
    await message.answer("Доступные комнаты:", reply_markup=get_rooms_kb())

@dp.message(Command("fill"))
async def fill_with_bots(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    price = 10
    fake_names = ["Artem", "Daria", "Moon", "Satoshi", "Elena", "X_Player"]
    
    for _ in range(TARGET_PLAYERS):
        name = random.choice(fake_names) + str(random.randint(100, 999))
        cursor.execute("INSERT INTO players (user_id, username, room_price) VALUES (?, ?, ?)", 
                       ("0", name, price))
    conn.commit()
    
    await message.answer(f"🤖 Комната {price} ⭐ заполнена ботами!")
    await start_draw(message, price)

@dp.callback_query(F.data.startswith("join_"))
async def process_join(callback: types.CallbackQuery):
    price = int(callback.data.split("_")[-1])
    user_id = str(callback.from_user.id)
    username = callback.from_user.username or callback.from_user.first_name

    # ЗАЩИТА УБРАНА: Просто записываем каждое нажатие
    cursor.execute("INSERT INTO players (user_id, username, room_price) VALUES (?, ?, ?)", 
                   (user_id, username, price))
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM players WHERE room_price = ?", (price,))
    current_count = cursor.fetchone()[0]

    try:
        await callback.message.edit_text(
            f"✅ Участие принято! Комната {price} ⭐\n"
            f"Всего заявок: {current_count} из {TARGET_PLAYERS}",
            reply_markup=get_rooms_kb()
        )
    except:
        pass

    if current_count >= TARGET_PLAYERS:
        await start_draw(callback.message, price)
    else:
        await callback.answer("Заявка добавлена!")

async def start_draw(message, price):
    cursor.execute("SELECT user_id, username FROM players WHERE room_price = ?", (price,))
    all_players = cursor.fetchall()

    if len(all_players) < TARGET_PLAYERS:
        return

    await message.answer(f"🎰 Комната {price} ⭐ заполнена! Выбираем победителя...")
    await asyncio.sleep(3) 

    winner = random.choice(all_players)
    w_id, w_name = winner
    
    bank = price * len(all_players)
    fee = int(bank * 0.15)
    prize = bank - fee

    winner_link = f"<a href='tg://user?id={w_id}'>{w_name}</a>" if w_id != "0" else f"🤖 {w_name}"

    await message.answer(
        f"🎉 <b>РОЗЫГРЫШ ЗАВЕРШЕН!</b>\n\n"
        f"🏆 Победитель: {winner_link}\n"
        f"💰 Выигрыш: {prize} ⭐\n"
        f"🛡 Комиссия: {fee} ⭐\n\n"
        f"Новый набор открыт!",
        parse_mode="HTML",
        reply_markup=main_kb
    )

    # Очистка только для этой комнаты
    cursor.execute("DELETE FROM players WHERE room_price = ?", (price,))
    conn.commit()

async def main():
    print("Бот запущен. Накрутка разрешена. Кнопка активна.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
