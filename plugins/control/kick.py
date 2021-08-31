# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

from handler.base_plugin import CommandPlugin
from utils import parse_user_id, get_role, get_username, get_random_smile

import json

class KickPlugin(CommandPlugin):
    __slots__ = ("description", )

    def __init__(self, *commands, prefixes=None, strict=False, required_role=None, ):
        self.description = ["Кик"]
        self.order = (-92, 92)
        
        super().__init__(*commands, prefixes=prefixes, strict=strict, required_role=required_role)
    
    
    async def process_message(self, msg):
        if not msg.is_chat or not msg.user_id:
            return await msg.answer("&#128573; Команду можно использовать только в беседе.")

        target = None

        command, text = self.parse_message(msg)
        if msg.meta["payload_obj"]:
            target = msg.meta["payload_obj"]["peer_id"] if "peer_id" in msg.meta["payload_obj"] else None
        
        if not target:
            target = await parse_user_id(msg)
        
        if not target:
            return await msg.answer("&#127856; Вы должны указать пользователя, которого хотите кикнуть.")
            
        if target <= 0:
            return await msg.answer(f"&#127856; Кикнуть можно только пользователя.")
        
        if msg.from_id == target:
            return await msg.answer("&#127856; Себя нельзя кикнуть.")
        
        target_role = await get_role(msg, target)
        if target_role in ["owner", "staff"]:
            if target_role == "owner":
                if not msg.meta["is_owner"]:
                    return await msg.answer("&#127856; Этот господин на порядок выше тебя во всех смыслах, даже не пытайся проделать подобное.")
                
            if not msg.meta["is_owner"]:
                return await msg.answer("&#127856; Этот господин имеет иммунитет, тебе следует связаться с вышестоящей властью.")

        remove_chat_user = await self.api.messages.removeChatUser(chat_id=msg.chat_id, member_id=target)
        
        if remove_chat_user:
            username = await get_username(msg, only_first_name=False)
            target_username = await get_username(msg, target, name_case='acc', only_first_name=False)       
            icon = await get_random_smile()
            
            keyboard = {
                "inline": True, 
                "buttons": [
                    [
                        {"action": {"type": "text", "label": f"{icon} Профиль", "payload": json.dumps({"cmd": "ProfilePlugin", "peer_id": target})}, "color": "primary"},
                        {"action": {"type": "text", "label": "&#128545; Бан", "payload": json.dumps({"cmd": "BanPlugin", "peer_id": target})}, "color": "primary"}
                    ]
                ]
            }
            
            return await msg.answer(f"&#127856; {username} исключил {target_username}.", keyboard=json.dumps(keyboard))

