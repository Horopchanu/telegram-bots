import hashlib
import logging
import os
import random
import re
import string

import aiofiles as aiofiles
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineQuery, InputTextMessageContent, \
    InlineQueryResultArticle, ChosenInlineResult, InputMedia
from aiogram.utils import executor
from aiohttp import ClientError
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('tiktok-video-bot')

bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
dp = Dispatcher(bot)


async def fetch_tiktok_video(link) -> dict:
    log.info(f'Fetching TikTok video from {link} ...')

    tiktok_video = dict()

    webdriver_options = Options()
    webdriver_options.headless = True

    with webdriver.WebDriver(options=webdriver_options) as driver:
        try:
            driver.get(link)
            wait = WebDriverWait(driver, 3)
            wait.until(EC.visibility_of_element_located((By.ID, "main")))
        except Exception as e:
            log.error(f'Error loading TikTok video page {link}: {e}')
            driver.save_screenshot('screenshot.png')

        soup = BeautifulSoup(driver.page_source, "html.parser")
        title = soup.find('a', attrs={'class': 'user-avatar'})
        if title:
            tiktok_video['title'] = title.get('title')

        user_avatar = soup.find('span', attrs={'class': 'tiktok-avatar'})
        if user_avatar:
            for avatar in user_avatar.children:
                tiktok_video['thumb'] = avatar.get('src')

        video = soup.find('video', attrs={'class': 'video-player'})
        if video:
            video_url = video.get('src')
            if video_url:
                tiktok_video['video'] = video_url
                mime_type_match = re.search('mime_type=\\w+', video_url)
                if mime_type_match:
                    mime_type = mime_type_match.group().split('=')[1:]
                    mime_type = mime_type[0] if mime_type else str()
                    tiktok_video['mime'] = mime_type.replace('_', '/')

    log.info(f'Got TikTok video from {link}: {tiktok_video}')

    return tiktok_video


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.answer("Send me link to TikTok video & I will download and "
                         "send it back to you.")


@dp.message_handler()
async def send_video(message: types.Message):
    link = message.text
    if link:
        tiktok_video = await fetch_tiktok_video(link)
        await bot.send_video(
            chat_id=message.chat.id,
            video=tiktok_video.get('video'),
            caption=tiktok_video.get('title', 'TikTok Video'),
            reply_to_message_id=message.message_id
        )


@dp.inline_handler()
async def select_inline_video(inline_query: InlineQuery):
    link = inline_query.query
    if link:
        input_content = InputTextMessageContent(link)
        result_id: str = hashlib.md5(link.encode()).hexdigest()
        item = InlineQueryResultArticle(
            id=result_id,
            title=f'TikTok video {link}',
            input_message_content=input_content,
        )
        await bot.answer_inline_query(inline_query.id, results=[item],
                                      cache_time=1)


@dp.chosen_inline_handler()
async def send_chosen_inline_video(chosen_inline_result: ChosenInlineResult):
    link = chosen_inline_result.query
    message_id = chosen_inline_result.from_user.id
    if link and message_id:
        tiktok_video = await fetch_tiktok_video(link)
        await bot.send_video(
            chat_id=message_id,
            video=tiktok_video.get('video'),
            thumb=tiktok_video.get('thumb'),
            caption=tiktok_video.get('title')
        )


if __name__ == '__main__':
    # executor.start_polling(dp, skip_updates=True)

    import asyncio
    test_link = 'https://vm.tiktok.com/ZMdRSxBL7/'
    test_tiktok_video = asyncio.run(fetch_tiktok_video(test_link))
    print(test_tiktok_video)
