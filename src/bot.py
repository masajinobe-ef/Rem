import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramNetworkError
import aiohttp

load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')

DATABASE_URL = 'sqlite:///reminders.db'
engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class Reminder(Base):
    __tablename__ = 'reminders'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, nullable=False)
    interval = Column(String, nullable=False)
    reminder_message = Column(Text, nullable=False)


Base.metadata.create_all(engine)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class ReminderStates(StatesGroup):
    select_interval = State()
    enter_message = State()


@dp.message(Command(commands=['help']))
async def cmd_start(message: Message):
    await message.answer(
        '`/remind` - Установить напоминание.\n'
        '`/delete_reminder` - Удалить напоминание.',
        parse_mode=ParseMode.MARKDOWN,
    )


@dp.message(Command(commands=['remind']))
async def cmd_remind(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='1 минута')],
            [KeyboardButton(text='5 минут')],
            [KeyboardButton(text='10 минут')],
            [KeyboardButton(text='15 минут')],
            [KeyboardButton(text='30 минут')],
            [KeyboardButton(text='1 час')],
            [KeyboardButton(text='2 часа')],
            [KeyboardButton(text='3 часа')],
            [KeyboardButton(text='6 часов')],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(
        'Выберите интервал для напоминания:',
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ReminderStates.select_interval)


@dp.message(ReminderStates.select_interval)
async def process_interval(message: Message, state: FSMContext):
    interval_mapping = {
        '1 минута': '1 минута',
        '5 минут': '5 минут',
        '10 минут': '10 минут',
        '15 минут': '15 минут',
        '30 минут': '30 минут',
        '1 час': '1 час',
        '2 часа': '2 часа',
        '3 часа': '3 часа',
        '6 часов': '6 часов',
    }

    interval = interval_mapping.get(message.text)
    if not interval:
        await message.answer(
            'Пожалуйста, выберите интервал из предложенных вариантов.',
            parse_mode=ParseMode.MARKDOWN,
        )
        print(
            f'[WARNING] Invalid interval input by user {message.chat.id}: {message.text}'
        )
        return

    await state.update_data(interval=interval)
    await message.answer(
        'Введите сообщение для напоминания.', parse_mode=ParseMode.MARKDOWN
    )
    await state.set_state(ReminderStates.enter_message)


@dp.message(ReminderStates.enter_message)
async def process_message(message: Message, state: FSMContext):
    user_data = await state.get_data()
    interval = user_data['interval']
    reminder_message = message.text

    session = Session()
    new_reminder = Reminder(
        chat_id=message.chat.id,
        interval=interval,
        reminder_message=reminder_message,
    )
    session.add(new_reminder)
    session.commit()
    session.close()

    await message.answer(
        f'*Напоминание установлено!*\n\n'
        f'Интервал: `{interval}`\n'
        f'Сообщение: `{reminder_message}`',
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.clear()
    delay = await calculate_delay(interval)
    asyncio.create_task(
        send_reminder(message.bot, message.chat.id, reminder_message, delay)
    )
    print(f'[INFO] Reminder created for user {message.chat.id}.')


async def send_reminder(bot, chat_id, reminder_message, delay):
    while True:
        if delay is None or delay <= 0:
            print(f'[ERROR] Invalid delay value: {delay}')
            break
        try:
            await asyncio.sleep(delay)
            await bot.send_message(chat_id, f'Напоминание: {reminder_message}')
        except TelegramNetworkError as e:
            print(f'[ERROR] Telegram network error: {e}')
            await asyncio.sleep(5)  # Retry after a short delay
        except aiohttp.ClientConnectorError as e:
            print(f'[ERROR] Network connection error: {e}')
            await asyncio.sleep(5)  # Retry after a short delay
        except Exception as e:
            print(f'[ERROR] Unexpected error: {e}')
            break


async def calculate_delay(interval_input):
    if '1 минута' in interval_input:
        return 1 * 60  # 1 минута
    elif '5 минут' in interval_input:
        return 5 * 60  # 5 минут
    elif '10 минут' in interval_input:
        return 10 * 60  # 10 минут
    elif '15 минут' in interval_input:
        return 15 * 60  # 15 минут
    elif '30 минут' in interval_input:
        return 30 * 60  # 30 минут
    elif '1 час' in interval_input:
        return 1 * 3600  # 1 час
    elif '2 часа' in interval_input:
        return 2 * 3600  # 2 часа
    elif '3 часа' in interval_input:
        return 3 * 3600  # 3 часа
    elif '6 часов' in interval_input:
        return 6 * 3600  # 6 часов
    else:
        print(f'[ERROR] Unknown interval: {interval_input}')
        return 60  # Default to 1 minute


@dp.message(Command(commands=['delete_reminder']))
async def cmd_delete_reminder(message: Message):
    session = Session()
    reminder = (
        session.query(Reminder)
        .filter(Reminder.chat_id == message.chat.id)
        .first()
    )
    session.close()

    if reminder:
        session = Session()
        session.delete(reminder)
        session.commit()
        session.close()
        await message.answer(
            '*Ваше напоминание было успешно удалено!*',
            parse_mode=ParseMode.MARKDOWN,
        )
        print(f'[INFO] Reminder deleted for user {message.chat.id}.')
    else:
        await message.answer(
            '*У вас нет установленного напоминания для удаления.*',
            parse_mode=ParseMode.MARKDOWN,
        )


async def main():
    bot = Bot(
        token=API_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        print('[INFO] Bot started!')
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print('[INFO] Bot stopped!')

