import logging

import aiohttp
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


@phone_checker("https://ktozvonit.com.ua/")
async def ktozvonit_check(phone_number, resource=None):
    reports = list()
    url = f'{resource}number/{phone_number}/comments/1'
    response = await _request('GET', url)

    if response:
        soup = BeautifulSoup(response, 'html.parser')
        comments = soup.find_all('p', attrs={'class': 'question-desc'})
        for comment in comments:
            if isinstance(comment.contents, list):
                reports.append("\n".join(comment.contents))
            elif isinstance(comment.contents, str):
                reports.append(comment.contents)

    return reports


async def _request(method, url):
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url) as response:
            if response.ok:
                return await response.text()
            else:
                log.warning(f"Can't get info from {url}: {response.status}")
