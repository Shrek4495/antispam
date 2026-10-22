import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties

# --- НАСТРОЙКИ ---
API_TOKEN = '8845906304:AAHKqme0R89-8O1qrKzfRPCPFHBfwECEcK4'
TARGET_BOT_ID = 123456789  
TARGET_TOPIC_TITLE = "ПРИЕМНАЯ"
GROUP_ID = -1004461327716 
# -----------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
dp = Dispatcher()

target_topic_id: int | None = None

async def find_topic_id(chat_id: int, title: str) -> int | None:
    try:
        topics = await dp.bot.get_forum_topic_list(chat_id)
        for topic in topics.topics:
            if topic.name == title:
                return topic.message_thread_id
    except Exception as e:
        logging.error(f"Не удалось получить список тем: {e}")
    return None

async def check_admin_privileges() -> bool:
    """Проверяет права с учетом разных версий aiogram 3.x"""
    try:
        me = await dp.bot.get_me()
        admins = await dp.bot.get_chat_administrators(GROUP_ID)
        
        for admin in admins:
            if admin.user.id == me.id:
                # Поддержка старой структуры (где нет объекта .privileges)
                if hasattr(admin, 'can_delete_messages') and admin.can_delete_messages:
                    logging.info("Привилегия 'Удаление сообщений' подтверждена (старая структура прав).")
                    return True
                
                # Поддержка новой структуры (3.7+)
                if hasattr(admin, 'privileges') and admin.privileges and admin.privileges.can_delete_messages:
                    logging.info("Привилегия 'Удаление сообщений' подтверждена (новая структура прав).")
                    return True

                logging.critical("У бота есть права админа, но НЕТ привилегии 'Удаление сообщений'.")
                return False
    except Exception as e:
        logging.error(f"Не удалось проверить привилегии: {e}")
    return False

@dp.message(lambda message: message.chat.type in [types.ChatType.SUPERGROUP, types.ChatType.CHANNEL])
async def delete_target_bot_messages(message: types.Message):
    global target_topic_id

    if message.message_thread_id is None:
        return

    if message.message_thread_id != target_topic_id:
        return

    if message.from_user and message.from_user.is_bot and message.from_user.id == TARGET_BOT_ID:
        try:
            await message.delete()
            logging.info(f"Удалено сообщение (ID: {message.message_id}) от бота {TARGET_BOT_ID}")
        except Exception as e:
            if "message is too old" in str(e):
                logging.warning(f"Сообщение {message.message_id} старше 24 часов.")
            elif "message can't be deleted" in str(e):
                logging.error(f"Нет прав на удаление сообщения {message.message_id}.")
            else:
                logging.error(f"Неизвестная ошибка при удалении {message.message_id}: {e}")

async def main():
    bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp.bot = bot

    me = await bot.get_me()
    logging.info(f"Запуск бота @{me.username}")

    # 1. Проверка привилегий
    if not await check_admin_privileges():
        logging.critical("Бот не имеет прав на удаление. Работа невозможна.")
        return

    # 2. Поиск темы
    global target_topic_id
    target_topic_id = await find_topic_id(GROUP_ID, TARGET_TOPIC_TITLE)

    if target_topic_id is None:
        logging.critical(f"Топик '{TARGET_TOPIC_TITLE}' не найден. Бот остановлен.")
        return
    
    logging.info(f"Топик '{TARGET_TOPIC_TITLE}' (ID: {target_topic_id}) мониторится.")

    try:
        await dp.start_polling(bot, allowed_updates=["message"])
    finally:
        # Исправление ошибки "Unclosed client session"
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
