import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aiogram import Bot

from app.config import get_settings


async def main() -> None:
    bot = Bot(get_settings().telegram_bot_token)
    try:
        me = await bot.get_me()
        print(f"bot_username={me.username}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
