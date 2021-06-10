import logging

import aiohttp
from aiohttp.client_exceptions import ClientError
from bs4 import BeautifulSoup, Tag

log = logging.getLogger(__name__)
phone_checkers = []


def phone_checker(resource):
    def decorator(checker):
        async def wrapper(*args, **kwargs):
            kwargs['resource'] = resource
            return {
                'resource': resource,
                'info': (await checker(*args, **kwargs)) or list()
            }

        phone_checkers.append(wrapper)
        return wrapper

    return decorator


async def _request(method, url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url) as response:
                if response.ok:
                    return await response.text()
                else:
                    log.warning(f"Can't get info from {url}: {response.status}")
    except ClientError as ex:
        log.error(f"Can't get info from: {url}: {ex}")


async def _fetch_comments(method, url, tag_name, tag_attrs):
    comments = list()

    response = await _request(method, url)
    if response:
        soup = BeautifulSoup(response, 'html.parser')
        comment_tags = soup.find_all(tag_name, attrs=tag_attrs)
        for comment_tag in comment_tags:
            if isinstance(comment_tag.contents, list):
                comments.append("\n".join(comment_tag.contents))
            elif isinstance(comment_tag.contents, str):
                comments.append(comment_tag.contents)

    return comments


def _filter_tags(element):
    return filter(lambda section: isinstance(section, Tag), element)


@phone_checker("https://ktozvonit.com.ua/")
async def ktozvonit_check(phone_number, resource=None):
    url = f'{resource}number/{phone_number}/comments/1'
    return await _fetch_comments('GET', url, 'p', {'class': 'question-desc'})


@phone_checker("https://ktozvonil.net/")
async def ktozvonil_check(phone_number, resource=None):
    url = f'{resource}nomer/{phone_number}'
    comment_attrs = {'class': 'content', 'itemprop': 'reviewBody'}
    return await _fetch_comments('GET', url, 'div', comment_attrs)


@phone_checker("https://mysmsbox.ru/")
async def mysmsbox_check(phone_number, resource=None):
    response = await _request('GET', f'{resource}phone-search/{phone_number}')
    if not response:
        return list()

    soup = BeautifulSoup(response, 'html.parser')
    info_blocks = soup.find_all('div', attrs={'class': 'info-blocks-in'})

    if not info_blocks:
        log.error(f'Unexpected response from {resource} for {phone_number}')
        log.error(response)
        return list()

    if len(info_blocks) == 1:
        if 'Номер не найден' in info_blocks[0].text:
            log.info(f'Cannot find number: {phone_number}.')
        else:
            log.warning(f'Too little info blocks: {info_blocks[0].text}')
        return list()

    phone_info_report = str()
    section_names = ['Тип телефонного номера', 'Оператор', 'Адрес']
    for phone_info_section in _filter_tags(info_blocks[0].children):
        for index, section_name in enumerate(section_names):
            if section_name in phone_info_section.text:
                section_info = phone_info_section.text.split(':')[1].strip()
                section_info = section_info.replace('\n', '')
                phone_info_report += f'{section_name}: {section_info}\n'
                del section_names[index]
                break

    comments_report = str()
    for comment_tag in soup.find_all('p', attrs={'itemprop': 'commentText'}):
        comments_report += f'{comment_tag.text}\n'

    return [
        phone_info_report or "Нет информации о номере.",
        comments_report or "Нет обсуждений номера."
    ]


if __name__ == '__main__':
    import asyncio

    reports = asyncio.run(mysmsbox_check("-4298fvf8s4v"))
    # reports = asyncio.run(mysmsbox_check('+380567161131'))
    print(reports)
