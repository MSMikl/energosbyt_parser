import asyncio
import logging

import aiohttp

import settings

from aiohttp import web
from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta

import asyncio


class State:
    states = {
        'binary': 'off',
        'state': '',
        'count': 0,
    }


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
    if len(results) == 0:
        State.states['binary'] = 'off'
        State.states['state'] = ''
        State.states['count'] = 0
    else:
        State.states['binary'] = 'on'
        unique_results = {f"{result.get('From')} - {result.get('To')} ({result.get('Description')}, {result.get('Condition')})": result for result in results}.values()
        State.states['state'] = '\n'.join([f"{result.get('From')} - {result.get('To')} ({result.get('Description')}, {result.get('Condition')})"
                                           for result in unique_results])
        State.states['count'] = len(unique_results)


async def give_shutdowns(request: web.BaseRequest):
    logger.info(f"Handling response from {request.remote}")
    return web.json_response(State.states)


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
