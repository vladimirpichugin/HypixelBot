# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

from handler.base_plugin import BasePlugin


class UserMetaPlugin(BasePlugin):
    __slots__ = ("users",)

    def __init__(self):
        """Adds `user_info` to messages and events's meta with user's data
        if available (https://vk.com/dev/users.get). You can refresh data
        with coroutine stored in `meta['user_info_refresh']`."""
        super().__init__()

        self.order = (-91, 91)

        self.users = {}

    async def update_user_info(self, user_id, refresh=False):
        if user_id <= 0:
            return False

        current_data = self.users.get(user_id)

        if not refresh and current_data: 
            return current_data
            
        new_data = await self.api.users.get(user_ids=user_id,
            fields="sex,screen_name,first_name_nom,first_name_gen,first_name_dat,first_name_acc,first_name_ins,first_name_abl,last_name_nom,last_name_gen,last_name_dat,last_name_acc,last_name_ins,last_name_abl") or {}
          
        if not new_data:
            return None
        
        if len(self.users) > 50000:
            from random import random
            self.users = dict((k, v) for k, v in self.users.items() if random() > 0.25)

        self.users[user_id] = new_data[0]

        return self.users[user_id]

    def create_refresh(self, user_id):
        async def func():
            return await self.update_user_info(user_id, True)

        return func

    async def global_before_message_checks(self, msg):
        info = await self.update_user_info(msg.user_id)

        if info:
            msg.meta["user_info_refresh"] = self.create_refresh(msg.user_id)
            msg.meta["user_info"] = {"raw": info}

    async def global_before_event_checks(self, evnt):
        if evnt.msg.is_chat:
            return

        info = await self.update_user_info(evnt.user_id)

        if info:
            evnt.meta["user_info_refresh"] = self.create_refresh(evnt.user_id)
            evnt.meta["user_info"] = {"raw": info}
