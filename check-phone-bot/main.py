import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, executor, types

from phone_checkers import phone_checkers

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
dp = Dispatcher(bot)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.answer("Отправь мне номер, чтобы получить о нём информацию.")


@dp.message_handler()
async def send_phone_number_reports(message: types.Message):
    phone_number = message.text
    checkers = [check(phone_number) for check in phone_checkers]
    no_information_found = True

    for check in asyncio.as_completed(checkers):
        report = await check
        if report['info']:
            no_information_found = False
            formatted_report = f"<b>Телефон: {phone_number}</b>\n\n"
            formatted_report += "\n\n".join(report['info'])
            formatted_report += f"\n\n<i>Ресурс: {report['resource']}</i>"
            await message.answer(formatted_report, parse_mode='HTML')

    if no_information_found:
        await message.answer(f'Нет информации по номеру {phone_number}')

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
