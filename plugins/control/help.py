# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

import json
from handler.base_plugin import CommandPlugin


class HelpPlugin(CommandPlugin):
    def __init__(self, *commands, prefixes=None, strict=False, required_role=None, ):
        self.description = ["Помощь"]
        super().__init__(*commands, prefixes=prefixes, strict=strict, required_role=required_role)
    
    async def process_message(self, msg):
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
                ],
                [
                    {
                        "action": {
                            "type": "open_link",
                            "label": "&#10084; Команды Hypixel",
                            "link": "https://vk.com/@hypebot-hypixel"
                        }
                    }
                ],
                [
                    {
                        "action": {
                            "type": "open_link",
                            "label": "&#128081; Пригласить бота в свою беседу",
                            "link": "https://vk.com/@hypebot-setup"
                        }
                    }
                ]
            ]
        }
        
        keyboard = json.dumps(keyboard)
        return await msg.answer("Помощь", keyboard=keyboard)
