# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

from handler.base_plugin import CommandPlugin

import json, time

class SyncPlugin(CommandPlugin):
    async def process_message(self, msg):
        if not msg.is_chat:
            return await msg.answer("&#128573; Команду можно использовать только в беседе.")
        
        staff = msg.meta["data_chat"].getraw("_staff_") 

        if msg.meta["data_chat"]["last_sync"].get("sync_cmd", True) == False:
            return await msg.answer(f"&#128683; Синхронизация командой отключена в настройках беседы.")
                
        if not msg.meta["data_chat"].getraw("last_sync", None):
            msg.meta["data_chat"]["last_sync"] = {}
            
        sync_status = msg.meta["data_chat"]["last_sync"].get("ok", False)
        
        if sync_status:
            await msg.answer("&#9989; Синхронизация выполнена.")

            members = await self.bot.api.messages.getConversationMembers(peer_id=msg.peer_id)
            if members and "items" in members:
                for member in members.get("items"):
                    member_id = member.get("member_id")
                    
                    if member_id < 1:
                        continue
                    
                    if member.get("is_owner", False):
                        if member_id not in staff["owner"]["clients"]:
                            staff["owner"]["clients"].append(member_id)
                    elif member.get("is_admin", False):
                        if member_id not in staff["staff"]["clients"]:
                            staff["staff"]["clients"].append(member_id)
        else:
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
            
            msg.meta["data_meta"].changed = True
            if msg.meta["data_chat"]:
                msg.meta["data_chat"].changed = True
            
            return await msg.answer("&#128683; Синхронизация не выполнена.\n\nПопробуйте через минуту.", keyboard=json.dumps(keyboard))
