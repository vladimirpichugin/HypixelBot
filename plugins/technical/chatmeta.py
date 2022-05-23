# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

from handler.base_plugin import BasePlugin
from utils import EventType

import asyncio, time, json

class ChatMetaPlugin(BasePlugin):
    __slots__ = ("chats",)

    def __init__(self):
        """Adds `chat_info` to messages and events's meta["data_chat"] with
        chat's data if available (https://vk.com/dev/messages.getChat). You can
        refresh data with coroutine stored in `meta['chat_info_refresh']`."""
        super().__init__()

        self.order = (-99, 99)

        self.chats = {}

    async def update_chat_info(self, entity, instant_refresh=False):
        """Argument `entity` must be Message or Event"""
        if not entity.is_chat or not entity.meta.get("data_chat"):
            return False
        
        data_chat = entity.meta["data_chat"]     
        
        if "chat_info" not in data_chat:
            data_chat["chat_info"] = {}
        
        if "last_sync" not in data_chat:
            data_chat["last_sync"] = {}   
        
        if not instant_refresh:
            if data_chat["last_sync"].get("timestamp", None):
                if data_chat["last_sync"]["timestamp"]+60 >= time.time():
                    return True
            
            if data_chat["last_sync"].get("problem_timestamp", None):
                if data_chat["last_sync"]["problem_timestamp"]+60 >= time.time():
                    return True            

        members = await self.api.messages.getConversationMembers(
            peer_id=entity.peer_id,
            fields="sex,screen_name,first_name_nom,first_name_gen,first_name_dat,first_name_acc,first_name_ins,first_name_abl,last_name_nom,last_name_gen,last_name_dat,last_name_acc,last_name_ins,last_name_abl"
        ) or {}
        
        if "items" in members:
            data_chat["chat_info"]["items"] = members["items"]
            data_chat["chat_info"]["users"] = members["profiles"]
            data_chat["chat_info"]["groups"] = members["groups"]

            data_chat["last_sync"]["ok"] = True
            data_chat["last_sync"]["timestamp"] = int(time.time())  
            
            if "timestamp_problem" in data_chat["last_sync"]:
                del data_chat["last_sync"]["timestamp_problem"]
            if "timestamp_alert" in data_chat["last_sync"]:
                del data_chat["last_sync"]["timestamp_alert"]
        else:
            data_chat["last_sync"]["ok"] = False
            data_chat["last_sync"]["timestamp_problem"] = int(time.time())
            
            if data_chat["last_sync"].get("timestamp_alert", None):
                if data_chat["last_sync"]["timestamp_alert"]+1800 >= time.time():
                    return True
                
            data_chat["last_sync"]["timestamp_alert"] = int(time.time())
            
            message = "&#128521; Назначьте меня админом беседы, а потом нажмите на кнопку «&#9989; Синхронизировать».\n\nHypeBot не обслуживает беседы без прав администратора. Это связано с особенностью реализации: мы получаем список участников беседы, это экономит запросы и ускоряет бота."
            keyboard = {
                "inline": True,
                "buttons": [
                    [
                        {
                            "action": {
                                "type": "open_link",
                                "label": "&#128073; Как выдать админку?",
                                "link": "https://vk.com/@hypixelbot-setup-admin"
                            }
                        }
                    ],
                    [
                        {
                            "action": {
                                "type": "text",
                                "label": "&#9989; Синхронизировать",
                                "payload": json.dumps({
                                    "cmd": "SyncPlugin"
                                })
                            },
                            "color": "positive"
                        }
                    ]
                ]
            }
            
            if not hasattr(entity, "msg"):    
                pass
                #await entity.answer(message, keyboard=json.dumps(keyboard))
        
        return True

    def create_refresh(self, entity, instant_refresh=False):
        """Argument `entity` must be Message or Event"""

        async def func():
            return await self.update_chat_info(entity, instant_refresh)

        return func

    async def global_before_message_checks(self, msg):
        if await self.update_chat_info(msg):
            msg.meta["chat_info_refresh"] = self.create_refresh(msg)

    async def global_before_event_checks(self, evnt):
        if not evnt.is_chat:
            return

        if await self.update_chat_info(evnt):
            evnt.meta["chat_info_refresh"] = self.create_refresh(evnt, True)
    
    async def check_event(self, evnt):
        if evnt.action_type in ("chat_invite_user", "chat_invite_user_by_link", "chat_kick_user"):
            await evnt.meta["chat_info_refresh"]()
            
        return False

    async def process_event(self, evnt):
        if evnt.action_type in ("chat_invite_user", "chat_invite_user_by_link", "chat_kick_user"):
            await evnt.meta["chat_info_refresh"]()
        
        return False
