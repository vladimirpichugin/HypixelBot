# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

import traceback, time, datetime, json

from handler.base_plugin import CommandPlugin

from utils import EventType, traverse, parse_user_id, get_username, get_user_sex, get_role, getDatesDiff, fmt_time


class MutePlugin(CommandPlugin):
    def __init__(self, *commands, prefixes=None, strict=False, required_role=None, ):
        self.description = ["Мут"]
        self.order = (-93, 93)
        
        self.free_commands = ("анмут", "unmute", "размут", )
        self.list_commands = ("муты", "мутлист", "мут лист", "mutes", "mutelist", "mute list", "muteslist", "mutes list", )
        
        super().__init__(*(*commands, *self.free_commands, *self.list_commands), prefixes=prefixes, strict=strict, required_role=required_role)
    
        
    async def global_before_message_checks(self, msg):
        if not msg.is_chat or not msg.from_id:
            return
        
        clients = msg.meta["data_chat"].getraw("_clients_")
        
        if not clients:
            clients = msg.meta["data_chat"]["_clients_"] = {}
            
        for client_id, client_obj in clients.items():
            if "mute" in client_obj and client_obj["mute"]:
                if "timestamp" in client_obj["mute"] and client_obj["mute"]["timestamp"]:
                    if time.time() >= client_obj["mute"]["timestamp"]+client_obj["mute"]["expires"]:
                        del client_obj["mute"]
                        
                        target_username = await get_username(msg, client_id) 
                        await msg.answer(f"&#129324; {target_username} снова может общаться, мут истёк.", disable_mentions=0)                       
                    else:
                        if msg.from_id == int(client_id) and not msg.action:
                            target_username = await get_username(msg, client_id)
                            
                            remove_chat_user = await self.api.messages.removeChatUser(chat_id=msg.chat_id, member_id=client_id)
                            if remove_chat_user:
                                await msg.answer(f"&#129324; Пользователь {target_username} исключён за несоблюдение срока мута.", disable_mentions=0)
                            else:
                                del client_obj["mute"]
                                await msg.answer(f"&#129324; {target_username} снова может общаться, мут отменен.", disable_mentions=0)                                
        
                    msg.meta["data_meta"].changed = True
                    if msg.meta["data_chat"]:
                        msg.meta["data_chat"].changed = True

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
                
        act = "unmute" if command in self.free_commands else ("list" if command in self.list_commands else "mute")
        #if command in self.perm_commands: t = "permanent"
        
        if msg.meta["payload_obj"]:
            act = msg.meta["payload_act"]
            target = msg.meta["payload_obj"]["peer_id"] if "peer_id" in msg.meta["payload_obj"] else None
            if "time" in msg.meta["payload_obj"]:
                t = msg.meta["payload_obj"]["time"]
            if "rule" in msg.meta["payload_obj"]:
                rule = msg.meta["payload_obj"]["rule"]
        act = "mute" if act not in ('unmute', 'rules', 'list', ) else act
        
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
                    if 'mute' not in _rule.get('sanctions', []): continue
                    
                    if rules_count+1 >= 9:
                        #keyboard['buttons'][len(keyboard['buttons'])-1].append({
                        #    "action": {
                        #        "type": "text",
                        #        "label": f"»",
                        #        "payload": json.dumps({
                        #            "cmd": "MutePlugin",
                        #            "act": "rules",
                        #            "peer_id": target,
                        #            "offset": rules_count
                        #        })
                        #    },
                        #    "color": "default"
                        #})
                        break
                    
                    if len(keyboard['buttons'][len(keyboard['buttons'])-1]) >= 5:
                        keyboard['buttons'].append([])
                    
    
                    text_rules += f"\n{_rule['id']}. {_rule['name']}"                        
                    keyboard['buttons'][len(keyboard['buttons'])-1].append({
                        "action": {
                            "type": "text",
                            "label": _rule['id'],
                            "payload": json.dumps({
                                "cmd": "MutePlugin",
                                "act": "mute",
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
            i, ok, message_list = 0, False, "&#129324; Пользователи в муте:"
            for client_id, client_obj in clients.items():
                if client_obj.get("mute", None):
                    ok = True
                    
                    client_username_mention = await get_username(msg, client_id, only_first_name=False)
                    message_list += f"\n{i+1}. {client_username_mention}"
                    
                    if client_obj["mute"]["expires"] != "permanent":
                        t = datetime.datetime.fromtimestamp(client_obj["mute"]["timestamp"])
                        t += datetime.timedelta(seconds=client_obj["mute"]["expires"])
                        message_list += " — до " + t.strftime('%d.%m.%Y %H:%M:%S')
                    else:
                        message_list += " — навсегда"
                
            if ok:
                return await msg.answer(message_list)
            else:
                return await msg.answer("&#129395; Пользователи с мутом не найдены, все могут общаться свободно.")

        if not target:
            if '\n' in text:
                reason_time, comment = text.split('\n')
                target = await parse_user_id(msg, custom_text=reason_time)
            else:
                target = await parse_user_id(msg)
                
            if not target:
                return await msg.answer(f"&#129324; Укажите пользователя, которого хотите {'замутить' if act == 'mute' else 'размутить'}.")
            
            parts = text.split(" ")
            if parts:
                try:
                    rule = int(parts[0])
                except:
                    pass
                
                if not t:
                    t = ''.join(parts)

        if target <= 0:
            return await msg.answer(f"&#129324; {'Замутить' if act == 'mute' else 'Размутить'} можно только пользователя.")

        if str(target) not in clients:
            clients[str(target)] = {}

        client_obj = clients[str(target)]
        
        if "mute" in client_obj and client_obj["mute"]:
            if client_obj["mute"]["expires"] != "permanent":
                if time.time() >= client_obj["mute"]["timestamp"]+client_obj["mute"]["expires"]:
                    del client_obj["mute"]
                    msg.meta["data_meta"].changed = True
        
        admin_username = await get_username(msg, msg.from_id, only_first_name=False)

        if act == "mute":
            if "mute" in client_obj and type(client_obj["mute"]) == dict:
                target_username = await get_username(msg, target, only_first_name=False)
                #sex = await get_user_sex(target, msg)
                sex = 0
                if not sex: sex = 0 
                sex_ending = "а" if sex == 1 else ""
                
                mutened_admin_username = admin_username
                if client_obj["mute"]["admin"] != msg.from_id:
                    mutened_admin_username = await get_username(msg, client_obj["mute"]["admin"], only_first_name=False)
                
                t_ = datetime.datetime.fromtimestamp(client_obj["mute"]["timestamp"])         
                t = await getDatesDiff(datetime.datetime.now(), t_, True) 
                
                t_start = t_.strftime('%d.%m.%Y %H:%M:%S')
                
                permanent = False
                if client_obj["mute"]["expires"] == "permanent":
                    permanent = True
                else:
                    t_end = t_ + datetime.timedelta(seconds=client_obj["mute"]["expires"])
                    t_end = t_end.strftime('%d.%m.%Y %H:%M:%S')
                
                    
                keyboard = {
                    "inline": True,
                    "buttons": [
                        [
                            {
                                "action": {
                                    "type": "text",
                                    "label": "&#129324; Размутить",
                                    "payload": json.dumps({
                                        "cmd": "MutePlugin",
                                        "act": "unmute",
                                        "peer_id": target
                                    })
                                },
                                "color": "default"
                            }
                        ]
                    ]
                }
                
                msg_mute = f"&#129324; {target_username} уже в муте{sex_ending}."
    
                if 'rule' in client_obj['mute']:
                    msg_mute += f"\n• Правило: {client_obj['mute']['rule']['id']}. {client_obj['mute']['rule']['name']}"
                
                msg_mute += f"\n• {t}\n• Замутил: {mutened_admin_username}\n• Начало: {t_start}"
                
                msg_mute += f"\n• Перманентный" if permanent else f"\n• Истекает: {t_end}"
                
                if "comment" in client_obj['mute']:
                    msg_mute += f"\n• Комментарий: {client_obj['mute']['comment']}"
                
                return await msg.answer(msg_mute, keyboard=json.dumps(keyboard))
                
            if msg.from_id == target:
                return await msg.answer("&#129324; Нельзя себя замутить.")
            
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
                                        "label": "30 м",
                                        "payload": json.dumps({
                                            "cmd": "MutePlugin",
                                            "peer_id": target,
                                            "time": "30m",
                                            "rule": rule
                                        })
                                    },
                                    "color": "default"
                                },
                                {
                                    "action": {
                                        "type": "text",
                                        "label": "1 ч",
                                        "payload": json.dumps({
                                            "cmd": "MutePlugin",
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
                                        "label": "2 ч",
                                        "payload": json.dumps({
                                            "cmd": "MutePlugin",
                                            "peer_id": target,
                                            "time": "2h",
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
                                            "cmd": "MutePlugin",
                                            "peer_id": target,
                                            "time": "6h",
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
                                        "label": "12 ч",
                                        "payload": json.dumps({
                                            "cmd": "MutePlugin",
                                            "peer_id": target,
                                            "time": "12h",
                                            "rule": rule
                                        })
                                    },
                                    "color": "default"
                                },
                                {
                                    "action": {
                                        "type": "text",
                                        "label": "Сутки",
                                        "payload": json.dumps({
                                            "cmd": "MutePlugin",
                                            "peer_id": target,
                                            "time": "1d",
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
                                return await msg.answer(f"&#129324; Выберите срока мута {target_username}\n• Правило: {_rule['id']}. {_rule['name']}", keyboard=json.dumps(keyboard))
                        else:
                            keyboard['buttons'] += [[
                                {
                                    "action": {
                                        "type": "text",
                                        "label": "По правилам",
                                        "payload": json.dumps({
                                            "cmd": "MutePlugin",
                                            "act": "rules",
                                            "peer_id": target
                                        })
                                    },
                                    "color": "primary"
                                }
                            ]]               
                
                    return await msg.answer(f"&#129324; Выберите срока мута {target_username}", keyboard=json.dumps(keyboard))

                t += datetime.timedelta(seconds=1)
                if t.days > 364:
                    t = datetime.timedelta(days=365)

            puid_role = await get_role(msg, target)
            if puid_role in ["owner", "staff"]:
                if puid_role == "owner":
                    target_username = await get_username(msg, target, only_first_name=False)                    
                    return await msg.answer(f"&#129324; {target_username} имеет иммунитет.")
                    
                if not msg.meta["is_owner"]:
                    target_username = await get_username(msg, target, only_first_name=False)                    
                    return await msg.answer(f"&#129324; {target_username} имеет иммунитет, тебе следует связаться с вышестоящей властью.")

            
            if "mute_history" not in client_obj:
                client_obj["mute_history"] = []            
            
            mute_obj = {
                "admin": msg.from_id,
                "timestamp": int(time.time()),
                "expires": "permanent" if t == "permanent" else t.total_seconds()
            }
            
            if rule:
                if rules:
                    for _rule in rules['list']:
                        if rule != _rule['id']: continue
                        mute_obj["rule"] = {'id': _rule['id'], 'name': _rule['name'], 'sanctions': _rule['sanctions']}
                else:
                    return await msg.answer("&#128018; Правила беседы не установлены.")
                            
            if comment:
                mute_obj["comment"] = comment
                
            client_obj["mute"] = mute_obj
            client_obj["mute_history"].append(mute_obj)
            
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
                                "label": "&#129324; Размутить",
                                "payload": json.dumps({
                                    "cmd": "MutePlugin",
                                    "act": "unmute",
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
            
            if t == "permanent":
                _msg = f"&#129324; {target_username} получил{sex_ending} перманентный мут.\n• Замутил: {admin_username}"
            else:
                _msg = f"&#129324; {target_username} получил{sex_ending} мут.\n• {period}\n• Истечёт: {period_.strftime('%d.%m.%Y %H:%M:%S')}\n• Замутил: {admin_username}"
                
            if "rule" in mute_obj:
                _msg += f"\n• Правило: {mute_obj['rule']['id']}. {mute_obj['rule']['name']}"
                
            if "comment" in mute_obj:
                _msg += f"\n• Комментарий: {mute_obj['comment']}"
                
            await msg.answer(_msg, keyboard=json.dumps(keyboard))
        if act == 'unmute':
            target_username = await get_username(msg, target, only_first_name=False)     
            sex = await get_user_sex(target, msg)
            if not sex: sex = 0 
            sex_ending = "а" if sex == 1 else ""
                    
            if "mute" not in client_obj or client_obj["mute"] is None:
                return await msg.answer(f"&#129324; Пользователь {target_username} может способно общаться, ведь мута нет.")
        
            mutened_admin_username = admin_username
            if client_obj["mute"]["admin"] != msg.from_id:
                mutened_admin_username = await get_username(msg, client_obj["mute"]["admin"], only_first_name=False)
                
            t_ = datetime.datetime.fromtimestamp(client_obj["mute"]["timestamp"])         
            t = await getDatesDiff(datetime.datetime.now(), t_, True) 
            t_mute = t_.strftime('%d.%m.%Y %H:%M:%S')
            
            _msg = f"&#128515; {target_username} теперь может общаться."
            
            if 'rule' in client_obj['mute']:
                _msg += f"\n• Правило: {client_obj['mute']['rule']['id']}. {client_obj['mute']['rule']['name']}"
        
            _msg += f"\n• Был{sex_ending} в муте {t}\n• Выдан: {t_mute}\n• Замутил: {mutened_admin_username}\n• Размутил: {admin_username}"

            await msg.answer(_msg)
            
            client_obj["mute"] = None
            
        msg.meta["data_meta"].changed = True
