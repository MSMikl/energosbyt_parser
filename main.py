import asyncio
import logging

import aiohttp

import settings

from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta

import asyncio

logger = logging.getLogger(__name__)

async def check_plans(url, params: dict[str] = {}, timeout: int = 120, retries: int = 3):
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
                logger.info(f'Parsing timeout. Trying again. {retries} retries remaining')
                continue
            else:
                break
        if not response.status or response.status != 200:
            logger.warning(f'Parsing unsuccessful')
            return
        results = (await response.json()).get('items', [])
    if len(results) == 0:
        binary = 'off'
        state = ''
    else:
        binary = 'on'
        state = '\n'.join([f"{result.get('From')} - {result.get('To', '').split(',')[1]}"
                            for result in results])
    binary_hass_url = f"{settings.HASS_URL}api/states/{settings.HASS_BINARY_SENSOR_NAME}"
    state_hass_url = f"{settings.HASS_URL}api/states/{settings.HASS_STATE_SENSOR_NAME}"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {settings.HASS_API_TOKEN}'
    }
    binary_data = {"state": binary}
    state_data = {"state": state}
    async with aiohttp.ClientSession() as session:
        response = await session.post(binary_hass_url, headers=headers, json=binary_data)
        logger.info(await response.text())
        response = await session.post(state_hass_url, headers=headers, json=state_data)
        logger.info(await response.text())


async def checker():
    async with AsyncScheduler() as scheduler:
        logger.setLevel(settings.LOG_LEVEL)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(settings.LOG_LEVEL)
        logger.addHandler(stream_handler)
        url = settings.PARSING_URL
        params = {
            'region': 'п. Инеш, ул. М.Джалиля, д. 11',
            'manualSettlement': 'п. Инеш, ул. М.Джалиля, д. 11',
            'orderDirection': 0,
            'page': 1,
            'isSettlement': 'true',
            'isManualStreet': 'true',
            'pageSize': 10
        }
        await scheduler.add_schedule(check_plans, IntervalTrigger(seconds=settings.PARSING_INTERVAL),
                                     kwargs={
                                         'url': url,
                                         'params': params,
                                     })
        scheduler.logger.setLevel(logging.DEBUG)
        scheduler.logger.addHandler(logging.StreamHandler())
        await scheduler.run_until_stopped()


def main():
    asyncio.run(checker())


if __name__ == '__main__':
    main()