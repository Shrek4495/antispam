import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties

# --- НАСТРОЙКИ ---
API_TOKEN = '8845906304:AAHKqme0R89-8O1qrKzfRPCPFHBfwECEcK4'
TARGET_BOT_ID = -2129127435  
TARGET_TAB_ID = 1          # ID вашей вкладки "ПРИЕМНАЯ"
GROUP_ID = -1004461327716  # ID вашего канала
# -----------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
dp = Dispatcher()

def get_tab_id(message: types.Message) -> int | None:
    """Извлекает ID вкладки из сырых данных для версий aiogram 3.1-3.2."""
    if not hasattr(message, 'raw_api') or not message.raw_api:
        return None
    return message.raw_api.get('topic_id')

async def check_admin_privileges(bot: Bot, chat_id: int) -> bool:
    try:
        me = await bot.get_me()
        admins = await bot.get_chat_administrators(chat_id)
        
        for admin in admins:
            if admin.user.id == me.id:
                if (hasattr(admin, 'can_delete_messages') and admin.can_delete_messages) or \
                   (hasattr(admin, 'privileges') and admin.privileges and admin.privileges.can_delete_messages):
                    logging.info("Привилегия 'Удаление сообщений' подтверждена.")
                    return True
                logging.critical("У бота есть права админа, но НЕТ привилегии 'Удаление сообщений'.")
                return False
    except Exception as e:
        logging.error(f"Не удалось проверить привилегии: {e}")
    return False

@dp.message(lambda message: message.chat.id == GROUP_ID)
async def delete_target_bot_messages(message: types.Message):
    # Фильтруем сообщения только из нужной вкладки
    if get_tab_id(message) != TARGET_TAB_ID:
        return

    # Проверяем, что сообщение от целевого бота
    if message.from_user and message.from_user.is_bot and message.from_user.id == TARGET_BOT_ID:
        try:
            await message.delete()
            logging.info(f"Удалено сообщение (ID: {message.message_id}) от бота {TARGET_BOT_ID}")
        except Exception as e:
            error_str = str(e)
            if "message is too old" in error_str:
                logging.warning(f"Сообщение {message.message_id} старше 24 часов.")
            elif "message can't be deleted" in error_str or "not enough rights" in error_str:
                logging.error(f"Нет прав на удаление сообщения {message.message_id}.")
            else:
                logging.error(f"Ошибка при удалении {message.message_id}: {e}")

async def main():
    bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp.bot = bot

    me = await bot.get_me()
    logging.info(f"Запуск бота @{me.username}")

    if not await check_admin_privileges(bot, GROUP_ID):
        logging.critical("Бот не имеет прав на удаление. Работа невозможна.")
        await bot.session.close()
        return

    logging.info(f"Канал {GROUP_ID}, вкладка ID {TARGET_TAB_ID} — мониторинг начат.")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Критическая ошибка поллинга: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
