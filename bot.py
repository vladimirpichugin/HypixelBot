# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

import asyncio, aiohttp, json, time, logging
from asyncio import Task

from handler.handler_controller import MessageHandler
from utils import VkController
from utils import Message, ChatChangeEvent
from utils import MessageEventData
from utils import is_blacklisted

class Bot:
    __slots__ = (
        "api", "handler", "logger", "logger_file", "loop",
        "tasks", "sessions", "requests", "settings"
    )

    def __init__(self, settings, logger=None, handler=None, loop=None):
        self.settings = settings

        if logger:
            self.logger = logger
        else:
            self.logger = self.init_logger()

        if loop:
            self.loop = loop
        else:
            self.loop = asyncio.get_event_loop()
        
        self.logger.info("Initializing bot")

        self.requests = []
        self.sessions = []
        self.tasks = []

        self.logger.info("Initializing vk clients")
        self.api = VkController(settings, logger=self.logger, loop=self.loop)

        self.logger.info("Loading plugins")
        if handler:
            self.handler = handler

        else:
            self.handler = MessageHandler(self, self.api, initiate_plugins=False)
            self.handler.initiate_plugins()

        self.logger.info("Bot successfully initialized")

    def init_logger(self):
        logger = logging.Logger("hypebot", level=logging.DEBUG if self.settings.DEBUG else logging.INFO)

        formatter = logging.Formatter(
            fmt=u'[%(asctime)s] %(levelname)-8s: %(message)s',
            datefmt='%y.%m.%d %H:%M:%S')

        file_handler = logging.FileHandler('logs.txt')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        self.logger_file = file_handler

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level=logging.DEBUG if self.settings.DEBUG else logging.INFO)
        stream_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

        return logger

    def add_task(self, task):
        for ctask in self.tasks[::]:
            if ctask.done() or ctask.cancelled():
                self.tasks.remove(ctask)

        if task.done() or task.cancelled():
            return

        self.tasks.append(task)

        return task

    def bots_longpoll_run(self, custom_process=False):
        task = self.add_task(Task(self.bots_longpoll_processor()))

        if custom_process:
            return task

        self.logger.info("Started to process messages")

        try:
            self.loop.run_until_complete(task)
        except (KeyboardInterrupt, SystemExit):
            self.loop.run_until_complete(self.stop())
        except asyncio.CancelledError:
            pass

    async def init_bots_long_polling(self, pack, update=0):
        result = None

        for _ in range(4):
            result = await self.api(sender=self.api.target_client).\
                groups.getLongPollServer(group_id=self.api.get_current_id())

            if result:
                break

            time.sleep(0.5)

        if not result:
            self.logger.error("Unable to connect to VK's bots long polling server.")
            exit()

        if update == 0:
            pack[1] = result['server']
            pack[0]['key'] = result['key']
            pack[0]['ts'] = result['ts']

        elif update == 2:
            pack[0]['key'] = result['key']

        elif update == 3:
            pack[0]['key'] = result['key']
            pack[0]['ts'] = result['ts']

    async def bots_longpoll_processor(self):
        pack = [{'act': 'a_check', 'key': '', 'ts': 0,
            'wait': 25}, ""]

        await self.init_bots_long_polling(pack)

        session = aiohttp.ClientSession(loop=self.loop)
        self.sessions.append(session)

        while True:
            try:
                requ = session.get(pack[1], params=pack[0])
            except aiohttp.ClientOSError:
                await asyncio.sleep(0.5)
                continue

            self.requests.append(requ)

            try:
                events = json.loads(await (await requ).text())

            except aiohttp.ClientOSError:
                try:
                    self.sessions.remove(session)
                except ValueError:
                    pass

                await asyncio.sleep(0.5)

                session = aiohttp.ClientSession(loop=self.loop)
                self.sessions.append(session)
                continue

            except (asyncio.TimeoutError, aiohttp.ServerDisconnectedError):
                self.logger.warning("Long polling server doesn't respond. Changing server.")
                await asyncio.sleep(0.5)

                await self.init_bots_long_polling(pack)
                continue

            except ValueError:
                await asyncio.sleep(0.5)
                continue

            finally:
                if requ in self.requests:
                    self.requests.remove(requ)

            failed = events.get('failed')

            if failed:
                err_num = int(failed)

                if err_num == 1:  # 1 - update timestamp
                    if 'ts' not in events:
                        await self.init_bots_long_polling(pack)
                    else:
                        pack[0]['ts'] = events['ts']

                elif err_num in (2, 3):  # 2, 3 - new data for long polling
                    await self.init_bots_long_polling(pack, err_num)

                continue

            pack[0]['ts'] = events['ts']

            for event in events['updates']:
                if "type" not in event or "object" not in event:
                    continue
                
                event_type = event["type"]
                obj = event["object"]
                
                if event_type in ('message_new', 'message_event'):
                    msg = Message(self.api, MessageEventData.from_message_body(obj))
                    
                    if await is_blacklisted(msg) >= 4:
                        continue  
                    
                    if event_type == 'message_new':
                        if await self.check_event(msg):
                            msg.is_event = True
                    else:
                        msg.is_event = True
                        
                    if await is_blacklisted(msg) >= 3:
                        continue                      
                    
                    await self.process_message(msg)

    async def check_event(self, msg):
        if msg.is_chat and msg.action:
            evnt = ChatChangeEvent(self.api, msg)
            
            await self.process_event(evnt)

            return True
        
        return False

    async def process_message(self, msg):
        asyncio.ensure_future(self.handler.process(msg), loop=self.loop)
        
    async def process_event(self, evnt):
        asyncio.ensure_future(self.handler.process_event(evnt), loop=self.loop)

    def coroutine_exec(self, coroutine):
        if asyncio.iscoroutine(coroutine) or isinstance(coroutine, asyncio.Future):
            return self.loop.run_until_complete(coroutine)

        return False

    async def stop_tasks(self):
        self.logger.info("Attempting stop bot")

        for task in self.tasks:
            try:
                task.cancel()
            except Exception:
                pass

        self.logger.info("Stopped to process messages")

    async def stop(self):
        self.logger.info("Attempting to turn bot off")

        for session in self.sessions:
            await session.close()

        await self.handler.stop()
        await self.api.stop()

        for task in self.tasks:
            try:
                task.cancel()
            except Exception:
                pass
        
        self.logger.info("Stopped to process messages")
        self.logger.removeHandler(self.logger_file)
        self.logger_file.close()
