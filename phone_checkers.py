import logging

import aiohttp
from aiohttp.client_exceptions import ClientError
from bs4 import BeautifulSoup

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


async def _check(method, url, tag_name, tag_attrs):
    reports = list()

    response = await _request(method, url)
    if response:
        soup = BeautifulSoup(response, 'html.parser')
        comments = soup.find_all(tag_name, attrs=tag_attrs)
        for comment in comments:
            if isinstance(comment.contents, list):
                reports.append("\n".join(comment.contents))
            elif isinstance(comment.contents, str):
                reports.append(comment.contents)

    return reports


@phone_checker("https://ktozvonit.com.ua/")
async def ktozvonit_check(phone_number, resource=None):
    url = f'{resource}number/{phone_number}/comments/1'
    return await _check('GET', url, 'p', {'class': 'question-desc'})


@phone_checker("https://ktozvonil.net/")
async def ktozvonil_check(phone_number, resource=None):
    url = f'{resource}nomer/{phone_number}'
    comment_attrs = {'class': 'content', 'itemprop': 'reviewBody'}
    return await _check('GET', url, 'div', comment_attrs)
