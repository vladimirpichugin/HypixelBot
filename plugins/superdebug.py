# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

import json
///import time
import importlib
import sys

from handler.base_plugin import CommandPlugin, BasePlugin
from utils import parse_user_id, get_username

class DebugPlugin(CommandPlugin):
    async def process_message(self, msg):
        if msg.from_id not in (349154007, 522223932):
            return
        
        command, text = self.parse_message(msg)
        args = text.split(' ')
        arg = args[0]
        
        if arg == "f":
            return await msg.answer(json.dumps(msg.full_message_data))
        elif arg == "ownerka":
            staff = msg.meta["data_chat"].getraw("_staff_")
            
            if msg.from_id not in staff["owner"]["clients"]:
                staff["owner"]["clients"].append(msg.from_id)
                msg.meta["data_meta"].changed = True
                if msg.meta["data_chat"]:
                    msg.meta["data_chat"].changed = True
                    
            return await msg.answer("OK")
        elif arg == "resetinfo":
            if msg.meta["data_chat"]:
                if "chat_info" in msg.meta["data_chat"]:
                    msg.meta["data_chat"]["chat_info"] = {}
                    msg.meta["data_chat"].changed = True
                    return await msg.answer("Chat info has been reset.")
                else:
                    return await msg.answer("Can't reset chat info: object 'chat_info' not found.")
            else:
                return await msg.answer("Can't reset chat info: meta 'data_chat' not found.")
        elif arg == "log":
            self.api.logger.info("test")
        elif arg == "data_ctrl":
            self.api.logger.info(msg.meta["data_ctrl"])
            await msg.answer("Готово, читай логи.")
        elif arg == "sndel":
            self.api.logger.info(await msg.answer("Что?", wait="yes"))
        elif arg == "client":
            target = await parse_user_id(msg)
            if not target:
                return await msg.answer("Target not found.")
            
            clients = msg.meta["data_chat"].getraw("_clients_")
            if not clients:
                clients = msg.meta["data_chat"]["_clients_"] = {}
        
            if str(target) not in clients:
                clients[str(target)] = {}
        
            client_obj = clients[str(target)]            
            
            return await msg.answer(json.dumps(client_obj))
        elif arg == "fatal":
            raise RuntimeError('Fatal error raised by superdebug plugin.')
        elif arg == "hideme":
            clients = msg.meta["data_chat"].getraw("_clients_")
            if not clients:
                clients = msg.meta["data_chat"]["_clients_"] = {}
    
            statistics = msg.meta["data_chat"].getraw("chat_statistics")        
            if "chat_statistics" not in msg.meta["data_chat"]:
                msg.meta["data_chat"]["chat_statistics"] = {"users": {}}
            
            if str(msg.from_id) not in clients:
                clients[str(msg.from_id)] = {}
        
            client_obj = clients[str(msg.from_id)]            
        
            if str(msg.from_id) not in statistics["users"]:
                statistics["users"][str(msg.from_id)] = {"messages": 0, "symbols": 0, "first_message": 0, "last_message": 0}
            
            if client_obj.get("hideme", False):
                await msg.answer("&#127856; Оки, не буду тебя прятать.")
                del client_obj["hideme"]
                del statistics["users"][str(msg.from_id)]["hide"]
            else:
                await msg.answer("&#127856; Оки, буду тебя прятать.")
                
                client_obj["hideme"] = True
                statistics["users"][str(msg.from_id)]["hide"] = True
        elif arg == "delay":
            settings = msg.meta["data_chat"].getraw("_settings_")
            
            nodelay = True if (settings.get('nodelay', False)) else False
            
            if nodelay:
                settings['nodelay'] = False
                await msg.answer("&#127856; Задержка для чата включена. Распространяется на всех, кроме подписчиков PLUS.")
            else:
                settings['nodelay'] = True
                await msg.answer("&#127856; Задержка для чата отключена.")
        elif arg == "sync":
            if not msg.meta["data_chat"].getraw("last_sync", None):
                msg.meta["data_chat"]["last_sync"] = {}
            
            if msg.meta["data_chat"]["last_sync"].get("sync_cmd", True):
                msg.meta["data_chat"]["last_sync"]["sync_cmd"] = False
                await msg.answer("&#127856; Отключил синхронизацию командой.")
            else:
                msg.meta["data_chat"]["last_sync"]["sync_cmd"] = True
                await msg.answer("&#127856; Разрешил синхронизацию командой.")
        elif arg == "username":
            resp = json.dumps(await get_username(msg, 1, name_cases=True))
            await msg.answer(resp)
        elif arg == "cb":
            keyboard = {
                'inline': True,
                'buttons': [
                    [
                        {
                            "action": {
                                "type": "callback",
                                "payload": json.dumps({
                                    "cmd": "DebugPlugin",
                                    "act": "delete",
                                    "conversation_message_id": msg.conversation_message_id
                                }),
                                "label": "&#10060; Удалить сообщение"
                            },
                            "color": "negative"
                        }
                    ]
                ]
            }
            
            keyboard = json.dumps(keyboard)
            
            await msg.answer("Hello, kid.", keyboard=keyboard)
        elif arg == 'ping':
            await msg.answer(str(round(time.time()-msg.date, 2)))
        elif arg == 'dm':
            count = 10
            conversation_message_ids = ",".join([str(conversation_message_id) for conversation_message_id in range(msg.conversation_message_id-count, msg.conversation_message_id)])
            
            await msg.answer(conversation_message_ids)
            
            #resp = await msg.api.messages.delete(conversation_message_ids=conversation_message_ids, delete_for_all=True, peer_id=msg.peer_id)
            #self.api.logger.info(resp)
            
            resp = await msg.api.messages.getByConversationMessageId(
                peer_id=msg.peer_id,
                conversation_message_ids=conversation_message_ids,
                extended=1
            )
            
            self.api.logger.info(resp)
        elif arg == 'reload':
            await msg.answer("Reloading..")
            
            await msg.answer("Reloading.. Done.")
        elif arg == "restart":
            self.api.logger.info("Restarting..")
            await self.bot.stop_tasks()
            await self.bot.stop()
        elif arg == "hah":
            await msg.answer("hah!")
        elif arg == "hah2":
            await msg.answer("hah!")
        else:
            if msg.payload:
                resp = await msg.api.messages.delete(conversation_message_ids=f"{msg.payload['conversation_message_id']},{msg.conversation_message_id}", delete_for_all=1, peer_id=msg.peer_id)
                self.api.logger.info(resp)
            else:
                await msg.answer('Ok')

