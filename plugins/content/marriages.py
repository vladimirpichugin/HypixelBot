# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

from handler.base_plugin import CommandPlugin
from utils import get_role_name, get_username, parse_user_id, getDatesDiff, get_user_sex

import datetime, time, json


class ContentMarriagesPlugin(CommandPlugin):
    __slots__ = ("description", "yes_words", )

    def __init__(self, *commands, prefixes=None, strict=False, required_role=None, ):
        self.description = ["Браки"]
        
        self.yes_words = ("да", "согл", "соглас", "согласен", "согласна", "yes", "согласиться", "подтвердить", "+", )
        
        super().__init__(*commands, prefixes=prefixes, strict=strict, required_role=required_role)
        

    async def process_message(self, msg):
        if not msg.is_chat or not msg.user_id:
            return await msg.answer("&#128573; Команду можно использовать только в беседе.")
            
        clients = msg.meta["data_chat"].getraw("_clients_")    
        if clients == None:
            msg.meta["data_chat"]["_clients_"] = []
            msg.meta["data_meta"].changed = True
            if msg.meta["data_chat"]:
                msg.meta["data_chat"].changed = True
            clients = msg.meta["data_chat"].getraw("_clients_")
            
        marriages = msg.meta["data_chat"].getraw("_marriages_")
        if marriages == None:
            msg.meta["data_chat"]["_marriages_"] = []
            msg.meta["data_meta"].changed = True
            if msg.meta["data_chat"]:
                msg.meta["data_chat"].changed = True
            marriages = msg.meta["data_chat"].getraw("_marriages_")

        target = None
        
        command, text = self.parse_message(msg)
        if msg.meta["payload_act"]:
            command = "брак"
            target = msg.meta["payload_obj"]["peer_id"] if "peer_id" in msg.meta["payload_obj"] else None
            
        if command == "брак":
            username = await get_username(msg) 
            puid_username = None
            
            if not target:
                marriages_ = []
                
                target = await parse_user_id(msg)
                
                if not target:
                    client_marriages = []
                    
                    for marriage in marriages:
                        if msg.from_id in marriage["clients"]:
                            for client_id in marriage["clients"]:
                                if msg.from_id == client_id: continue
                                client_marriages.append({'partner': client_id, 'timestamp': marriage["timestamp"]})
                                
            
                    for marriage in client_marriages:
                        created_time = datetime.datetime.fromtimestamp(marriage['timestamp'])
                        
                        if len(client_marriages) == 1:
                            sexual_partner_username = await get_username(msg, marriage['partner'], name_case='ins')
                        else:
                            sexual_partner_username = await get_username(msg, marriage['partner'])
                        
                        t = await getDatesDiff(datetime.datetime.now(), created_time)
                        marriages_.append("{} уже {}".format(sexual_partner_username, t))                                

                    if text not in self.yes_words:   
                        if marriages_:
                            if len(marriages_) > 1:
                                marriage_message = "&#128141; {} в браке:\n{}".format(
                                    username,
                                    '\n'.join(f'{marriage_num+1}. {marriage}' for marriage_num, marriage in enumerate(marriages_))
                                )
                                return await msg.answer(marriage_message)                                
                            else:
                                return await msg.answer(f"&#128141; {username} в браке с {marriages_[0]}.")
                        else:
                            return await msg.answer(f"&#128141; {username}, укажите пользователя, чтобы зарегистрировать брак.")

            if target:
                if target <= 0:
                    if not msg.meta['is_supporter']:
                        return await msg.answer(f"&#127856; {username}, брак можно зарегистрировать только с пользователем.")
    
                if target == msg.from_id:
                    return await msg.answer(f"&#128141; {username}, нельзя зарегистрировать брак с самим собой.")
                          

            if str(msg.from_id) not in clients:
                clients[str(msg.from_id)] = {}
                msg.meta["data_meta"].changed = True
                if msg.meta["data_chat"]:
                    msg.meta["data_chat"].changed = True
                
            client_obj = clients[str(msg.from_id)]
            
            if "marriage_requests" in client_obj and client_obj["marriage_requests"]:
                for marriage_request in client_obj["marriage_requests"]:
                    if target:
                        if target != marriage_request["client_id"]:
                            continue
                
                    if not marriage_request["accepted"] and marriage_request["timestamp"]+120 >= time.time():
                        if not puid_username:
                            puid_username = await get_username(msg, marriage_request["client_id"])
                            
                        marriage_request["accepted"] = True
                        marriages.append({
                            "clients": [marriage_request["client_id"], msg.from_id],
                            "timestamp": int(time.time())
                        })
                        
                        msg.meta["data_meta"].changed = True
                        if msg.meta["data_chat"]:
                            msg.meta["data_chat"].changed = True
                            
                        return await msg.answer(f"&#128141; С этого момента {puid_username} и {username} состоят в браке.", disable_mentions=0)
        
            if text in self.yes_words:
                return await msg.answer("&#128141; Нечего подтверждать!")
            
            u_already_marriage = False
            target_already_marriage_with_u = False
            target_already_marriage = False
            for marriage in marriages:
                if msg.from_id in marriage["clients"]:
                    u_already_marriage = True
                    
                for _ in marriage["clients"]:
                    if target == _:
                        target_already_marriage = True
                        if msg.from_id in marriage["clients"]:
                            target_already_marriage_with_u = True
            
            if target_already_marriage_with_u: 
                puid_username = await get_username(msg, target, name_case='ins')
                return await msg.answer(f"&#128141; Вы уже состоите в браке с {puid_username}.")
            
            # Не менять порядок
            if not msg.meta['is_supporter']:
                if u_already_marriage:         
                    return await msg.answer(f"&#128141; Вы уже состоите в браке.")
                
                if target_already_marriage:
                    puid_username = await get_username(msg, target)
                    return await msg.answer(f"&#128141; {puid_username} уже состоит в браке.")
            # Не менять порядок
            
            if str(target) not in clients:
                clients[str(target)] = {}
            
            if clients[str(target)].get("hideme", False):
                return await msg.answer("&#128141; Пользователь не найден.")
            
            if "marriage_requests" not in clients[str(target)]:
                clients[str(target)]["marriage_requests"] = []
            
            marriage_requests = clients[str(target)]["marriage_requests"]
            if marriage_requests:
                for marriage_request in marriage_requests:
                    if not marriage_request["accepted"] and marriage_request["timestamp"]+120 >= time.time():
                        if msg.from_id == marriage_request["client_id"]:
                            puid_username = await get_username(msg, target, name_case='gen')
                            return await msg.answer(f"&#128141; {username}, запрос для {puid_username} уже отправлен, ожидаем решения.") 
                        else:
                            if not msg.meta['is_supporter']:
                                other_username = await get_username(msg, marriage_request["client_id"]) # Это запрос для другого клиента.
                                return await msg.answer(f"&#128141; {username}, запрос для {other_username} уже отправлен, ожидаем решения.\nНовый запрос можно будет отправить чуть-чуть позже.")
            
            marriage_requests.append({
                "client_id": msg.from_id,
                "accepted": False,
                "timestamp": int(time.time())
            })
            
            msg.meta["data_meta"].changed = True
            if msg.meta["data_chat"]:
                msg.meta["data_chat"].changed = True
            
            keyboard = json.dumps({"inline": True, "buttons": [[
                   {"action": {"type": "text", "label": "&#128141; Согласиться", "payload": json.dumps({"cmd": self.name, "act": "invite", "peer_id": msg.from_id})}, "color": "default"}
            ]]})            
            
            sex = await get_user_sex(msg.from_id, msg)
            if not sex: sex = 0 
            sex_ending = "а" if sex == 1 else ""
            
            puid_username = await get_username(msg, target)            
            return await msg.answer(f"&#128150; {puid_username}, минуточку внимания!\n&#128141; {username} предложил{sex_ending} тебе руку и сердце.\n\nЗапрос истечёт через пару минут.", disable_mentions=0, keyboard=keyboard)
        elif command == 'развод':
            username = await get_username(msg)

            if marriages == None:
                return await msg.answer(f"&#128141; {username}, ты не состоишь в браке.")
            
            marriages_count = 0
            for marriage in marriages:
                if msg.from_id in marriage["clients"]:
                    marriages_count += 1
            
            if marriages_count == 0:
                return await msg.answer(f"&#128141; {username}, ты не состоишь в браке.")
            
            if marriages_count > 1:
                target = None
                target = await parse_user_id(msg)
                
                if not target:
                    return await msg.answer(f"&#128141; {username}, у тебя несколько браков. Укажи пользователя, с которым хочешь развестись.")
                
                client_id = None
                for marriage in marriages:
                    if msg.from_id in marriage["clients"] and target in marriage["clients"]:
                        for client_id in marriage["clients"]:
                            if msg.from_id != client_id:
                                break
                        break
                    
                if not client_id:
                    puid_username = await get_username(msg, target, name_case='ins')
                    return await msg.answer(f"&#128141; {username}, брак с {puid_username} не найден.")
            else:
                for marriage in marriages:
                    if msg.from_id in marriage["clients"]:
                        for client_id in marriage["clients"]:
                            if msg.from_id != client_id:
                                break
                        break
                        
            puid_username = await get_username(msg, client_id)
            
            created_time = datetime.datetime.fromtimestamp(marriage["timestamp"])
            t = await getDatesDiff(datetime.datetime.now(), created_time)
        
            marriages.remove(marriage)
            
            msg.meta["data_meta"].changed = True
            if msg.meta["data_chat"]:
                msg.meta["data_chat"].changed = True
            
            sex = await get_user_sex(msg.from_id, msg)
            if not sex: sex = 0 
            sex_ending = "а" if sex == 1 else ""
            
            return await msg.answer(f"&#128148; {puid_username}, сожалеем, {username} подал{sex_ending} на развод...\n\nБрак просуществовал {t}.", disable_mentions=0)
        else:
            if not marriages:
                return await msg.answer("&#128141; В беседе еще никто не заключил брак.")
            
            count = 0
            marriages_ = []
            for marriage in marriages:
                if count > 9:
                    break
                sexual_partners = []
                for client_id in marriage["clients"]:
                    sexual_partner_username = await get_username(msg, client_id)
                    sexual_partners.append(sexual_partner_username)
                
                created_time = datetime.datetime.fromtimestamp(marriage["timestamp"])
                t = await getDatesDiff(datetime.datetime.now(), created_time)
                sexual_partners = " и ".join("%s" % _ for _ in sexual_partners)
                
                marriages_.append("{}. {} уже {}".format(count+1, sexual_partners, t))
                count += 1

            message = "&#128141; Браки беседы ({}):\n{}".format(len(marriages), "\n".join("%s" % _ for _ in marriages_))                    
            await msg.answer(message)
