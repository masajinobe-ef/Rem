from aiogram import Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db import Session, Reminder
from utils import calculate_delay
import asyncio


class ReminderStates(StatesGroup):
    select_interval = State()
    enter_message = State()
    delete_reminder = State()


async def safe_send_message(bot, chat_id, text, retries=5, delay=2):
    """Retries sending message on failure."""
    attempt = 0
    while attempt < retries:
        try:
            await bot.send_message(
                chat_id, text, parse_mode=ParseMode.MARKDOWN
            )
            return
        except Exception as e:
            attempt += 1
            print(f'Error on attempt {attempt}: {e}')
            if attempt >= retries:
                print('Failed to send message after multiple retries.')


async def cmd_help(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text='/remind'),
                KeyboardButton(text='/list_reminders'),
                KeyboardButton(text='/delete_reminder'),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await safe_send_message(
        message.bot,
        message.chat.id,
        '`/remind` - Установить напоминание.\n'
        '`/delete_reminder` - Удалить напоминание.\n'
        '`/list_reminders` - Показать список ваших напоминаний.',
        retries=5,
        delay=2,
    )

    await message.answer(
        'Выберите команду из предложенных ниже или введите её вручную:',
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_remind(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='1 минута'), KeyboardButton(text='5 минут')],
            [KeyboardButton(text='10 минут'), KeyboardButton(text='15 минут')],
            [KeyboardButton(text='30 минут'), KeyboardButton(text='1 час')],
            [KeyboardButton(text='2 часа'), KeyboardButton(text='3 часа')],
            [KeyboardButton(text='6 часов'), KeyboardButton(text='12 часов')],
            [KeyboardButton(text='24 часа'), KeyboardButton(text='2 дня')],
            [KeyboardButton(text='1 неделя'), KeyboardButton(text='2 недели')],
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
        '12 часов': '12 часов',
        '24 часа': '24 часа',
        '2 дня': '2 дня',
        '1 неделя': '1 неделя',
        '2 недели': '2 недели',
    }

    user_input = message.text.strip()
    interval = interval_mapping.get(user_input)

    if not interval:
        await message.answer(
            'Пожалуйста, выберите интервал из предложенных вариантов.',
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await state.update_data(interval=interval)
    await message.answer(
        'Введите сообщение для напоминания.', parse_mode=ParseMode.MARKDOWN
    )
    await state.set_state(ReminderStates.enter_message)


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


async def send_reminder(bot, chat_id, reminder_message, delay):
    while True:
        await asyncio.sleep(delay)
        await bot.send_message(chat_id, f'Напоминание: {reminder_message}')


async def cmd_list_reminders(message: Message):
    session = Session()
    reminders = (
        session.query(Reminder)
        .filter(Reminder.chat_id == message.chat.id)
        .all()
    )

    if not reminders:
        await message.answer(
            '*У вас нет активных напоминаний.*', parse_mode=ParseMode.MARKDOWN
        )
        session.close()
        return

    reminders_text = '\n'.join(
        [
            f'{reminder.id}: {reminder.reminder_message} (интервал: {reminder.interval})'
            for reminder in reminders
        ]
    )
    await message.answer(
        f'*Ваши напоминания:*\n\n{reminders_text}',
        parse_mode=ParseMode.MARKDOWN,
    )
    session.close()


async def cmd_delete_reminder(message: Message, state: FSMContext):
    session = Session()
    reminders = (
        session.query(Reminder)
        .filter(Reminder.chat_id == message.chat.id)
        .all()
    )

    if not reminders:
        await message.answer(
            '*У вас нет напоминаний для удаления.*',
            parse_mode=ParseMode.MARKDOWN,
        )
        session.close()
        return

    reminders_text = '\n'.join(
        [
            f'{reminder.id}: {reminder.reminder_message} (интервал: {reminder.interval})'
            for reminder in reminders
        ]
    )
    await message.answer(
        f'*Ваши напоминания:*\n\n{reminders_text}\n\nВведите ID напоминания, чтобы удалить его.',
        parse_mode=ParseMode.MARKDOWN,
    )
    session.close()
    await state.set_state(ReminderStates.delete_reminder)


async def process_delete_reminder(message: Message, state: FSMContext):
    try:
        reminder_id = int(message.text)
    except ValueError:
        await message.answer('Пожалуйста, введите корректный ID.')
        return

    session = Session()
    reminder = (
        session.query(Reminder).filter(Reminder.id == reminder_id).first()
    )

    if not reminder:
        await message.answer('Напоминание с указанным ID не найдено.')
        session.close()
        return

    session.delete(reminder)
    session.commit()
    session.close()

    await message.answer(
        '*Напоминание удалено!*', parse_mode=ParseMode.MARKDOWN
    )
    await state.clear()


def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_help, Command(commands=['help']))
    dp.message.register(cmd_remind, Command(commands=['remind']))
    dp.message.register(process_interval, ReminderStates.select_interval)
    dp.message.register(process_message, ReminderStates.enter_message)
    dp.message.register(
        cmd_list_reminders, Command(commands=['list_reminders'])
    )
    dp.message.register(
        cmd_delete_reminder, Command(commands=['delete_reminder'])
    )
    dp.message.register(
        process_delete_reminder, ReminderStates.delete_reminder
    )

