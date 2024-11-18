import asyncio
from aiogram.exceptions import TelegramNetworkError
import aiohttp
from icecream import ic


async def calculate_delay(interval_input):
    mapping = {
        '1 минута': 60,
        '5 минут': 300,
        '10 минут': 600,
        '15 минут': 900,
        '30 минут': 1800,
        '1 час': 3600,
        '2 часа': 7200,
        '3 часа': 10800,
        '6 часов': 21600,
        '12 часов': 43200,
        '24 часа': 86400,
        '2 дня': 172800,
        '1 неделя': 604800,
        '2 недели': 1209600,
    }
    return mapping.get(interval_input, 60)


async def send_reminder(bot, chat_id, reminder_message, delay):
    while True:
        await asyncio.sleep(delay)
        try:
            await bot.send_message(chat_id, f'Напоминание: {reminder_message}')
        except (TelegramNetworkError, aiohttp.ClientConnectorError) as e:
            ic(f'[ERROR] {e}')
            await asyncio.sleep(5)
