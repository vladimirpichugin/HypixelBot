# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

from handler.base_plugin import CommandPlugin
from utils import get_role_name, get_username, parse_user_id, get_user_sex, parse_username_mention, is_supporter

import datetime, time, random, json

class ContentDuelsPlugin(CommandPlugin):
    __slots__ = ("find_commands", "shot_commands", "top_commands", "yes_words", "no_words", "messages", "description", )

    def __init__(self, *commands, prefixes=None, strict=False, required_role=None, ):
        self.description = ["Дуэли"]
        
        self.find_commands = ("кто дуэль", "дуэль кто", "ктодуэль", "дуэлькто", )
        self.shot_commands = ("выстрел", )
        self.top_commands = ("дуэли", "дуэли топ", "дуэлитоп", "топ дуэлей", "топдуэлей", )
        
        self.yes_words = ("да", "yes", "согласиться", "подтвердить", "+", )
        self.no_words = ("нет", "no", "отказаться", "отказ", "отклонить", "отмена", "отменить", "cancel", "-", )
        
        self.messages = ['&#128299; {0} стреляет в {1}']
        
        super().__init__(*(*self.find_commands, *self.shot_commands, *self.top_commands, *commands), prefixes=prefixes, strict=strict, required_role=required_role)
    
    
    async def process_message(self, msg):
        if not msg.is_chat or not msg.user_id:
            return await msg.answer("&#128573; Команду можно использовать только в беседе.")
        
        target, cancel_duel = None, False
        command, text = self.parse_message(msg)
        if msg.meta["payload_act"]:
            if msg.meta["payload_act"] == "invite":
                command = "дуэль"
                text = command
                
                if "peer_id" in msg.meta["payload_obj"]:
                    target = msg.meta["payload_obj"]["peer_id"]
                    
                if "duelists" in msg.meta["payload_obj"]:
                    duelists = msg.meta["payload_obj"]["duelists"]
                    if type(duelists) == list and len(duelists) == 2:
                        target = duelists[1] if msg.from_id == duelists[0] else duelists[0]
            
            if msg.meta["payload_act"] == "cancel":
                command = "отмена"
                text = command
                cancel_duel = True
                
                if "duelists" in msg.meta["payload_obj"]:
                    duelists = msg.meta["payload_obj"]["duelists"]
                    if type(duelists) == list and len(duelists) == 2:
                        target = duelists[1] if msg.from_id == duelists[0] else duelists[0]
            
            if msg.meta["payload_act"] == "shot":
                command = "выстрел"
                text = command
                
            if msg.meta["payload_act"] == "find":
                command = "кто дуэль"
                text = command
        
        clients = msg.meta["data_chat"].getraw("_clients_") 
        duels = msg.meta["data_chat"].getraw("_duels_")

        if duels == None:
            msg.meta["data_chat"]["_duels_"] = []
            msg.meta["data_chat"].changed = True
            duels = msg.meta["data_chat"].getraw("_duels_")
        
        for duel in duels:
            if duel["state"] == "wait":
                if time.time() >= duel["timestamp"]+240:
                    duels.remove(duel)
            if duel["state"] == "game":
                if duel["last_shot_timestamp"]:
                    if time.time() >= duel["last_shot_timestamp"]+240:
                        winner = duel["clients"][1] if duel["clients"][0] == duel["current"] else duel["clients"][0]
                        clients[str(winner)]["duels_stats"].append({"opponent": duel["current"], "time": int(time.time())})
                        duels.remove(duel)
                else:
                    if time.time() >= duel["timestamp"]+240:
                        duels.remove(duel)
        
        msg.meta["data_chat"].changed = True
        
        if command in self.find_commands: # Предложить любому дуэль
            username_only = await get_username(msg, parsed_mention=False)
            username = await parse_username_mention(msg.from_id, username_only)

            keyboard = json.dumps({"inline": True, "buttons": [[
                   {"action": {"type": "text", "label": f"&#128299; Дуэль {username_only}", "payload": json.dumps({"cmd": self.name, "act": "invite", "peer_id": msg.from_id})}, "color": "default"}
            ]]})  
            
            return await msg.answer(f"&#128299; {username} предлагает любому желающему поучаствовать в дуэли.", disable_mentions=1, keyboard=keyboard)
        elif command in self.top_commands: # Топ дуэлей
            statistics = sorted(
                msg.meta["data_chat"]["_clients_"].items(),
                key=lambda item: len(item[1]["duels_stats"]) if "duels_stats" in item[1] else 0,
                reverse=True
            )

            message_stats = ""
            clients = []
            for i, pack in enumerate(statistics[:10]):
                client_id, client = pack
                if "duels_stats" in client and len(client["duels_stats"]):
                    client_id = int(client_id)
                    clients.append(client_id)
                    username = await get_username(msg, client_id)
                    
                    wins = len(client["duels_stats"])
                    losses = 0
                    
                    for _ in statistics:
                        peer, obj = _
                        if "duels_stats" in obj and obj["duels_stats"]:
                            for duel in obj["duels_stats"]:
                                if duel["opponent"] == client_id:
                                    losses += 1

                    message_stats += f"{i+1}. {username} — {wins:,}:{losses:,}\n"

            message_stats = message_stats = f"&#128299; Статистика дуэлей:\n{message_stats}" if message_stats else  "&#128299; В беседе еще никто не совершал дуэль."
            
            keyboard = json.dumps({"inline": True, "buttons": [[
                   {"action": {"type": "text", "label": f"&#128299; Кто дуэль?", "payload": json.dumps({"cmd": self.name, "act": "find"})}, "color": "default"}
            ]]})  
            
            await msg.answer(message_stats, keyboard=keyboard)
        elif command in self.shot_commands: # Выстрел
            have_wait, have_game = False, False
            for duel in duels:
                if msg.from_id in duel["clients"]:
                    if duel["state"] == "game":
                        have_game = True
                        break
            
            if have_game:
                opponent = duel["clients"][1] if msg.from_id == duel["clients"][0] else duel["clients"][0]

                if duel["current"] == opponent:
                    target_username = await get_username(msg, opponent)
                    keyboard = json.dumps({"inline": True, "buttons": [[
                           {"action": {"type": "text", "label": "&#128299; Выстрел", "payload": json.dumps({"cmd": self.name, "act": "shot"})}, "color": "default"}
                    ]]})
                    return await msg.answer(f"&#128299; Сейчас {target_username} должен произвести выстрел, ждём.", keyboard=keyboard, disable_mentions=0)
                
                min_chance = 0.6 if msg.meta["is_supporter"] else 0.5
                
                if random.uniform(0, 1) > min_chance:
                    kill = True
                else:
                    kill = False
                
                #if opponent in (349154007, 522223932, ): kill = False
                #if msg.from_id in (349154007, 522223932, ): kill = True
                
                if kill:
                    duels.remove(duel)
                    
                    clients[str(msg.from_id)]["duels_stats"].append({"opponent": opponent, "time": int(time.time())})
                    
                    msg.meta["data_chat"].changed = True
        
                    username = await get_username(msg)                    
                    target_username = await get_username(msg, opponent, name_case='acc')
                    target_sex = 0
                    target_sex = await get_user_sex(msg.from_id, msg)
                    target_sex = "а" if target_sex == 1 else ""
                    
                    keyboard = json.dumps({"inline": True, "buttons": [[
                           {"action": {"type": "text", "label": "&#128299; Повторить дуэль", "payload": json.dumps({"cmd": self.name, "act": "invite", "duelists": duel["clients"]})}, "color": "default"}
                    ]]})  
                    return await msg.answer(f"&#128299;&#129327; Попадание!\n{username} застрелил{target_sex} {target_username}", disable_mentions=0, keyboard=keyboard)
                else:
                    username = await get_username(msg)
                    target_username = await get_username(msg, opponent, name_case='acc')
                    message = random.choice(self.messages).format(username, target_username)
                    duel["last_shot_timestamp"] = int(time.time())
                    duel["round"] += 1
                    if duel["round"] > 4:
                        duels.remove(duel)
                        keyboard = json.dumps({"inline": True, "buttons": [[
                               {"action": {"type": "text", "label": "&#128299; Повторить дуэль", "payload": json.dumps({"cmd": self.name, "act": "invite", "duelists": duel["clients"]})}, "color": "default"}
                        ]]})  
                        return await msg.answer(f"&#128552; Ничья.\n\n{message}", disable_mentions=0, keyboard=keyboard)
                    duel["current"] = opponent
                    msg.meta["data_chat"].changed = True
                        
                    keyboard = json.dumps({"inline": True, "buttons": [[
                           {"action": {"type": "text", "label": "&#128299; Выстрел", "payload": json.dumps({"cmd": self.name, "act": "shot"})}, "color": "default"}
                    ]]})
                    return await msg.answer(message, disable_mentions=0, keyboard=keyboard)
        else: # Управление дуэлью
            username = await get_username(msg)  

            have_wait, have_game = False, False
            for duel in duels:
                if msg.from_id in duel["clients"]:    
                    if duel["state"] == "wait":
                        have_wait = True
                    if duel["state"] == "game":
                        have_game = True
            
            if not target:
                cancel_duel = False
                if have_game:
                    if text in self.no_words:
                        cancel_duel = True
                else:
                    target = await parse_user_id(msg)
                    if not target or target <= 0:
                        if text not in (*self.yes_words, *self.no_words):   
                            return await msg.answer(f"&#127856; {username}, укажите пользователя, чтобы предложить дуэль.")
                        else:
                            if text in self.no_words:
                                cancel_duel = True
                        
            if target and target <= 0:
                return await msg.answer(f"&#127856; {username}, предложить дуэль можно только пользователю.")
            
            sex = await get_user_sex(msg.from_id, msg)
            if not sex: sex = 0 
            sex = "а" if sex == 1 else ""
            
            if have_game:
                for duel in duels:
                    if duel["state"] == "game":
                        if msg.from_id in duel["clients"]:
                            opponent = duel["clients"][1] if msg.from_id == duel["clients"][0] else duel["clients"][0]
                            opponent_username = await get_username(msg, opponent)
                            
                            if cancel_duel:
                                duels.remove(duel)
                                
                                clients[str(opponent)]["duels_stats"].append({"opponent": msg.from_id, "time": int(time.time())})
                                
                                msg.meta["data_chat"].changed = True
                                
                                return await msg.answer(f"&#128299; {username} отменил дуэль, {opponent_username} победил.", disable_mentions=0)
                            
                            keyboard = json.dumps({"inline": True, "buttons": [[
                                   {"action": {"type": "text", "label": "&#128299; Выстрел", "payload": json.dumps({"cmd": self.name, "act": "shot"})}, "color": "default"},
                                   {"action": {"type": "text", "label": "&#10060; Отменить дуэль", "payload": json.dumps({"cmd": self.name, "act": "cancel"})}, "color": "negative"}
                            ]]})
                            
                            if duel["current"] == msg.from_id:
                                return await msg.answer(F"&#128299; {username}, ты уже принял дуэль, стреляй.", keyboard=keyboard)
                            return await msg.answer(f"&#128299; Сейчас {opponent_username} должен произвести выстрел, ждём.", keyboard=keyboard)
            
            if have_wait:
                for duel in duels:
                    if duel["state"] == "wait":
                        if msg.from_id in duel["clients"]:
                            opponent = duel["clients"][1] if msg.from_id == duel["clients"][0] else duel["clients"][0]
                            
                            if target and target != opponent:
                                continue
                            
                            if cancel_duel:
                                duels.remove(duel)
                                opponent_username = await get_username(msg, opponent)
                                return await msg.answer(f"&#128299; {opponent_username}, очень жаль, но {username} отменил{sex} дуэль.", disable_mentions=0)
                            
                            if duel["clients"][0] == msg.from_id:
                                keyboard = json.dumps({"inline": True, "buttons": [[
                                       {"action": {"type": "text", "label": "&#10060; Отменить дуэль", "payload": json.dumps({"cmd": self.name, "act": "cancel", "duelists": [msg.from_id, opponent]})}, "color": "negative"}
                                ]]})
                                opponent_username = await get_username(msg, opponent, name_case='dat')
                                return await msg.answer(f"&#128299; {username}, запрос уже отправлен {opponent_username}", keyboard=keyboard)

                            duel["state"] = "game"
                            duel["current"] = opponent
                            opponent_username = await get_username(msg, opponent)                            
                            
                            keyboard = json.dumps({"inline": True, "buttons": [[
                                   {"action": {"type": "text", "label": "&#128299; Выстрел", "payload": json.dumps({"cmd": self.name, "act": "shot"})}, "color": "default"}
                            ]]})
                            
                            return await msg.answer(f"&#128299; {opponent_username}, {username} принял{sex} дуэль.\n&#127993; {opponent_username} сделает первый выстрел.", disable_mentions=0, keyboard=keyboard)

            if target == msg.from_id:
                return await msg.answer(f"&#127856; {username}, нельзя вызывать самого себя на дуэль.")
            if text in (*self.yes_words, *self.no_words):
                return await msg.answer(f"&#128299; {username}, нет запросов на дуэль.")
            
            if str(msg.from_id) not in clients:
                clients[str(msg.from_id)] = {}
            
            if "duels_stats" not in clients[str(msg.from_id)]:
                clients[str(msg.from_id)]["duels_stats"] = []
            
            if str(target) not in clients:
                clients[str(target)] = {}
                
            if clients[str(target)].get("hideme", False):
                return await msg.answer("&#128299; Пользователь не найден.")
                    
            if "duels_stats" not in clients[str(target)]:
                clients[str(target)]["duels_stats"] = []
            
            duels.append({
                "state": "wait",
                "clients": [msg.from_id, target],
                "round": 0,
                "current": None,
                "last_shot_timestamp": None,
                "timestamp": int(time.time())
            })
            
            msg.meta["data_chat"].changed = True

            target_username = await get_username(msg, target)            
            message = f"&#128299; {target_username}, минуточку внимания!\n&#127993; {username} вызвал{sex} тебя на дуэль.\n\nЗапрос истечёт через пару минут."
            
            keyboard = json.dumps({"inline": True, "buttons": [[
                   {"action": {"type": "text", "label": "&#128299; Принять", "payload": json.dumps({"cmd": self.name, "act": "invite", "duelists": [msg.from_id, target]})}, "color": "positive"},
                   {"action": {"type": "text", "label": "&#128020; Отказаться", "payload": json.dumps({"cmd": self.name, "act": "cancel", "duelists": [msg.from_id, target]})}, "color": "negative"}
            ]]})            
            
            return await msg.answer(message, disable_mentions=0, keyboard=keyboard)
      