# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

from handler.base_plugin import CommandPlugin
from utils import EventType, get_username, get_random_smile, get_user_sex

import json, random, time

class AutoKickPlugin(CommandPlugin):
    def __init__(self):
        self.order = (-96, 96)
        super().__init__()
        
    async def check_event(self, evnt):
        return evnt.type == EventType.ChatChange
    
    async def process_event(self, evnt):
        if evnt.action_type in ("chat_kick_user", ):
            settings = evnt.meta["data_chat"].getraw("_settings_")
            auto_kick = True if (settings.get("auto_kick", False)) else False
            
            if evnt.msg.action.get("member_id") == evnt.msg.from_id:
                member_id = evnt.msg.from_id

                icon = await get_random_smile()
                username = await get_username(evnt.msg, member_id, only_first_name=False)
                
                if auto_kick:
                    result = await self.api.messages.removeChatUser(
                        member_id=member_id,
                        chat_id=evnt.msg.chat_id
                    )

                    sex = await get_user_sex(member_id, evnt.msg)                    
                    if result == 1:
                        message = f"&#128546; {username} вышла из беседы и была исключена." if sex == 1 else f"&#128546; {username} вышел из беседы и был исключён."
                        keyboard = {
                            "inline": True,
                            "buttons": [
                                [
                                    {
                                        "action":{
                                            "type": "text", 
                                            "label": f"{icon} Профиль", 
                                            "payload": json.dumps({"cmd": "ProfilePlugin", "peer_id": member_id})
                                        }, 
                                        "color": "primary"
                                    }
                                ]
                            ]
                        }
                    else:
                        message = f"&#128544; {username} вышла из беседы.\n&#10071; Возникла ошибка при исключении." if sex == 1 else f"&#128544; {username} вышел из беседы.\n&#10071; Возникла ошибка при исключении."
                        keyboard = {
                            "inline": True,
                            "buttons": [
                                [
                                    {"action": {"type": "text", "label": f"{icon} Профиль", "payload": json.dumps({"cmd": "ProfilePlugin", "peer_id": member_id})}, "color": "primary"},
                                    {"action": {"type": "text", "label": "&#128094; Кик", "payload": json.dumps({"cmd": "KickPlugin", "peer_id": member_id})}, "color": "primary"},
                                    {"action": {"type": "text", "label": "&#128545; Бан", "payload": json.dumps({"cmd": "BanPlugin", "peer_id": member_id})}, "color": "primary"}
                                ]
                            ]
                        }
                else:
                    sex = await get_user_sex(member_id, evnt.msg)                    
                    message = f"&#128546; {username} вышла из беседы." if sex == 1 else f"&#128546; {username} вышел из беседы."
                    keyboard = {
                        "inline": True,
                        "buttons": [
                            [
                                {"action": {"type": "text", "label": f"{icon} Профиль", "payload": json.dumps({"cmd": "ProfilePlugin", "peer_id": member_id})}, "color": "primary"},
                                {"action": {"type": "text", "label": "&#128094; Кик", "payload": json.dumps({"cmd": "KickPlugin", "peer_id": member_id})}, "color": "primary"},
                                {"action": {"type": "text", "label": "&#128545; Бан", "payload": json.dumps({"cmd": "BanPlugin", "peer_id": member_id})}, "color": "primary"}
                            ]
                        ]
                    }
           
                keyboard = json.dumps(keyboard)
                await evnt.msg.answer(message, keyboard=keyboard)
                
        return False # False Не останавливает дальнейшую обработку событий.

