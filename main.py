import asyncio
import logging
from dateutil import parser

import aiohttp

import settings

from aiohttp import web
from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta

import asyncio
from dataclasses import dataclass

# Mapping of Russian month names to English
MONTHS_MAP = {
    "января": "January",
    "февраля": "February",
    "марта": "March",
    "апреля": "April",
    "мая": "May",
    "июня": "June",
    "июля": "July",
    "августа": "August",
    "сентября": "September",
    "октября": "October",
    "ноября": "November",
    "декабря": "December"
}

def preprocess_date(date_str):
    for ru_month, en_month in MONTHS_MAP.items():
        if ru_month in date_str:
            date_str = date_str.replace(ru_month, en_month)
            break
    return date_str

@dataclass
class State:
    state: str = ''
    time_start: datetime = datetime.now()
    time_end: datetime = datetime.now()
    binary: str = 'off'

class CurrentStates:
    binary: str = 'off'
    last_checked = datetime.now()
    items: list[State] = []


logger = logging.getLogger(__name__)


async def check_plans(url, params: dict[str] = {}, timeout: int = 120, retries: int = 3):
    logger.info('start parsing')
    timeout = aiohttp.ClientTimeout(timeout)
    now = datetime.now()
    params.update({
        'from': now.strftime('%d.%m.%Y'),
        'to': (now + timedelta(days=25)).strftime('%d.%m.%Y'),
    })
    headers = {
        'User-Agent': 'PostmanRuntime/7.28.4',
        'Connection': 'keep-alive',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'ru,en-US;q=0.9,en;q=0.8,tr;q=0.7',
        'Sec-Ch-Ua': '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
        'Referer': 'https://pdo.gridcom-rt.ru/(X(1)S(pe1xmur4jrfff3zo0dfupcai))/PowerInterruptions/AllInterruptions',
        'Host': 'pdo.gridcom-rt.ru'
    }
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while retries:
            try:
                response = await session.get(url, params=params, headers=headers)
                response.raise_for_status()
            except TimeoutError:
                retries -= 1
                logger.info(
                    f'Parsing timeout. Trying again. {retries} retries remaining')
                continue
            else:
                break
        if not response.status or response.status != 200:
            logger.warning(f'Parsing unsuccessful')
            return
        parsed_response = await response.json()
        logger.debug(parsed_response)
        results = parsed_response.get('Model', {}).get('AllDataModel', [])
    CurrentStates.last_checked = datetime.now()
    CurrentStates.items = []
    unique_results = set()
    for result in results:
        state = f"{result.get('From')} - {result.get('To')} ({result.get('Description')}, {result.get('Condition')})"
        if state in unique_results:
            continue
        CurrentStates.items.append(State(
            binary='on',
            state=state,
            time_start=parser.parse(preprocess_date(result.get('From'))),
            time_end=parser.parse(preprocess_date(result.get('To'))),
        ))
    if len(CurrentStates.items) == 0:
        CurrentStates.binary = 'off'
    else:
        CurrentStates.binary = 'on'


async def give_shutdowns(request: web.BaseRequest):
    logger.info(f"Handling response from {request.remote}")
    return web.json_response({
        "binary": CurrentStates.binary,
        "last_checked": CurrentStates.last_checked.isoformat(),
        "items": [
            {
                "state": item.state,
                "time_start": item.time_start.isoformat(),
                "time_end": item.time_end.isoformat()
            }
            for item in CurrentStates.items
        ]
    })


async def server(request: web.BaseRequest):
    if (request.path == '/shutdowns/' and request.method == 'GET'):
        return await give_shutdowns(request)
    return web.HTTPNotFound()


async def checker():
    logger.setLevel(settings.LOG_LEVEL)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(settings.LOG_LEVEL)
    logger.addHandler(stream_handler)
    url = "https://pdo.gridcom-rt.ru/api/Ajax/GetInterruptions"
    params = {
        'SearchText': 'п Инеш, М.Джалиля, д. 11,',
        'Page': 1,
        'PageSize': 5,
        'From': '',
        'To': ''
    }

    async with AsyncScheduler() as scheduler:
        await scheduler.add_schedule(check_plans, IntervalTrigger(seconds=settings.PARSING_INTERVAL),
                                     kwargs={
            'url': url,
            'params': params,
        })
        scheduler.logger.setLevel(logging.DEBUG)
        scheduler.logger.addHandler(logging.StreamHandler())
        handler = web.Server(server)
        runner = web.ServerRunner(handler)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        logger.info("======= Serving on http://127.0.0.1:8080/ ======")
        await scheduler.run_until_stopped()


def main():
    asyncio.run(checker())


if __name__ == '__main__':
    main()
