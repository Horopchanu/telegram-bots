import hashlib
import logging
import os
import random
import string
import traceback
from urllib.parse import unquote

from aiogram.types.inline_keyboard import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types.inline_query_result import InlineQueryResultVideo
from aiogram.types.input_media import InputMediaVideo
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineQuery, InputTextMessageContent, \
    InlineQueryResultArticle, ChosenInlineResult
from aiogram.utils import executor
import aiohttp
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('tiktok-video-bot')

bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
dp = Dispatcher(bot)


async def fetch_tiktok_video(link) -> dict:
    log.info(f'Fetching TikTok video from {link} ...')

    service_url = "https://snaptik.app/"
    tiktok_video = dict()

    webdriver_options = Options()
    webdriver_options.headless = True
    webdriver_options.binary_location = os.environ.get('GOOGLE_CHROME_SHIM', None)

    with webdriver.WebDriver(executable_path="chromedriver", options=webdriver_options) as driver:
        try:
            driver.get(service_url)
            wait = WebDriverWait(driver, 5)
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input#url"))).send_keys(link)
            driver.find_element_by_id('submiturl').click()
            wait = WebDriverWait(driver, 5)
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "a.is-success")))
        except Exception as e:
            log.error(f'Error loading TikTok video page {link}: {e}')
            traceback.print_exc()
            driver.save_screenshot('screenshot.png')

        soup = BeautifulSoup(driver.page_source, "html.parser")
        log.info(f'Loaded service page: {soup}')

        user_avatar = soup.find('img', attrs={'class': 'lazy'})
        log.info(f'User avatar tag: {user_avatar}')
        if user_avatar:
            tiktok_video['title'] = user_avatar.get('alt')
            tiktok_video['thumb'] = user_avatar.get('src')

        video = soup.find('a', attrs={'class': 'is-success'})
        log.info(f'Video link tag: {video}')
        if video:
            tiktok_video['mime'] = 'video/mp4'
            video_url = video.get('href')
            if video_url and not video_url.startswith('http'):
                video_url = service_url + video_url
            tiktok_video['video'] = unquote(video_url)

    log.info(f'Got TikTok video from {link}: {tiktok_video}')

    return tiktok_video


async def download_video(url):
    filename = f"videos/{''.join(random.choice(string.ascii_lowercase) for i in range(32))}.mp4"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                video_bytes = await response.read()
                with open(filename, "wb") as video_file:
                    video_file.write(video_bytes)
    except Exception as ex:
        log.error(f'Error downloading video from {url}: {ex}')

    return filename

async def remove_video(filename):
    if os.path.exists(filename):
        os.remove(filename)
        log.info(f'Removed video: {filename}')
    else:
        log.warning(f'Trying to remove not existing video: {filename}')


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.answer("Send me link to TikTok video & I will download and send it back to you.")


@dp.message_handler()
async def send_video(message: types.Message):
    link = message.text
    if link:
        tiktok_video = await fetch_tiktok_video(link)
        if tiktok_video.get('video'):
            await bot.send_video(
                chat_id=message.chat.id, video=tiktok_video['video'],
                caption=tiktok_video.get('title'), reply_to_message_id=message.message_id)
        else:
            await message.reply('Cannot load video.')


@dp.inline_handler()
async def select_inline_video(inline_query: InlineQuery):
    link = inline_query.query
    if link:
        input_content = InputTextMessageContent(link)
        result_id: str = hashlib.md5(link.encode()).hexdigest()
        inline_keyboard = [[InlineKeyboardButton(text='Downloading...', callback_data='downloading')]]
        item = InlineQueryResultArticle(
            id=result_id, title=f'TikTok video {link}', input_message_content=input_content,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard))
        await bot.answer_inline_query(inline_query.id, results=[item], cache_time=1)


@dp.chosen_inline_handler()
async def send_chosen_inline_video(chosen_inline_result: ChosenInlineResult):
    link = chosen_inline_result.query
    message_id = chosen_inline_result.inline_message_id
    if not link or not message_id:
        return

    tiktok_video = await fetch_tiktok_video(link)
    if not tiktok_video.get('video'):
        await bot.edit_message_text(f'No video found on: {link}')
        return

    await bot.edit_message_text('Not accessible for now.')
    # TOOD: uncomment when telegram will allow send video as the response for inline query
    # filename = await download_video(tiktok_video['video'])
    # try:
    #     with open(filename, 'rb') as video:
    #         media = InputMediaVideo(media=video, thumb=tiktok_video.get('thumb'), caption=tiktok_video.get('title'))
    #         await bot.edit_message_media(media, inline_message_id=message_id)
    # except Exception as ex:
    #     log.error(f'Error uploading video: {ex}')
    # finally:
    #     await remove_video(filename)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

    # import asyncio
    # import time
    # test_link = 'https://vm.tiktok.com/ZMdRSxBL7/'
    # test_tiktok_video = asyncio.run(fetch_tiktok_video(test_link))
    # print(test_tiktok_video)
    # filename = asyncio.run(download_video(test_tiktok_video.get('video')))
    # print(filename)
    # # time.sleep(1000)
    # asyncio.run(remove_video(filename))
