# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

from handler.base_plugin import CommandPlugin
from utils import get_role_name, has_perms, get_username, parse_user_id, getDatesDiff, get_user_sex, plural_form

import datetime, json, time

class ProfilePlugin(CommandPlugin):
    __slots__ = ("description", )

    def __init__(self, *commands, prefixes=None, strict=False, required_role=None, ):
        self.description = ["Профиль участника"]
        
        super().__init__(*commands, prefixes=prefixes, strict=strict, required_role=required_role)
    
    async def process_message(self, msg):
        if not msg.is_chat or not msg.user_id:
            return await msg.answer("&#128573; Команду можно использовать только в беседе.")
        
        m = None
        if msg.meta["payload_obj"]:
            if "peer_id" in msg.meta["payload_obj"]:
                m = msg.meta["payload_obj"]["peer_id"]
        
        if not m:
            m = msg.from_id
            puid = await parse_user_id(msg)
            if puid:
                m = puid
        
        has_username = False
        can_change_username = True
        muted = False
        banned = False
        activity = ""
        duels = ""
        rewards = "Награды отсутствуют"
        message_marriage = "Не состоит в браке"
        username = None
        role = "—"
        sex = 2
        mutes = 0
        bans = 0
        
        username = await get_username(msg, m)
        role = await get_role_name(msg, m)
        #sex = await get_user_sex(m, msg)
        sex = "а" if sex == 1 else ""
        
        if "data_chat" in msg.meta:
            message_stats = ""
            if msg.meta["is_supporter"]:
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
                            _statistics.append((client_id, member))
                
                    statistics = list(_statistics)
                
                for chat_top, pack in enumerate(statistics):
                    client_id, u = pack
                    client_id = int(client_id)
                    if client_id == int(m):
                        if chat_top == 0: message_stats += "&#129351;"
                        if chat_top == 1: message_stats += "&#129352;"
                        if chat_top == 2: message_stats += "&#129353;"
                        message_stats += f"Топ #{chat_top+1} по активности.\n\n"    
                        
            
            if "chat_statistics" in msg.meta["data_chat"]:
                if "users" in msg.meta["data_chat"]["chat_statistics"]:
                    if str(m) in msg.meta["data_chat"]["chat_statistics"]["users"]:
                        m_stats = msg.meta["data_chat"]["chat_statistics"]["users"][str(m)]
                        
                        if "first_message" in m_stats and "last_message" in m_stats:
                            messages_count = m_stats["messages"]
                            messages_count = f"{messages_count:,} {['сообщение', 'сообщения', 'сообщений'][2 if (4 < messages_count % 100 < 20) else (2, 0, 1, 1, 1, 2)[min(messages_count % 10, 5)]]}"
                            
                            first_message_date = datetime.datetime.fromtimestamp(m_stats["first_message"])         
                            first_message_date = await getDatesDiff(datetime.datetime.now(), first_message_date) 
                            first_message_date = "только что" if len(first_message_date) <= 1 else f"{first_message_date} назад"
                            
                            last_message_date = datetime.datetime.fromtimestamp(m_stats["last_message"])         
                            last_message_date = await getDatesDiff(datetime.datetime.now(), last_message_date)
                            last_message_date = "только что" if len(last_message_date) <= 1 else f"{last_message_date} назад"
                            
                            activity += f"Первое появление {first_message_date}\n\nОтправил{sex} {messages_count}\nПоследнее сообщение {last_message_date}\n"     
                
            if "_clients_" in msg.meta["data_chat"]:
                if str(m) in msg.meta["data_chat"]["_clients_"]:
                    m_client = msg.meta["data_chat"]["_clients_"][str(m)]
                    
                    if m_client.get("hideme", False) and msg.from_id != m:
                        return await msg.answer("&#127856; Пользователь не найден.")
                    
                    if "mute" in m_client and type(m_client["mute"]) == dict:
                        muted = True
                        
                    if "ban" in m_client and type(m_client["ban"]) == dict:
                        banned = True
                        
                    if "mute_history" in m_client and type(m_client["mute_history"]) == list:
                        mutes = len(m_client["mute_history"])
                    
                    if "ban_history" in m_client and type(m_client["ban_history"]) == list:
                        bans = len(m_client["ban_history"])
                    
                    if "username" in m_client:
                        has_username = True
                    
                    if "can_change_username" in m_client:
                        can_change_username = m_client["can_change_username"]
                    
                    if "duels_stats" in m_client and m_client["duels_stats"]:
                        duels = f"\n\n&#128299; Выиграл{sex} " + plural_form(len(m_client["duels_stats"]), ['дуэль', 'дуэли', 'дуэлей'])
                    
                    if "rewards" in m_client and m_client["rewards"]:
                        rewards_levels = ['&#127895;', '&#129353;', '&#129352;', '&#129351;', '&#127894;', '&#127941;', '&#127942;', '&#127989;', '&#127775;', '&#128050;']
                        
                        rewards_ = []
                        
                        for r in m_client["rewards"][:5]:
                            if type(r) == str:
                                rewards_.append(f"&#127895; {r}")
                            else:
                                reward_text = r['reward']
                                reward_level = r['level']
                                reward_icon = rewards_levels[reward_level] if reward_level <= len(rewards_levels) else rewards_levels[0]
                                rewards_.append(f"{reward_icon} {reward_text}")
                    
                        rewards = "\n".join("%s" % _ for _ in rewards_[-3:])
                        if len(rewards_) > 3:
                            rewards += "\nи еще {}.".format(plural_form(len(rewards_)-3, ['награда', 'награды', 'наград']))
        
            if "_marriages_" in msg.meta["data_chat"]:
                marriages = msg.meta["data_chat"].getraw("_marriages_")
                
                marriages_ = []
                for marriage in marriages:
                    if m in marriage["clients"]:
                        for client_id in marriage["clients"]:
                            if m == client_id: continue
                            sexual_partner_username = await get_username(msg, client_id, name_case='ins')
                            
                            created_time = datetime.datetime.fromtimestamp(marriage["timestamp"])
                            t = await getDatesDiff(datetime.datetime.now(), created_time)
                            marriages_.append(f"{sexual_partner_username} уже {t}")
                            
                if marriages_:
                    if len(marriages_) > 1:
                        message_marriage = "Браки:\n{}".format("\n".join("• %s" % _ for _ in marriages_[-3:]))

                        if len(marriages_) > 3:                            
                            message_marriage += "\nи еще {}.".format(plural_form(len(marriages_)-3, ['брак', 'брака', 'браков']))
                    else:
                        message_marriage = "В браке с {}".format(marriages_[0])
        
        
        rewards = f"\n\n&#127942; Награды:\n{rewards}"                
        message = f"{'Пользователь' if m > 0 else 'Сообщество'} {username}:\n{message_stats}Роль: {role}\n{activity}\n&#128141; {message_marriage}{duels}{rewards}"
        
        plugins = {}
        for plugin in self.handler.plugins:
            if plugin.name in plugins: continue
            if hasattr(plugin, "required_role"):
                plugins[plugin.name] = plugin.required_role
        
        buttons, staff_buttons, super_staff_buttons = [], [], []
        for plugin in self.handler.plugins:
            if plugin.name == "ContentMarriagesPlugin":
                if await has_perms(msg, plugin):
                    buttons.append({"action": {"type": "text", "label": "&#128141; Брак", "payload": json.dumps({"cmd": "ContentMarriagesPlugin", "act": "invite", "peer_id": m})}, "color": "default"})
            
            if plugin.name == "ContentDuelsPlugin":
                if await has_perms(msg, plugin):
                    buttons.append({"action": {"type": "text", "label": "&#128299; Дуэль", "payload": json.dumps({"cmd": "ContentDuelsPlugin", "act": "invite", "peer_id": m})}, "color": "default"})

            if plugin.name == "MutePlugin":
                if await has_perms(msg, plugin):
                    if mutes > 1:
                        message += f"\n\nМутов: {mutes}"
                    
                    if muted:
                        muted_admin_username = await get_username(msg, m_client["mute"]["admin"], only_first_name=False)
                        
                        t_ = datetime.datetime.fromtimestamp(m_client["mute"]["timestamp"])         
                        t = await getDatesDiff(datetime.datetime.now(), t_, True) 
                        
                        t_start = t_.strftime('%d.%m.%Y %H:%M:%S')
                        t_end = t_ + datetime.timedelta(seconds=m_client["mute"]["expires"])
                        t_end = t_end.strftime('%d.%m.%Y %H:%M:%S')
                        
                        message += f"\n\nМут:\n• В муте: {t}\n• Замутил: {muted_admin_username}\n• Время мута: {t_start}\n• Истечёт: {t_end}"
                        
                    if m != msg.from_id:
                        if not muted:
                            staff_buttons.append({"action": {"type": "text", "label": "&#129324; Мут", "payload": json.dumps({"cmd": "MutePlugin", "peer_id": m})}, "color": "primary"})
                        else:
                            staff_buttons.append({"action": {"type": "text", "label": "&#129324; Анмут", "payload": json.dumps({"cmd": "MutePlugin", "act": "unmute", "peer_id": m})}, "color": "positive"})
            
            if plugin.name == "KickPlugin":
                if m != msg.from_id:
                    if await has_perms(msg, plugin):
                        staff_buttons.append({"action": {"type": "text", "label": "&#128094; Кик", "payload": json.dumps({"cmd": "KickPlugin", "peer_id": m})}, "color": "primary"})

            if plugin.name == "BanPlugin":
                if await has_perms(msg, plugin):
                    if bans > 1:
                        message += f"\n\nБанов: {bans}"
                    
                    if banned:
                        banned_admin_username = await get_username(msg, m_client["ban"]["admin"], only_first_name=False)
                        
                        t_ = datetime.datetime.fromtimestamp(m_client["ban"]["timestamp"])         
                        t = await getDatesDiff(datetime.datetime.now(), t_, True) 
                        
                        t_start = t_.strftime('%d.%m.%Y %H:%M:%S')
                        if m_client["ban"]["expires"] == "permanent":
                            t_end = "Перманентный"
                        else:
                            t_end = t_ + datetime.timedelta(seconds=m_client["ban"]["expires"])
                            t_end = t_end.strftime('%d.%m.%Y %H:%M:%S')
                        
                        message += f"\n\nБан:\n• В бане: {t}\n• Забанил: {banned_admin_username}\n• Время бана: {t_start}\n• Истечёт: {t_end}"
                        
                    if m != msg.from_id:
                        if not banned:
                            staff_buttons.append({"action": {"type": "text", "label": "&#128545; Бан", "payload": json.dumps({"cmd": "BanPlugin", "peer_id": m})}, "color": "primary"})
                        else:
                            staff_buttons.append({"action": {"type": "text", "label": "&#128545; Анбан", "payload": json.dumps({"cmd": "BanPlugin", "act": "unban", "peer_id": m})}, "color": "positive"})

            
            if plugin.name == "ControlPlugin":
                if await has_perms(msg, plugin):
                    if has_username:
                        super_staff_buttons.append({"action": {"type": "text", "label": "Удалить ник", "payload": json.dumps({"cmd": "ControlPlugin", "act": "username.delete", "peer_id": m})}, "color": "primary"})
                    
                    if m != msg.from_id:
                        if can_change_username:
                            super_staff_buttons.append({"action": {"type": "text", "label": "-ник", "payload": json.dumps({"cmd": "ControlPlugin", "act": "username.interact", "peer_id": m})}, "color": "negative"})
                        else:
                            super_staff_buttons.append({"action": {"type": "text", "label": "+ник", "payload": json.dumps({"cmd": "ControlPlugin", "act": "username.interact", "peer_id": m})}, "color": "positive"})
        
        if not m or m == msg.from_id:
            if msg.meta["is_supporter"]:
                message += "\n\n&#129392; Подписчица PLUS." if sex else" \n\n&#129392; Подписчик PLUS." 

        columns = []
        
        if buttons: columns.append(buttons)
        if staff_buttons:
            staff_buttons.reverse()
            columns.append(staff_buttons)
        if super_staff_buttons: columns.append(super_staff_buttons)
        

        columns.append([{"action": {"type": "open_link", "link": "https://vk.com/@hypebot-plus", "label": "&#129392; Подписка PLUS"}}])
        
        if columns:
            keyboard = json.dumps({"inline": True, "buttons": columns})
            return await msg.answer(message, keyboard=keyboard)
        else:
            return await msg.answer(message)
