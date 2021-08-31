# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

import traceback
import sys, json
from random import randint

from utils import random_key, has_perms, get_role_obj_by_plugin, get_random_smile, create_report


class MessageHandler:
    def __init__(self, bot, api, initiate_plugins=True):
        self.bot = bot
        self.api = api

        self.plugins = []
        self.exceptions = []

        for plugin in self.bot.settings.PLUGINS:
            plugin.set_up(self.bot, self.api, self)
            self.plugins.append(plugin)

        if initiate_plugins:
            self.initiate_plugins()

    def initiate_plugins(self):
        for plugin in self.plugins:
            self.bot.logger.info(f"Preload: {plugin.name}")
            plugin.preload()

        for plugin in self.plugins:
            self.bot.logger.info(f"Initiate: {plugin.name}")
            plugin.initiate()

    async def process(self, msg):
        if msg.from_id < 0:
            return None    
        
        try:
            res = await self.core_process(msg)

            for plugin in sorted(self.plugins, key=lambda x: x.order[-1]):
                if await plugin.global_after_message_process(msg, res) is False:
                    break
        except:
            exception = traceback.format_exc()
            self.exceptions.append(exception)
            error_key = random_key(10)
            
            self.bot.logger.error(f"Error id: {error_key} (errors: {len(self.exceptions)})\n{exception}")
            
            if len(self.exceptions) <= 10:
                keyboard = await create_report(err_code=error_key, plugin='_handler_controller', msg=msg, return_keyboard=True, register=True)
                
                await msg.answer(
                    f"&#10071; При обработке события произошла ошибка (#{error_key}).\n&#128140; Отчёт отправлен разработчику.",
                    keyboard=keyboard,
                    random_id=randint(0, int(2e20))
                )         
                
                client = "id" if msg.from_id > 0 else "public"
                target = f"https://vk.com/gim{self.api.get_current_id()}?msgid={msg.msg_id}&sel={abs(msg.from_id)}" if not msg.is_chat else f"беседа #{2000000000+int(msg.chat_id)}"
                await msg.api.messages.send(
                    peer_ids=','.join(str(user_id) for user_id in [349154007, 522223932]),
                    message=f"[ @{client}{abs(msg.from_id)} произошло исключение ({target}). ]\n[ {exception} ]\n[ {len(self.exceptions)}:{error_key} ]",
                    random_id=randint(0, int(2e20))
                )
            

    async def core_process(self, msg):
        self.bot.logger.debug(f"Processing message ({msg.msg_id})")
        
        for plugin in sorted(self.plugins, key=lambda x: x.order[0]):
            if await plugin.global_before_message_checks(msg) is False:
                self.bot.logger.debug(f"Message cancelled with {plugin.name}")
                return None

        for plugin in self.plugins:
            if await plugin.check_message(msg):
                subres = await self.process_with_plugin(msg, plugin)

                if subres is not False:
                    self.bot.logger.debug(f"Message ({msg.msg_id}) completed with {plugin.name}")
                    return subres

        self.bot.logger.debug(f"Processed message ({msg.msg_id})")

    async def process_with_plugin(self, msg, plugin):
        if not await has_perms(msg, plugin):
            plugin_name = plugin.name
            if hasattr(plugin, "description"):
                if plugin.description:
                    plugin_name = plugin.description[0]
            
            role = await get_role_obj_by_plugin(msg, plugin)
            if role and "info" in role:
                role = role["info"].get("name", None)
                
            return await msg.answer(f"&#128683; Команда «{plugin_name}» доступна с роли {f'«{role}»' if role else 'выше'}.")
        
        for p in self.plugins:
            if await p.global_before_message(msg, plugin) is False:
                return
        
        result = await plugin.process_message(msg)

        for p in self.plugins:
            await p.global_after_message(msg, plugin, result)

        return result

    async def process_event(self, evnt):
        res = await self.core_process_event(evnt)
        
        for plugin in self.plugins:
            if await plugin.global_after_event_process(evnt, res) is False:
                break

    async def core_process_event(self, evnt):
        self.bot.logger.debug(f"Processing event ({evnt.type})")
        
        for plugin in self.plugins:
            if await plugin.global_before_event_checks(evnt) is False:
                self.bot.logger.debug(f"Event {evnt.type} cancelled with {plugin.name}")
                return

        for plugin in self.plugins:
            if await plugin.check_event(evnt):
                subres = await self.process_event_with_plugin(evnt, plugin)

                if subres is not False:
                    self.bot.logger.debug(f"Finished with event ({evnt.type}) on {plugin.name}")
                    return subres
        
        self.bot.logger.debug(f"Processed event ({evnt.type})")

    async def process_event_with_plugin(self, evnt, plugin):
        for p in self.plugins:
            if await p.global_before_event(evnt, plugin) is False:
                return

        result = await plugin.process_event(evnt)

        for p in self.plugins:
            await p.global_after_event(evnt, plugin, result)

        return result

    async def stop(self):
        for plugin in self.plugins:
            self.bot.logger.info(f"Stopping plugin: {plugin.name}")
            await plugin.stop()
