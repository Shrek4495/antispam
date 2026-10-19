import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import ChatTypeFilter

# --- НАСТРОЙКИ ---
API_TOKEN = '8845906304:AAHKqme0R89-8O1qrKzfRPCPFHBfwECEcK4'
# ID отправителя, чьи сообщения нужно удалять (пока стоит ID бота)
TARGET_SENDER_ID = 2129127435
# Точное название вкладки (темы)
TARGET_TOPIC_TITLE = "Приемная"
# -----------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
dp = Dispatcher()

async def get_topic_id_by_title(chat_id: int, title: str) -> int | None:
    try:
        topics = await dp.bot.get_forum_topic_list(chat_id)
        for topic in topics.topics:
            if topic.name == title:
                return topic.message_thread_id
    except Exception as e:
        logging.error(f"Не удалось получить список тем: {e}")
    return None

@dp.message(ChatTypeFilter([types.ChatType.SUPERGROUP, types.ChatType.CHANNEL]))
async def delete_target_messages(message: types.Message):
    # Игнорируем сообщения в общей ленте
    if message.message_thread_id is None:
        return

    # Находим ID нужного топика по названию
    target_topic_id = await get_topic_id_by_title(message.chat.id, TARGET_TOPIC_TITLE)
    
    # Если топик не найден или сообщение пришло в другую тему
    if target_topic_id is None or message.message_thread_id != target_topic_id:
        return

    sender_id = None
    
    # Проверяем разных отправителей (обычный юзер, пересланное сообщение, анонимный админ)
    if message.from_user:
        sender_id = message.from_user.id
    elif message.forward_from:
        sender_id = message.forward_from.id
    # Если сообщение отправлено от имени канала/группы (анонимный админ), from_user будет None
    # Удалить такое сообщение можно только если ваш бот - владелец группы, но по ID отправителя это не сработает

    if sender_id == TARGET_SENDER_ID:
        try:
            await message.delete()
            logging.info(f"Удалено сообщение (ID: {message.message_id}) от {sender_id} в теме '{TARGET_TOPIC_TITLE}'")
        except Exception as e:
            # Самая частая ошибка здесь: "Forbidden: message can't be deleted by bot"
            logging.error(f"Ошибка при удалении сообщения {message.message_id}: {e}")

async def main():
    bot = Bot(token=API_TOKEN, parse_mode="HTML")
    
    # Проверка прав и наличия топика при старте
    try:
        me = await bot.get_me()
        logging.info(f"Запуск бота @{me.username}")
        
        # Проверяем, что группа/канал имеет темы
        topics = await bot.get_forum_topic_list(bot.id) # Здесь лучше использовать ID вашей группы, если он известен
        if not any(t.name == TARGET_TOPIC_TITLE for t in topics.topics):
            logging.critical(f"Топик '{TARGET_TOPIC_TITLE}' не найден. Бот остановлен.")
            return
    except Exception as e:
        logging.error(f"Критическая ошибка при старте: {e}")
        return

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
