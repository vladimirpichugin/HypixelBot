# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

from handler.base_plugin import CommandPlugin
from utils import EventType, get_username, get_random_smile, get_user_sex

import json, random

class MemberInvitePlugin(CommandPlugin):
    def __init__(self):
        self.order = (-94, 94)
        super().__init__()
        
    async def check_event(self, evnt):
        return evnt.type == EventType.ChatChange
    
    async def process_event(self, evnt):
        if evnt.action_type in ("chat_invite_user_by_link", "chat_invite_user", ):
            member_id = evnt.msg.action.get("member_id", None)
            if member_id and abs(member_id) != self.api.get_current_id():
                
                settings = evnt.msg.meta["data_chat"].getraw("_settings_")
                auto_kick = True if (settings.get("auto_kick", False)) else False
                chat_rules_link = settings.get('chat_rules', {}).get('link', None) if settings.get('chat_rules', None) else None
                
                if auto_kick:
                    if evnt.action_type == 'chat_invite_user' and member_id == evnt.msg.from_id:
                        result = await self.api.messages.removeChatUser(
                            member_id=member_id,
                            chat_id=evnt.msg.chat_id
                        )
        
                        username = await get_username(evnt.msg, member_id, only_first_name=False)
                        sex = await get_user_sex(member_id, evnt.msg)                        

                        icon = await get_random_smile()
                                                
                        if result == 1:
                            message = f"{username} вернулась в беседу и была исключена." if sex == 1 else f"{username} вернулся в беседу и был исключён."
                            keyboard = {
                                "inline": True, 
                                "buttons": [
                                    [
                                        {"action": {"type": "text", "label": f"{icon} Профиль", "payload": json.dumps({"cmd": "ProfilePlugin", "peer_id": member_id})}, "color": "primary"},
                                        {"action": {"type": "text", "label": "&#128545; Бан", "payload": json.dumps({"cmd": "BanPlugin", "peer_id": member_id})}, "color": "primary"}
                                    ]
                                ]
                            }
                            await evnt.msg.answer(message, keyboard=json.dumps(keyboard))
                            return False                     
                        else:
                            message = f"{username} вернулась в беседу.\n\nВозникла ошибка при исключении." if sex == 1 else f"{username} вернулся в беседу.\n\nВозникла ошибка при исключении."
                            keyboard = {
                                "inline": True, 
                                "buttons": [
                                    [
                                        {"action": {"type": "text", "label": f"{icon} Профиль", "payload": json.dumps({"cmd": "ProfilePlugin", "peer_id": member_id})}, "color": "primary"},
                                        {"action": {"type": "text", "label": "&#128094; Кик", "payload": json.dumps({"cmd": "BanPlugin", "peer_id": member_id})}, "color": "primary"}
                                    ]
                                ]
                            }
                            await evnt.msg.answer(message, keyboard=json.dumps(keyboard))

                
                muted, banned = False, False
                if "data_chat" in evnt.msg.meta and "_clients_" in evnt.msg.meta["data_chat"]:
                    if str(member_id) in evnt.msg.meta["data_chat"]["_clients_"]:                
                        m_client = evnt.msg.meta["data_chat"]["_clients_"][str(member_id)]
                        muted = True if "mute" in m_client and type(m_client["mute"]) == dict else False
                        banned = True if "ban" in m_client and type(m_client["ban"]) == dict else False
                
                
                buttons = []
                
                if chat_rules_link:
                    buttons.append([
                        {
                            "action": {
                                "type": "open_link",
                                "label": "&#128018; Правила беседы",
                                "link": chat_rules_link
                            }
                        }                            
                    ])
                    
                
                
                buttons.append([
                    {
                        "action": {
                            "type": "open_link",
                            "label": "&#127856; Команды бота",
                            "link": "https://vk.com/@hypebot-commands"
                        }
                    }
                ])
                
                buttons.append([
                    {
                        "action": {
                            "type": "open_link",
                            "label": "&#128081; Пригласить бота в свою беседу",
                            "link": "https://vk.com/@hypebot-setup"
                        }
                    }
                ])
                
                icon = await get_random_smile()
                
                buttons.append([
                    {
                        "action": {
                            "type": "text",
                            "label": f"{icon} Профиль",
                            "payload": json.dumps({
                                "cmd": "ProfilePlugin",
                                "peer_id": member_id
                            })
                        },
                        "color": "primary"
                    }
                ])
                
                if muted:
                    buttons.append([
                        {
                            "action": {
                                "type": "text",
                                "label": "&#129324; Анмут",
                                "payload": json.dumps({
                                    "cmd": "MutePlugin",
                                    "act": "unmute",
                                    "peer_id": member_id
                                })
                            },
                            "color": "positive"
                        }
                    ])         
                
                if banned:
                    buttons.append([
                        {
                            "action": {
                                "type": "text",
                                "label": "&#128545; Разбанить",
                                "payload": json.dumps({
                                    "cmd": "BanPlugin",
                                    "act": "unban",
                                    "peer_id": member_id
                                })
                            },
                            "color": "positive"
                        }
                    ])                
                        
                keyboard = {
                    "inline": True,
                    "buttons": buttons
                }
                    
                keyboard = json.dumps(keyboard)
                username = await get_username(evnt.msg, member_id, only_first_name=False)
                await evnt.msg.answer(f"Добро пожаловать, {username}.", keyboard=keyboard)
            
        return False # Не останавливает дальнейшую обработку.
