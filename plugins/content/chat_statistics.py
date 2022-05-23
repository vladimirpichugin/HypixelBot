# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

from handler.base_plugin import CommandPlugin
from utils import get_username, plural_form, getDatesDiff

import time, datetime, json


class StatisticsPlugin(CommandPlugin):
    __slots__ = ("description", )

    def __init__(self, *commands, prefixes=None, strict=False, required_role=None, ):
        """Stores amount of messages for users in chats. Requires: StoragePlugin."""
        self.description = ["Статистика беседы"]
        
        super().__init__(*commands, prefixes=prefixes, strict=strict, required_role=required_role)


    async def global_before_message_checks(self, msg):
        if not msg.is_chat or not msg.user_id:
            return
        
        data = msg.meta["data_chat"]

        if not data:
            return

        if "chat_statistics" not in data:
            data["chat_statistics"] = {"users": {}}

        statistics = data["chat_statistics"]

        if str(msg.from_id) not in statistics["users"]:
            statistics["users"][str(msg.from_id)] = {"messages": 0, "symbols": 0, "first_message": int(time.time()), "last_message": int(time.time())}

        user = statistics["users"][str(msg.from_id)]

        user["messages"] += 1
        user["symbols"] += len(msg.full_text)
        user["last_message"] = int(time.time())

    async def process_message(self, msg):
        if not msg.is_chat or not msg.user_id:
            return await msg.answer("&#128573; Команду можно использовать только в беседе.")
        
        
        minumum, maximum = 10, 25
        
        count = minumum
        
        args = msg.text.split(" ")
        if args[-1].isdigit():
            if not msg.meta['is_supporter']:
                keyboard = json.dumps({
                    'inline': True,
                    'buttons': [
                        [
                            {
                                'action': {
                                    'type': 'open_link',
                                    'label': '&#127850; Подписка Extra',
                                    'link': 'https://vk.com/@hypixelbot-extra'
                                }
                            }
                        ]
                    ]
                })
                return await msg.answer("&#129392; Активируйте Подписку Extra, чтобы смотреть статистику беседы.", keyboard=keyboard)
            count = maximum if int(args[-1]) > maximum else int(args[-1])
        
        statistics = sorted(
            msg.meta["data_chat"]["chat_statistics"]["users"].items(),
            key=lambda item: (-item[1]["messages"], -item[1]["last_message"])
        )

        statistics = list(filter(lambda x: (int(x[0]) > 0), statistics))

        if "chat_info" in msg.meta["data_chat"]:
            _members = []
            for _member in msg.meta["data_chat"]["chat_info"].get("items", []):
                _members.append(int(_member["member_id"]))
    
            _statistics = []
            for client_id, member in statistics:
                if int(client_id) in _members:
                    if member.get('hide', False): continue
                    _statistics.append((client_id, member))
        
            statistics = list(_statistics)

        message_stats = "&#128064; Статистика беседы:\n"
        
        clients = []
        ok = False
        
        for i, pack in enumerate(statistics[:count]):
            client_id, u = pack
            client_id = int(client_id)
            clients.append(client_id)
            username = await get_username(msg, client_id)
            
            last_message_t_diff = await getDatesDiff(datetime.datetime.now(), datetime.datetime.fromtimestamp(u['last_message']), True)
            last_message_t_diff = "только что" if len(last_message_t_diff) <= 1 else f"{last_message_t_diff} назад"
                        
            message_stats += f"{i+1}. {username} — {plural_form(u['messages'], ('сообщение', 'сообщения', 'сообщений'), fmt=True)}, {last_message_t_diff}\n"              
            ok = True

        if ok:
            if msg.from_id not in clients:
                for i, pack in enumerate(statistics):
                    client_id, u = pack
                    client_id = int(client_id)
                    if msg.from_id != client_id: continue
                    
                    username = await get_username(msg, client_id)
                    
                    last_message_t_diff = await getDatesDiff(datetime.datetime.now(), datetime.datetime.fromtimestamp(u['last_message']), True)
                    last_message_t_diff = "только что" if len(last_message_t_diff) <= 1 else f"{last_message_t_diff} назад"
                    
                    message_stats += f"...\n{i+1}. {username} — {plural_form(u['messages'], ('сообщение', 'сообщения', 'сообщений'), fmt=True)}, {last_message_t_diff}\n"     
        else:
            message_stats = "&#128064; Недостаточно сообщений для формирования статистики беседы, продолжайте общаться."
        
        await msg.answer(message_stats, disable_mentions=1)
