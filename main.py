import asyncio
import random
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# === НАСТРОЙКИ ===
API_TOKEN = '8255936453:AAEfRCrQV5Iqno5aFjGevWzO4uBqg5NJYKg' # Вставь сюда токен от @BotFather
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Настройка базы данных (создается файл roulette.db на телефоне)
conn = sqlite3.connect('roulette.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS players 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   user_id TEXT, 
                   username TEXT, 
                   room_price INTEGER)''')
conn.commit()

ROOM_PRICES = [10, 30, 50, 100, 200] # ИСПРАВЛЕНО: Добавлены цены
TARGET_PLAYERS = 30 # Сколько человек нужно для розыгрыша

# === КОМАНДЫ ===

# Приветствие и меню
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    for price in ROOM_PRICES:
        builder.button(text=f"Войти: {price} ⭐", callback_data=f"join_{price}")
    builder.adjust(1)
    
    await message.answer(
        f"💎 Привет, {message.from_user.first_name}!\n\n"
        "Это Рулетка 2026. Выбери комнату для игры.\n"
        f"Как только наберется {TARGET_PLAYERS} участников, бот выберет победителя!",
        reply_markup=builder.as_markup()
    )

# Команда для тебя (админа): заполнить ботами комнату на 10 звезд
@dp.message(Command("fill"))
async def fill_with_bots(message: types.Message):
    price = 10
    fake_names = ["Artem_PRO", "Daria_V", "MoonWalker", "Satoshi_N", "Elena", "X_Player"]
    for _ in range(25):
        name = random.choice(fake_names) + str(random.randint(100, 999))
        cursor.execute("INSERT INTO players (user_id, username, room_price) VALUES (?, ?, ?)", 
                       ("0", name, price))
    conn.commit()
    await message.answer(f"🤖 25 ботов добавлены в комнату {price} ⭐!")

# ... (начало кода совпадает)

# Обработка нажатия кнопок
@dp.callback_query(F.data.startswith("join_"))
async def process_join(callback: types.CallbackQuery):
    price = int(callback.data.split("_")[-1])
    user_id = str(callback.from_user.id)
    username = callback.from_user.username or callback.from_user.first_name

    # 1. Записываем игрока
    cursor.execute("INSERT INTO players (user_id, username, room_price) VALUES (?, ?, ?)", 
                   (user_id, username, price))
    conn.commit()

    # 2. СРАЗУ проверяем актуальное количество в этой комнате
    cursor.execute("SELECT COUNT(*) FROM players WHERE room_price = ?", (price,))
    result = cursor.fetchone()
    current_count = result[0] if result else 0

    # 3. Редактируем сообщение (с защитой от ошибок Telegram)
    try:
        await callback.message.edit_text(
            f"✅ Участие принято в комнате {price} ⭐\n"
            f"Собрано участников: {current_count} из {TARGET_PLAYERS}\n\n"
            "Ожидайте завершения набора!"
        )
    except Exception:
        pass

    # 4. Если набралось НУЖНОЕ количество (или больше) — запускаем
    if current_count >= TARGET_PLAYERS:
        await start_draw(callback.message, price)
    else:
        await callback.answer("Вы добавлены!")

# Логика розыгрыша
async def start_draw(message, price):
    # Получаем список всех участников этой комнаты
    cursor.execute("SELECT user_id, username FROM players WHERE room_price = ?", (price,))
    all_players = cursor.fetchall()

    # Проверка на случай системного сбоя
    if not all_players or len(all_players) < TARGET_PLAYERS:
        return

    await message.answer(f"🎰 ВНИМАНИЕ! Комната {price} ⭐ заполнена! Выбираем счастливчика...")
    await asyncio.sleep(2) 

    # ВЫБОР ПОБЕДИТЕЛЯ
    winner = random.choice(all_players)
    w_id, w_name = winner
    
    bank = price * len(all_players)
    fee = int(bank * 0.15)
    prize = bank - fee

    # Красивое упоминание (работает даже если нет username)
    winner_link = f"<a href='tg://user?id={w_id}'>{w_name}</a>"

    await message.answer(
        f"🎉 <b>РОЗЫГРЫШ ЗАВЕРШЕН!</b>\n\n"
        f"🏆 Победитель: {winner_link}\n"
        f"💰 Выигрыш: {prize} ⭐ (чистыми)\n"
        f"🛡 Комиссия системы: {fee} ⭐\n\n"
        f"Поздравляем! Новая игра открыта.",
        parse_mode="HTML"
    )

    # Очистка базы для этой комнаты
    cursor.execute("DELETE FROM players WHERE room_price = ?", (price,))
    conn.commit()

# Запуск бота
async def main():
    print("Бот запущен в 2026 году. Проверь свой Telegram!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")

