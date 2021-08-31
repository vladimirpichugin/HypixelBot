# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

import re, emoji, json

from handler.base_plugin import CommandPlugin
from utils import parse_user_id, parse_username_mention, get_username, is_blacklisted, get_random_smile


class UsernamePlugin(CommandPlugin):
    def __init__(self, *commands, prefixes=None, strict=False, required_role=None, ):
        self.description = ["Выбор ника участника"]

        super().__init__(*commands, prefixes=prefixes, strict=strict, required_role=required_role)        
        
        self.regexp_username = r'^[а-яёa-z0-9]{2,20}$' 
        self.regexp_username_plus = r'^[а-яёa-z0-9 ]{1,20}$' 
        self.regexp_emoji = r'(\:[\w\d\-]+\:)'
        
        self.username_regexp_blacklist = [
            r'^((.+)?(hype|(x|х)(a|а|e)(й|i|и|e)(p|п|5))(b|б|б)(o|о|0)(t|т)?(.+))$', # hypebot
            r'^((.+)?((t|т)+)((r|р|5|p)+)((i|и|1|l|e|е)+)((p|п|р|5)+)?((p|п|5|р)+)((s|с|c)+)((o|о|0)+)((l|л|1|i)+)?(.+))$' # trippsol
        ]      
        self.username_rules = "Требования к нику:\n• А-я, A-z, 0-9;\n• Максимум 20 символов;\n• Минимум 2 символа;\n• Пробел запрещён;\n• Емоджи запрещены.\n\n&#127850; Емоджи и пробел доступны с подписки PLUS."
        self.username_rules_plus = "Требования к нику:\n• А-я, A-z, 0-9;\n• Максимум 20 символов;\n• Минимум 1 символ;\n• Пробел разрешён;\n• Емоджи разрешены."
        
    async def global_before_message_checks(self, msg):
        if not msg.is_chat or not msg.from_id:
            return

        clients = msg.meta["data_chat"].getraw("_clients_")
        if not clients:
            clients = msg.meta["data_chat"]["_clients_"] = {}        
        
        msg.meta["username"] = "Пользователь" if msg.from_id > 0 else "Сообщество"
        msg.meta["parsed_username"] = await parse_username_mention(msg.from_id, msg.meta["username"])
        msg.meta["has_username"] = False
        msg.meta["can_change_username"] = True
        msg.meta["hideme"] = False
        
        if await is_blacklisted(msg, True) >= 2:
            msg.meta["can_change_username"] = False
        else:
            for client_id, client_obj in clients.items():
                if client_id != str(msg.from_id): continue
                if type(client_obj) != dict: continue
                
                msg.meta["hideme"] = client_obj.get("hideme", False)
                
                msg.meta["can_change_username"] = client_obj.get("can_change_username", True)
                if "username" in client_obj and client_obj["username"]:
                    msg.meta["username"] = emoji.emojize(client_obj["username"], use_aliases=True)
                    msg.meta["has_username"] = True
                    
            msg.meta["parsed_username"] = await parse_username_mention(msg.from_id, msg.meta["username"])


    async def process_message(self, msg):
        if not msg.is_chat or not msg.user_id:
            return await msg.answer("&#128573; Команду можно использовать только в беседе.")
        
        command, text = self.parse_message(msg, full=True)
        icon = await get_random_smile()
        
        if not msg.meta["can_change_username"]:
            nick_owner = await parse_username_mention(msg.from_id, ("пользователя" if msg.from_id > 0 else "сообщества"))
            return await msg.answer(f"{icon} Ник {nick_owner}: {msg.meta['username']}\n\n&#10060; Наложены ограничения на изменение ника." if msg.meta["has_username"] else f"{icon} Ник не установлен.\n\n&#10060; Наложены ограничения на установку ника.")
        
        username = None
        if text:
            emoji_found = False
            for word in text:
                try:
                    emoji.UNICODE_EMOJI_ENGLISH[word]
                    emoji_found = True
                    break
                except:
                    pass        
                
            if emoji_found and not msg.meta["is_supporter"]: 
                current_username = await get_username(msg)
                keyboard = json.dumps({
                    'inline': True,
                    'buttons': [
                        [
                            {
                                'action': {
                                    'type': 'open_link',
                                    'label': '&#127850; Подписка PLUS',
                                    'link': 'https://vk.com/@hypebot-plus'
                                }
                            }
                        ]
                    ]
                })
                return await msg.answer(f"&#128545; {current_username}, такой ник установить нельзя.\nНик содержит емоджи.\n\n&#127850; Для использования емоджи требуется подписка PLUS.", keyboard=keyboard)
            
            spaces = len(re.findall(r' ', text))
            emojis = len(re.findall(self.regexp_emoji, emoji.demojize(text)))
            cleared_text = re.sub(r'\s+', '', re.sub(self.regexp_emoji, '', emoji.demojize(text)))
            symbols = int(len(cleared_text)+emojis+spaces)
            
            if symbols > 20 or symbols < 1 or (symbols < 2 and not msg.meta['is_supporter']):
                current_username = await get_username(msg)
                
                if msg.meta['is_supporter']:
                    keyboard = None
                else:
                    keyboard = json.dumps({
                        'inline': True,
                        'buttons': [
                            [
                                {
                                    'action': {
                                        'type': 'open_link',
                                        'label': '&#127850; Подписка PLUS',
                                        'link': 'https://vk.com/@hypebot-plus'
                                    }
                                }
                            ]
                        ]
                    })                
                
                return await msg.answer(f"&#128545; {current_username}, такой ник установить нельзя.\nМаксимум 20 символов, минимум {'1 символ' if msg.meta['is_supporter'] else '2 символа'}. В нике {symbols}.\n{self.username_rules_plus if msg.meta['is_supporter'] else self.username_rules}", keyboard=keyboard)
            
            regexp_bad_symbols = re.compile(self.regexp_username_plus, flags=re.IGNORECASE) if msg.meta["is_supporter"] else re.compile(self.regexp_username, flags=re.IGNORECASE)
            
            if emojis > 0 and len(cleared_text) == 0:
                cleared_text = 'username'
            
            if not re.search(regexp_bad_symbols, cleared_text):
                current_username = await get_username(msg)
                
                if msg.meta['is_supporter']:
                    return await msg.answer(f"&#128545; {current_username}, такой ник установить нельзя.\n{self.username_rules_plus}")
                else:
                    keyboard = json.dumps({
                        'inline': True,
                        'buttons': [
                            [
                                {
                                    'action': {
                                        'type': 'open_link',
                                        'label': '&#127850; Подписка PLUS',
                                        'link': 'https://vk.com/@hypebot-plus'
                                    }
                                }
                            ]
                        ]
                    })
                    return await msg.answer(f"&#128545; {current_username}, такой ник установить нельзя.\n{self.username_rules}", keyboard=keyboard)
                
            
            if msg.from_id not in [349154007, 522223932]:
                for _ in self.username_regexp_blacklist:
                    if not re.search(re.compile(_, flags=re.IGNORECASE), text):
                        pass
                    else:
                        current_username = await get_username(msg)
                        keyboard = json.dumps({
                            'inline': True,
                            'buttons': [
                                [
                                    {
                                        'action': {
                                            'type': 'open_link',
                                            'label': '&#8505; Условия использования',
                                            'link': 'https://vk.com/@hypebot-terms'
                                        }
                                    }
                                ]
                            ]
                        })
                        return await msg.answer(f"&#128545; {current_username}, такой ник установить нельзя.\nВыбранный ник нарушает условия использования HypeBot. Если попытки продолжатся, мы запретим вам изменять ник.", keyboard=keyboard)
                    
            username_raw = text
            username = emoji.demojize(username_raw)

        if username:
            clients = msg.meta["data_chat"].getraw("_clients_")
            
            for client_id, client_obj in clients.items():
                if client_id == str(msg.from_id): continue
                if "username" not in client_obj or not client_obj["username"]: continue
                
                if client_obj["username"].lower() == username.lower():
                    username_owner = await parse_username_mention(int(client_id), ("пользователю" if int(client_id) > 0 else "сообществу"))
                    return await msg.answer(f"{icon} Ник «{username_raw}» принадлежит {username_owner}.")
            
            if str(msg.from_id) not in clients:
                clients[str(msg.from_id)] = {}
                
            clients[str(msg.from_id)]["username"] = username
            
            msg.meta["data_meta"].changed = True
            msg.meta["data_chat"].changed = True
                
            return await msg.answer(f"&#128522; Ник «{username_raw}» установлен.")
        
        if msg.meta["has_username"]:
            if msg.meta["payload_obj"]:
                if "act" in msg.meta["payload_obj"]:
                    if msg.meta["payload_obj"]["act"] == "delete":
                        if "peer_id" in msg.meta["payload_obj"]:
                            if msg.from_id == msg.meta["payload_obj"]["peer_id"]:
                                clients = msg.meta["data_chat"].getraw("_clients_")
                    
                                if str(msg.from_id) not in clients:
                                    clients[str(msg.from_id)] = {}
                                
                                clients[str(msg.from_id)]["username"] = None
                                
                                msg.meta["data_meta"].changed = True
                                msg.meta["data_chat"].changed = True
                                return await msg.answer(f"{icon} Ник удалён.")

            
            keyboard = json.dumps({
                'inline': True,
                'buttons': [
                    [
                        {
                            "action": {
                                "type": "text",
                                "label": "Удалить ник",
                                "payload": json.dumps({"cmd": "UsernamePlugin", "act": "delete", "peer_id": msg.from_id})
                            },
                            "color": "negative"
                        }
                    ]
                ]
            })
            return await msg.answer(f"{icon} Выбранный ник: {msg.meta['username']}", keyboard=keyboard)
        else:
            return await msg.answer(f"{icon} Ник не установлен.")
            