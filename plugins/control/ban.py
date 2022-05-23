# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

import traceback, time, datetime, json

from handler.base_plugin import CommandPlugin

from utils import EventType, traverse, parse_user_id, get_username, get_user_sex, get_role, getDatesDiff, fmt_time


class BanPlugin(CommandPlugin):
    def __init__(self, *commands, prefixes=None, strict=False, required_role=None, ):
        self.description = ["Бан"]
        self.order = (-97, 97)
        
        self.free_commands = ("анбан", "unban", "разбан", )
        self.perm_commands = ("pban", "пермбан", "пбан", )
        self.list_commands = ("баны", "банлист", "бан лист", "bans", "banlist", "ban list", "banslist", "bans list", )
        
        super().__init__(*(*commands, *self.free_commands, *self.perm_commands, *self.list_commands), prefixes=prefixes, strict=strict, required_role=required_role)
        
    async def check_event(self, evnt):
        return evnt.type == EventType.ChatChange
    
    async def process_event(self, evnt):
        if evnt.action_type in ("chat_invite_user", "chat_invite_user_by_link", ):
            member_id = evnt.msg.action.get("member_id", None)
            clients = evnt.msg.meta["data_chat"].getraw("_clients_")
            
            if not clients:
                clients = evnt.msg.meta["data_chat"]["_clients_"] = {}
            
            for client_id, client_obj in clients.items():
                if type(client_id) != str or type(client_id) != int:
                    continue
                
                client_id = int(client_id)
                if client_id != member_id:
                    continue
                
                if "ban" in client_obj and client_obj["ban"]:
                    if "timestamp" in client_obj["ban"] and client_obj["ban"]["timestamp"]:
                        target_username = await get_username(evnt.msg, client_id) 
                        if client_obj["ban"]["expires"] != "permanent":
                            if time.time() >= client_obj["ban"]["timestamp"]+client_obj["ban"]["expires"]:
                                del client_obj["ban"]
                                evnt.msg.meta["data_meta"].changed = True
                                if evnt.msg.meta["data_chat"]:
                                    evnt.msg.meta["data_chat"].changed = True
                                await evnt.msg.answer(f"&#128545; {target_username} снова может общаться, бан истёк.", disable_mentions=0)
                                continue
                            
                            
                        t_ = datetime.datetime.fromtimestamp(client_obj["ban"]["timestamp"])         
                        t_start = t_.strftime('%d.%m.%Y %H:%M:%S')
                        
                        permanent = False
                        if client_obj["ban"]["expires"] == "permanent":
                            permanent = True
                        else:
                            t_end = t_ + datetime.timedelta(seconds=client_obj["ban"]["expires"])
                            t_end = t_end.strftime('%d.%m.%Y %H:%M:%S')
                        

                        keyboard = {
                            "inline": True,
                            "buttons": [
                                [
                                    {
                                        "action": {
                                            "type": "text",
                                            "label": "&#128545; Анбан",
                                            "payload": json.dumps({
                                                "cmd": "BanPlugin",
                                                "act": "unban",
                                                "peer_id": member_id
                                            })
                                        },
                                        "color": "positive"
                                    }
                                ]
                            ]
                        }
                        
                        msg_ban = f"&#128545; Приглашён заблокированный пользователь {target_username}."
                        
                        banned_admin_username = await get_username(evnt.msg, client_obj["ban"]["admin"], only_first_name=False)
                        
                        if permanent:
                            msg_ban += f"\n• Забанил: {banned_admin_username}"
                        else:
                            msg_ban += f"\n• {t_start}\n• Истечёт: {t_end}\n• Забанил: {banned_admin_username}"                        
                        

                        if 'rule' in client_obj['ban']:
                            msg_ban += f"\n• Правило: {client_obj['ban']['rule']['id']}. {client_obj['ban']['rule']['name']}"

                    
                        await evnt.msg.answer(msg_ban, keyboard=json.dumps(keyboard))
                        await self.api.messages.removeChatUser(chat_id=evnt.msg.chat_id, member_id=client_id)
                        return True

        return False # Не останавливает дальнейшую обработку.

    async def process_message(self, msg):
        if not msg.is_chat or not msg.from_id:
            return await msg.answer("&#128573; Команду можно использовать только в беседе.")
        
        t, target, rule, comment = None, None, None, None
        command, text = self.parse_message(msg)
        
        settings = msg.meta["data_chat"].getraw("_settings_")
        
        rules = None
        if settings.get("chat_rules", None):
            if settings.get("chat_rules").get("list"):
                rules = settings['chat_rules']
        
        act = "unban" if command in self.free_commands else ("list" if command in self.list_commands else "ban")
        if command in self.perm_commands: t = "permanent"
        
        if msg.meta["payload_obj"]:
            act = msg.meta["payload_act"]
            target = msg.meta["payload_obj"]["peer_id"] if "peer_id" in msg.meta["payload_obj"] else None
            if "time" in msg.meta["payload_obj"]:
                t = msg.meta["payload_obj"]["time"]
            if "rule" in msg.meta["payload_obj"]:
                rule = msg.meta["payload_obj"]["rule"]
        act = "ban" if act not in ('unban', 'rules', 'list', ) else act
        
        if act == "rules":
            if rules:
                keyboard = {
                    'inline': True,
                    'buttons': [
                        []
                    ]
                }
                
                text_rules = '&#128018; Правила беседы:'
                rules_count = 0
                for _rule in rules.get('list', []):
                    if 'ban' not in _rule.get('sanctions', []): continue
                    
                    if rules_count+1 >= 9:
                        """
                        keyboard['buttons'][len(keyboard['buttons'])-1].append({
                            "action": {
                                "type": "text",
                                "label": f"»",
                                "payload": json.dumps({
                                    "cmd": "BanPlugin",
                                    "act": "rules",
                                    "peer_id": target,
                                    "offset": rules_count
                                })
                            },
                            "color": "default"
                        })
                        """
                        break
                    
                    if len(keyboard['buttons'][len(keyboard['buttons'])-1]) >= 5:
                        keyboard['buttons'].append([])
                    
    
                    text_rules += f"\n{_rule['id']}. {_rule['name']}"                        
                    keyboard['buttons'][len(keyboard['buttons'])-1].append({
                        "action": {
                            "type": "text",
                            "label": _rule['id'],
                            "payload": json.dumps({
                                "cmd": "BanPlugin",
                                "act": "ban",
                                "peer_id": target,
                                "rule": _rule['id']
                            })
                        },
                        "color": "default"
                    })
                    rules_count += 1
                    
                
                rules_link = rules.get('link', None)
                if rules_link:
                    keyboard['buttons'].append([
                        {
                            'action': {
                                'type': 'open_link',
                                'label': '&#128018; Правила беседы',
                                'link': rules_link
                            }
                        }
                    ])
                
                return await msg.answer(text_rules, keyboard=json.dumps(keyboard))
            else:
                return await msg.answer(f"&#128018; Правила беседы не установлены.")
        
        clients = msg.meta["data_chat"].getraw("_clients_")
        if not clients:
            clients = msg.meta["data_chat"]["_clients_"] = {}
        
        if act == "list":
            i, ok, message_list = 0, False, "&#128545; Заблокированные пользователи:"
            for client_id, client_obj in clients.items():
                if client_obj.get("ban", None):
                    ok = True
                    
                    client_username_mention = await get_username(msg, client_id, only_first_name=False)
                    message_list += f"\n{i+1}. {client_username_mention}"
                    
                    if client_obj["ban"]["expires"] != "permanent":
                        t = datetime.datetime.fromtimestamp(client_obj["ban"]["timestamp"])
                        t += datetime.timedelta(seconds=client_obj["ban"]["expires"])
                        message_list += " — до " + t.strftime('%d.%m.%Y %H:%M:%S')
                    else:
                        message_list += " — навсегда"
                        
            if ok:
                return await msg.answer(message_list)
            else:
                return await msg.answer("&#129395; Пользователи с баном не найдены, все могут общаться свободно.")
            
        if not target:
            if '\n' in text:
                reason_time, comment = text.split('\n')
                target = await parse_user_id(msg, custom_text=reason_time)
            else:
                target = await parse_user_id(msg)
                
            if not target:
                return await msg.answer(f"&#128545; Укажите пользователя, которого хотите {'забанить' if act == 'ban' else 'разбанить'}.")
            
            parts = text.split(" ")
            if parts:
                try:
                    rule = int(parts[0])
                except:
                    pass

                if not t:
                    t = ''.join(parts)

        if target <= 0:
            return await msg.answer(f"&#128545; {'Забанить' if act == 'ban' else 'Разбанить'} можно только пользователя.")

        if str(target) not in clients:
            clients[str(target)] = {}
                
        client_obj = clients[str(target)]
        
        if "ban" in client_obj and client_obj["ban"]:
            if client_obj["ban"]["expires"] != "permanent":
                if time.time() >= client_obj["ban"]["timestamp"]+client_obj["ban"]["expires"]:
                    del client_obj["ban"]
                    msg.meta["data_meta"].changed = True
        
        admin_username = await get_username(msg, msg.from_id, only_first_name=False)

        if act == "ban":
            if "ban" in client_obj and type(client_obj["ban"]) == dict:
                target_username = await get_username(msg, target, only_first_name=False)
                sex = await get_user_sex(target, msg)
                if not sex: sex = 0 
                sex_ending = "а" if sex == 1 else ""
                
                banned_admin_username = admin_username
                if client_obj["ban"]["admin"] != msg.from_id:
                    banned_admin_username = await get_username(msg, client_obj["ban"]["admin"], only_first_name=False)
                
                t_ = datetime.datetime.fromtimestamp(client_obj["ban"]["timestamp"])         
                t = await getDatesDiff(datetime.datetime.now(), t_, True) 
                
                t_start = t_.strftime('%d.%m.%Y %H:%M:%S')
                
                permanent = False
                if client_obj["ban"]["expires"] == "permanent":
                    permanent = True
                else:
                    t_end = t_ + datetime.timedelta(seconds=client_obj["ban"]["expires"])
                    t_end = t_end.strftime('%d.%m.%Y %H:%M:%S')
                
                    
                keyboard = {
                    "inline": True,
                    "buttons": [
                        [
                            {
                                "action": {
                                    "type": "text",
                                    "label": "&#128545; Разбанить",
                                    "payload": json.dumps({
                                        "cmd": "BanPlugin",
                                        "act": "unban",
                                        "peer_id": target
                                    })
                                },
                                "color": "default"
                            }
                        ]
                    ]
                }
                
                msg_ban = f"&#128545; {target_username} уже забанен{sex_ending}."
    
                if 'rule' in client_obj['ban']:
                    msg_ban += f"\n• Правило: {client_obj['ban']['rule']['id']}. {client_obj['ban']['rule']['name']}"
                
                msg_ban += f"\n• {t}\n• Забанил: {banned_admin_username}\n• Начало: {t_start}"
                
                msg_ban += f"\n• Перманентный" if permanent else f"\n• Истекает: {t_end}"
                
                if "comment" in client_obj['ban']:
                    msg_ban += f"\n• Комментарий: {client_obj['ban']['comment']}"
                
                return await msg.answer(msg_ban, keyboard=json.dumps(keyboard))
                
            if msg.from_id == target:
                return await msg.answer("&#128545; Нельзя себя забанить.")
            
            if t != "permanent":
                t = await fmt_time(t)
                if not t or type(t) != datetime.timedelta:
                    
                    target_username = await get_username(msg, target, name_case='gen', only_first_name=False)
                    
                    keyboard = {
                        'inline': True,
                        'buttons': [
                            [
                                {
                                    "action": {
                                        "type": "text",
                                        "label": "1 ч",
                                        "payload": json.dumps({
                                            "cmd": "BanPlugin",
                                            "peer_id": target,
                                            "time": "1h",
                                            "rule": rule
                                        })
                                    },
                                    "color": "default"
                                },
                                {
                                    "action": {
                                        "type": "text",
                                        "label": "6 ч",
                                        "payload": json.dumps({
                                            "cmd": "BanPlugin",
                                            "peer_id": target,
                                            "time": "6h",
                                            "rule": rule
                                        })
                                    },
                                    "color": "default"
                                },
                                {
                                    "action": {
                                        "type": "text",
                                        "label": "12 ч",
                                        "payload": json.dumps({
                                            "cmd": "BanPlugin",
                                            "peer_id": target,
                                            "time": "12h",
                                            "rule": rule
                                        })
                                    },
                                    "color": "default"
                                }
                            ],
                            [
                                {
                                    "action": {
                                        "type": "text",
                                        "label": "Сутки",
                                        "payload": json.dumps({
                                            "cmd": "BanPlugin",
                                            "peer_id": target,
                                            "time": "1d",
                                            "rule": rule
                                        })
                                    },
                                    "color": "default"
                                },
                                {
                                    "action": {
                                        "type": "text",
                                        "label": "Перманентный",
                                        "payload": json.dumps({
                                            "cmd": "BanPlugin",
                                            "peer_id": target,
                                            "time": "permanent",
                                            "rule": rule
                                        })
                                    },
                                    "color": "default"
                                }
                            ]
                        ]
                    }
                    
                    if rules:
                        if rule:
                            for _rule in rules['list']:
                                if rule != _rule['id']: continue
                                return await msg.answer(f"&#128545; Выберите срока бана {target_username}\n• Правило: {_rule['id']}. {_rule['name']}", keyboard=json.dumps(keyboard))
                        else:
                            keyboard['buttons'] += [[
                                {
                                    "action": {
                                        "type": "text",
                                        "label": "По правилам",
                                        "payload": json.dumps({
                                            "cmd": "BanPlugin",
                                            "act": "rules",
                                            "peer_id": target
                                        })
                                    },
                                    "color": "primary"
                                }
                            ]]               
                
                    return await msg.answer(f"&#128545; Выберите срока бана {target_username}", keyboard=json.dumps(keyboard))

                t += datetime.timedelta(seconds=1)
                if t.days > 364:
                    t = datetime.timedelta(days=365)

            puid_role = await get_role(msg, target)
            if puid_role in ["owner", "staff"]:
                if puid_role == "owner":
                    target_username = await get_username(msg, target, only_first_name=False)                    
                    return await msg.answer(f"&#128545; {target_username} имеет иммунитет.")
                    
                if not msg.meta["is_owner"]:
                    target_username = await get_username(msg, target, only_first_name=False)                    
                    return await msg.answer(f"&#128545; {target_username} имеет иммунитет, тебе следует связаться с вышестоящей властью.")

            
            if "ban_history" not in client_obj:
                client_obj["ban_history"] = []            
            
            ban_obj = {
                "admin": msg.from_id,
                "timestamp": int(time.time()),
                "expires": "permanent" if t == "permanent" else t.total_seconds()
            }
            
            if rule:
                if rules:
                    for _rule in rules['list']:
                        if rule != _rule['id']: continue
                        ban_obj["rule"] = {'id': _rule['id'], 'name': _rule['name'], 'sanctions': _rule['sanctions']}
                else:
                    return await msg.answer("&#128018; Правила беседы не установлены.")
                                       
            if comment:
                ban_obj["comment"] = comment
                
            client_obj["ban"] = ban_obj
            client_obj["ban_history"].append(ban_obj)
            
            if t != "permanent":
                period_ = datetime.datetime.now() + t
                period = await getDatesDiff(period_, datetime.datetime.now(), True)
            
        
            keyboard = {
                "inline": True,
                "buttons": [
                    [
                        {
                            "action": {
                                "type": "text",
                                "label": "&#128545; Разбанить",
                                "payload": json.dumps({
                                    "cmd": "BanPlugin",
                                    "act": "unban",
                                    "peer_id": target
                                })
                            },
                            "color": "default"
                        }
                    ]
                ]
            }
            
            target_username = await get_username(msg, target, only_first_name=False)
            sex = await get_user_sex(target, msg)
            if not sex: sex = 0 
            sex_ending = "а" if sex == 1 else ""
            

            remove_chat_user = await self.api.messages.removeChatUser(chat_id=msg.chat_id, member_id=target)
            
            """
            if remove_chat_user:
                error_code = remove_chat_user.get('error_code', None)
                if error_code == 917:
                    keyboard = {
                        "inline": True,
                        "buttons": [
                            [
                                {
                                    "action": {
                                        "type": "open_link",
                                        "label": "&#127829; Инструкция: Права администратора",
                                        "link": "https://vk.com/@hypixelbot-setup-admin"
                                    }
                                }
                            ]
                        ]
                    }
                    
                    return await msg.answer(f"&#128545; Не могу исключить {target_username} из беседы.\n.Бот не назначен администратором беседы.", keyboard=json.dumps(keyboard))
                elif error_code in [935, 15]:
                    pass
            """
            
            if t == "permanent":
                _msg = f"&#128545; {target_username} получил{sex_ending} перманентный бан.\n• Забанил: {admin_username}"
            else:
                _msg = f"&#128545; {target_username} получил{sex_ending} временный бан.\n• {period}\n• Истечёт: {period_.strftime('%d.%m.%Y %H:%M:%S')}\n• Забанил: {admin_username}"
                
            if "rule" in ban_obj:
                _msg += f"\n• Правило: {ban_obj['rule']['id']}. {ban_obj['rule']['name']}"
                
            if "comment" in ban_obj:
                _msg += f"\n• Комментарий: {ban_obj['comment']}"
                
            await msg.answer(_msg, keyboard=json.dumps(keyboard))
        if act == 'unban':
            target_username = await get_username(msg, target, only_first_name=False)     
            sex = await get_user_sex(target, msg)
            if not sex: sex = 0 
            sex_ending = "а" if sex == 1 else ""
                    
            if "ban" not in client_obj or client_obj["ban"] == None:
                return await msg.answer(f"&#128545; {target_username} не забанен{sex_ending}, он может свободно общаться.")
        
            banned_admin_username = admin_username
            if client_obj["ban"]["admin"] != msg.from_id:
                banned_admin_username = await get_username(msg, client_obj["ban"]["admin"], only_first_name=False)
                
            t_ = datetime.datetime.fromtimestamp(client_obj["ban"]["timestamp"])         
            t = await getDatesDiff(datetime.datetime.now(), t_, True) 
            t_ban = t_.strftime('%d.%m.%Y %H:%M:%S')
            
            _msg = f"&#128515; {target_username} разбанен{sex_ending}."
            
            if 'rule' in client_obj['ban']:
                _msg += f"\n• Правило: {client_obj['ban']['rule']['id']}. {client_obj['ban']['rule']['name']}"
        
            _msg += f"\n• Был{sex_ending} в бане {t}\n• Выдан: {t_ban}\n• Забанил: {banned_admin_username}\n• Разбанил: {admin_username}"

            await msg.answer(_msg)
            
            client_obj["ban"] = None
            
        msg.meta["data_meta"].changed = True
