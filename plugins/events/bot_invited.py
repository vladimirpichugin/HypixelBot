# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

from handler.base_plugin import CommandPlugin
from utils import EventType, get_username, get_random_smile

import json, random

class BotInvitePlugin(CommandPlugin):
    def __init__(self):
        self.order = (-95, 95)
        super().__init__()
        
    async def check_event(self, evnt):
        return evnt.type == EventType.ChatChange
    
    async def process_event(self, evnt):
        if evnt.action_type in ("chat_invite_user", ):
            member_id = evnt.msg.action.get("member_id", None)
            if member_id and abs(member_id) == self.api.get_current_id():
                message = "Чат-менеджер HypeBot."
                
                keyboard = {
                    "inline": True,
                    "buttons": [
                        [
                            {
                                "action": {
                                    "type": "open_link",
                                    "label": "&#127856; Команды бота",
                                    "link": "https://vk.com/@hypebot-commands"
                                }
                            }
                        ]
                    ]
                }
                
                await evnt.msg.answer(message, keyboard=json.dumps(keyboard))
        
        return False # Не останавливает дальнейшую обработку.
