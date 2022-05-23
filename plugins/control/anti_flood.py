# -*- coding: utf-8 -*-

import time, json

from utils import plural_form

from handler.base_plugin import BasePlugin

class AntiFloodPlugin(BasePlugin):
    def __init__(self):
        """ Forbids users to send messages to bot more often than delay `delay`."""
        super().__init__()
        self.order = (-85, 85)

        self.users = {}
        self.delay_min = 3
        self.delay_max = 13
        
        self.whitelist_plugins = [
            "StoragePlugin", "ChatMetaPlugin", "UserMetaPlugin", "ControlPlugin", "StatisticsPlugin",
            "BotInvitePlugin", "MemberInvitePlugin", "AutoKickPlugin",
            "BanPlugin", "MutePlugin", "SyncPlugin",
            "NoQueuePlugin","AntiFloodPlugin", "DebugPlugin"
        ]
        self.delay_min_plugins = [
            "ContentDuelsPlugin", "UsernamePlugin", "HelpPlugin", "ProfilePlugin"
        ]

    async def global_before_message(self, msg, plugin):
        if not msg.is_chat:
            return True

        if msg.meta["is_supporter"]:
            return True
                
        if plugin.name in self.whitelist_plugins:
            return True
    
        settings = msg.meta["data_chat"].getraw("_settings_")
        if settings.get('nodelay', False):
            return True
        
        current_time = time.time()
        
        delay = self.delay_min if plugin.name in self.delay_min_plugins else self.delay_max
        
        if msg.meta.get("data_user"):
            last_message = msg.meta["data_user"].getraw("last_message", 0)

            if current_time - last_message <= delay:
                t = int(last_message-current_time+delay)                
                
                if t == 0: return True
                                
                keyboard = json.dumps({
                    'inline': True,
                    'buttons': [
                        [
                            {
                                'action': {
                                    'type': 'open_link',
                                    'label': '&#127850; Снять лимиты — Extra',
                                    'link': 'https://vk.com/@hypixelbot-extra'
                                }
                            }
                        ]
                    ]
                })
                
                message = "&#8987; Попробуй через {}.".format(
                    plural_form(int(t), ['секунду', 'секунды', 'секунд'])
                )
                
                await msg.answer(message, keyboard=keyboard)
                
                return False

            msg.meta["data_user"]["last_message"] = current_time
        else:
            if len(self.users) > 5000:
                self.users.clear()

            if current_time - self.users.get(msg.user_id, 0) <= delay:
                return False

            self.users[msg.user_id] = current_time
