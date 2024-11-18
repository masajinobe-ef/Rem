import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from icecream import ic
from handlers import register_handlers
from config import API_TOKEN


async def main():
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    bot = Bot(
        token=API_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Register handlers
    register_handlers(dp)

    ic('[INFO] Started')
    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        ic('[INFO] Stopped')


if __name__ == '__main__':
    asyncio.run(main())
