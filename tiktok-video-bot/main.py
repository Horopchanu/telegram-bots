import hashlib
import logging
import os

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineQuery, InputTextMessageContent, \
    InlineQueryResultVideo

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
dp = Dispatcher(bot)


async def fetch_tiktok_video(link) -> str:
    return ""


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.answer("Send me link to TikTok video & I will download and "
                         "send it back to you.")


@dp.message_handler
async def send_video(message: types.Message):
    pass


@dp.inline_handler()
async def send_inline_video(inline_query: InlineQuery):
    text = inline_query.query
    if text:
        input_content = InputTextMessageContent(text)
        result_id: str = hashlib.md5(text.encode()).hexdigest()
        item = InlineQueryResultVideo(

        )

        await bot.answer_inline_query(inline_query.id, results=[item],
                                      cache_time=1)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)