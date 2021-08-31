# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

import traceback, time, json

from handler.base_plugin import CommandPlugin

from utils import traverse, parse_user_id, get_username, is_supporter


class ControlPlugin(CommandPlugin):
    def __init__(self, *commands, prefixes=None, strict=False, required_role=None, ):
        self.description = ["Настройки"]
        
        self.commands_roles_list = ('стафф', 'персонал', 'админы', 'staff', 'admins', )
        self.commands_roles_add = ('повысить', 'назначить', 'promote', )
        self.commands_roles_rem = ('понизить', 'снять', 'demote', )
        self.command_rewards_add = ('награда', 'наградить', )
        
        super().__init__(*(*commands, *self.commands_roles_list, *self.commands_roles_add, *self.commands_roles_rem, *self.command_rewards_add), prefixes=prefixes, strict=strict, required_role=required_role)
        
        self.rewards_levels = ['&#127895;', '&#129353;', '&#129352;', '&#129351;', '&#127894;', '&#127941;', '&#127942;', '&#127989;', '&#127775;', '&#128050;']        
    
    async def global_before_message_checks(self, msg):
        if not msg.is_chat or not msg.from_id:
            return
        
        roles = {
            "owner": {"clients": [], "info": {"name": "Владелец", "priority": 100}},
            "staff": {"clients": [], "info": {"name": "Администратор", "priority": 80}},
            "jrstaff": {"clients": [], "info": {"name": "Помощник", "priority": 60}},
            "trusted": {"clients": [], "info": {"name": "Доверенный", "priority": 20}},
            "any": {"info": {"name": "Участник", "priority": 1}}
        }
        
        staff = msg.meta["data_chat"].getraw("_staff_")

        if staff is None or ("info" not in staff["owner"]):
            staff = msg.meta["data_chat"]["_staff_"] = \
                roles
        
        if "any" not in staff.keys():
            staff["any"] = roles["any"]
        
        for role, clients in staff.items():
            if role == "any": continue
            msg.meta[f"is_{role}"] = True if msg.from_id in clients["clients"] else False
        msg.meta["is_staff_or_owner"] = msg.meta["is_staff"] or msg.meta["is_owner"]
        
        msg.meta["get_editable_staff_lists"] = \
            (lambda: msg.meta["data_chat"]["_staff_"])
        
        msg.meta["is_supporter"] = await is_supporter(msg.from_id, msg.meta["data_user_plus"])
        
        settings = msg.meta["data_chat"].getraw("_settings_")
        if settings is None:
            msg.meta["data_chat"]["_settings_"] = {}
    
    async def process_message(self, msg):
        if not msg.is_chat or not msg.from_id:
            return await msg.answer("&#128573; Команду можно использовать только в беседе.")
        
        command, text = self.parse_message(msg)
        _, full_text = self.parse_message(msg, full=True)
        
        if msg.meta["payload_act"]:
            if msg.meta["payload_act"]:
                act = msg.meta["payload_act"].split(".")
                
                command = act[0]
                text = command
                
                try:
                    text += " " + act[1]
                except:
                    pass
                
                if "peer_id" in msg.meta["payload_obj"]:
                    text += " " + str(msg.meta["payload_obj"]["peer_id"])
                
                msg.text = text

        args = text.replace('\n', ' ').split(' ')
        full_text_args = full_text.replace('\n', ' ').split(' ')
        
        sections = {
            'roles': {
                '_name_': 'Управление ролями',
                '_words_': ('роль', 'роли', 'roles', 'role', ),
                'list': ('список', 'показать', '?', 'list', 'лист', ),
                'add': ('добавить', '+', 'add', 'выдать', 'установить', ),
                'rem': ('удалить', 'убрать', '-', 'del', 'rem', 'delete', 'remove', 'снять', 'отобрать', ),
                'name': ('имя', 'name', )
            },
            'permissions': {
                '_name_': 'Управление правами ролей',
                '_words_': ('доступ', 'право', 'права', 'perm', 'perms', 'permissions', ),
                'list': ('список', 'показать', '?', 'list', 'лист', ),
                'add': ('установить', 'выдать', 'добавить', '+', 'add', ),
            },
            'username': {
                '_name_': 'Управление никами',
                '_words_': ('ник', 'nick', 'username', ),
                'interact': ('изменять', 'изменение', 'взаимодействие', 'change', 'interact', ),
                'rem': ('удалить', 'убрать', '-', 'del', 'rem', 'delete', 'remove', 'снять', 'отобрать', )
            },
            'rewards': {
                '_name_': 'Управление наградами',
                '_words_': ('награда', 'награды', 'rewards', 'reward', ),
                'add': ('наградить', '+', 'add', 'выдать', 'добавить', 'установить', ),
                'rem': ('снять', 'убрать', '-', 'del', 'rem', 'delete', 'remove', 'удалить', 'отобрать', ),
                'list': ('показать', 'список', '?', 'list', 'лист', ),
            },
            'auto_kick': {
                '_name_': 'Авто-кик покинувших беседу',
                '_words_': ('автокик', 'авто-кик', 'autokick', 'auto-kick', ),
                'add': ('вкл', 'on', 'true', 'включить', '+',  ),
                'rem': ('откл', 'off', 'false', 'отключить', '-',  ),
            },
            'chat_rules': {
                '_name_': 'Правила беседы',
                '_words_': ('правила', 'rules', ),
                'list': ('показать', '?', ),
                'add': ('добавить', '+', 'add', 'set', 'установить', ),
                'rem': ('удалить', 'убрать', '-', 'del', 'rem', 'delete', ),
                'link': ('ссылка', 'link', )
            },
            'api_integration': {
                '_name_': 'API-Интеграция',
                '_words_': ('интеграция', 'integration', 'api', 'апи', ),
                'add': ('вкл', 'on', 'true', 'включить', '+',  ),
                'rem': ('откл', 'off', 'false', 'отключить', '-',  ),
            },
        }

        if command in self.commands_roles_add:
            if not args[0]: return await msg.answer("Недостаточно аргументов: [роль] [пользователь]")
            args = ['roles', 'add', args[0]]
        if command in self.commands_roles_rem:
            if args[0]:
                args = ['roles', 'del', args[0]]
            else:
                args = ['roles', 'del']
        if command in self.commands_roles_list:
            args = ['roles', 'list']
        #if command in self.command_rewards_add:
        #    if not args[0]: return await msg.answer("Недостаточно аргументов: [роль] [пользователь]")
        #    args = ['rewards', 'add', args[0]]
        
        if not args[0]:
            help_message = "Настройки бота:\n"
            for section_id, section_object in sections.items():
                help_message += '• ' + (section_object['_name_'] if '_name_' in section_object else section_id) + " (" + section_object['_words_'][0]  + "):\n"
                actions = []
                for name, _ in section_object.items():
                    if name in ['_name_', '_words_']: continue
                    actions.append(_[0])
                help_message += "Действия: "
                help_message += ", ".join(actions)
                help_message += "\n\n"
            help_message += "Пример: .ctrl [секция] [действие] [значение]"
            
            keyboard = {
                'inline': True,
                'buttons': [
                    [
                        {
                            "action": {
                                "label": "Статья: Управление ботом",
                                "type": "open_link",
                                "link": "https://vk.com/@hypebot-commands?anchor=3-upravlenie-botom"
                            }
                        }
                    ]
                ]
            }
            
            return await msg.answer(help_message, keyboard=json.dumps(keyboard))

        section_found = False    
        for section_id, section_object in sections.items():
            if args[0] in section_object.get('_words_'):
                section_found = True
                break
            
        if section_found:
            staff = msg.meta["data_chat"].getraw("_staff_")
            clients = msg.meta["data_chat"].getraw("_clients_")
            settings = msg.meta["data_chat"].getraw("_settings_")
            
            section_name = sections[section_id]['_name_']
            if 'add' in sections[section_id].keys(): add = sections[section_id]['add']
            if 'list' in sections[section_id].keys(): _list = sections[section_id]['list']
            if 'rem' in sections[section_id].keys(): rem = sections[section_id]['rem']
            if 'interact' in sections[section_id].keys(): interact = sections[section_id]['interact']
            if 'name' in sections[section_id].keys(): name = sections[section_id]['name']
            if 'link' in sections[section_id].keys(): link = sections[section_id]['link']
            
            if section_id == 'auto_kick':
                auto_kick = True if (settings.get('auto_kick', False)) else False
                
                try:
                    args[1]
                except:
                    return await msg.answer(f"&#127856; Авто-кик сейчас {'включён' if auto_kick else 'отключён'}.\nДоступные действия: {', '.join([_[0] for _ in (add, rem)])}")
                
                if args[1] in add:
                    if auto_kick:
                        return await msg.answer("&#127856; Авто-кик уже включён.")
                    
                    settings['auto_kick'] = True
                    msg.meta["data_meta"].changed = True                    
                    return await msg.answer("&#127856; Авто-кик успешно включён.\n\nЯ буду исключать пользователей, которые выходят из беседы.")
                elif args[1] in rem:
                    if not auto_kick:
                        return await msg.answer("&#127856; Авто-кик уже отключён.")
                    
                    settings['auto_kick'] = False
                    msg.meta["data_meta"].changed = True                    
                    return await msg.answer("&#127856; Авто-кик успешно отключён.")
                else:
                    return await msg.answer("&#127856; Действие не найдено, доступные действия: {}".format(", ".join([_[0] for _ in (add, rem)])))       
            elif section_id == 'api_integration':
                api_integration = True if (settings.get('api_integration', False)) else False
                
                try:
                    args[1]
                except:
                    return await msg.answer(f"&#127856; API-Интеграция сейчас {'включена' if api_integration else 'отключена'}.\nДоступные действия: {', '.join([_[0] for _ in (add, rem)])}")
                
                if args[1] in add:
                    if api_integration:
                        return await msg.answer("&#127856; API-Интеграция уже включена.\n\nДоступ:\n&#9989; Изменение профилей (ники, роли, награды).\n&#9989; Изменение настроек (роли, права, авто-кик).\n&#10060; Исключение и приглашение участников.")
                    
                    if msg.from_id not in [349154007, 522223932]:
                        return await msg.answer("&#127856; API-Интеграция недоступна для беседы.")
                    
                    settings['api_integration'] = True
                    settings['api_integration_read'] = True
                    settings['api_integration_write'] = True
                    settings['api_integration_kick'] = False
                    msg.meta["data_meta"].changed = True                    
                    return await msg.answer("&#127856; API-Интеграция успешно включена.\n\nТеперь беседой можно управлять с помощью API-Интерфейса.\n\nДоступ:\n&#9989; Изменение профилей (ники, роли, награды).\n&#9989; Изменение настроек (роли, права, авто-кик).\n&#10060; Исключение и приглашение участников.")
                elif args[1] in rem:
                    if not api_integration:
                        return await msg.answer("&#127856; API-Интеграция уже отключена.")
                    
                    settings['api_integration'] = False
                    settings['api_integration_read'] = False
                    settings['api_integration_write'] = False
                    settings['api_integration_kick'] = False
                    msg.meta["data_meta"].changed = True                    
                    return await msg.answer("&#127856; API-Интеграция успешно отключена.\n\nДоступ:\n&#10060; Изменение профилей (ники, роли, награды).\n&#10060; Изменение настроек (роли, права, авто-кик).\n&#10060; Исключение и приглашение участников.")
                else:
                    return await msg.answer("&#127856; Действие не найдено, доступные действия: {}".format(", ".join([_[0] for _ in (add, rem)])))    
            elif section_id == 'chat_rules':
                if settings.get('chat_rules', None):
                    chat_rules = settings['chat_rules'].get('list')
                    chat_rules_link = settings['chat_rules'].get('link', None)
                else:
                    chat_rules, chat_rules_link = None, None
                
                try:
                    args[1]
                except:
                    return await msg.answer(f"&#127856; Правила беседы {'установлены' if chat_rules else 'не добавлены'}.\n{f'&#128018; Ссылка на правила: {chat_rules_link}' if chat_rules_link else '&#10071; Ссылка на правила не указана.'}\n\nДоступные действия: {', '.join([_[0] for _ in (add, rem, _list, link)])}")
                
                if args[1] in add:
                    chat_rules = []
                    
                    full_text_args = full_text.replace("&quot;", "\"").split('\n')
                    rules_split = full_text_args[1:]
                    
                    for rule_text in rules_split:
                        rule = rule_text.split('|')
                        
                        rule_obj = {
                            'id': rule[0],
                            'name': rule[1],
                            'rule': rule[2]
                        }
                        
                        if len(rule) > 4:
                            rule_obj['link'] = rule[3]
                            rule_obj['sanctions'] = rule[4].split(',')
                        else:
                            rule_obj['link'] = None
                            rule_obj['sanctions'] = rule[3].split(',')
                        
                        chat_rules.append(rule_obj)
                        
                    settings['chat_rules'] = {
                        'link': None,
                        'list': chat_rules
                    }
                    
                    return await msg.answer("&#127856; Правила сохранены.")
                elif args[1] in rem:
                    if not chat_rules:
                        return await msg.answer("&#127856; Правила беседы не добавлены, нечего удалять.")                        
                    settings['chat_rules'] = {'link': None, 'list': None}
                    
                    return await msg.answer("&#127856; Правила беседы удалены.")
                elif args[1] in _list:
                    if not chat_rules:
                        return await msg.answer("&#127856; Правила беседы не добавлены.")
                    
                    chat_rules_msg = '&#128018; Правила беседы:'
                    for rule in chat_rules:
                        chat_rules_msg += f"\n{rule['id']}. {rule['name']}\nПравило: {rule['rule']}"
                        if rule.get('link', None):
                            chat_rules_msg += f"\nСсылка: {rule['link']}"
                    
                    return await msg.answer(chat_rules_msg)
                elif args[1] in link:
                    try:
                        args[2]
                        
                        settings['chat_rules'] = {
                            'link': args[2],
                            'list': chat_rules
                        }
    
                        return await msg.answer("&#127856; Ссылка на правила установлена.")                        
                    except:
                        if chat_rules_link:
                            return await msg.answer(f"&#127856; Ссылка на правила: {chat_rules_link}")
                        return await msg.answer("&#127856; Ссылка на правила не установлена.")
                else:
                    return await msg.answer("&#127856; Действие не найдено, доступные действия: {}".format(", ".join([_[0] for _ in (add, rem, _list, link)])))
            elif section_id == 'username':
                try:
                    args[1]
                except:
                    return await msg.answer("&#127856; Доступные действия: {}".format(", ".join([_[0] for _ in (rem, interact)])))
                
                if args[1] in rem:
                    client_id = None
                    client_id = await parse_user_id(msg)
                    if not client_id:
                        return await msg.answer("&#127856; Вы должны указать пользователя, которому хотите удалить ник.")
                    
                    if str(client_id) not in clients:
                        clients[str(client_id)] = {}
                    
    
                    clients[str(client_id)]["username"] = None
                    clients[str(client_id)]["has_username"] = False

                    if msg.meta["data_chat"]:
                        msg.meta["data_chat"].changed = True
                    
                    return await msg.answer("&#127856; Ник успешно удалён.")
                elif args[1] in interact:
                    client_id = None
                    client_id = await parse_user_id(msg)
                    if not client_id:
                        return await msg.answer("&#127856; Вы должны указать пользователя, которому хотите ограничить возможность взаимодействия с ником.")
                    
                    if str(client_id) not in clients:
                        clients[str(client_id)] = {}
                    
                    clients[str(client_id)]["can_change_username"] = False if clients[str(client_id)].get('can_change_username', True) else True
                    
                    if msg.meta["data_chat"]:
                        msg.meta["data_chat"].changed = True
                    
                    return await msg.answer("&#127856; Ограничение на взаимодействие с ником успешно {}.".format("аннулировано" if clients[str(client_id)]["can_change_username"] else "установлено"))
                else:
                    return await msg.answer("&#127856; Действие не найдено, доступные действия: {}".format(", ".join([_[0] for _ in (rem, interact)])))           
            elif section_id == 'roles':
                try:
                    args[1]
                except:
                    actions = []
                    for _ in (add, rem, _list, name):
                        actions.append(_[0])
                    return await msg.answer("&#127856; Доступные действия: {}".format(", ".join(actions)))
                
                if args[1] in name:
                    roles_visual = staff.keys()
                        
                    try:
                        role = args[2]
                    except:
                        return await msg.answer("&#127856; Роль не указана, доступные роли: {}".format(", ".join(roles_visual)))
                    
                    try:
                        full_text_args = full_text.split(' ')
                        new_name = full_text_args[3]                        
                    except:
                        new_name = None
                        
                    if role not in roles_visual:
                        return await msg.answer("&#127856; Роль не найдена, доступные роли: {}".format(", ".join(roles_visual)))
                    else:
                        current_name = staff[role]['info']['name']
                        if not new_name or (new_name == current_name):
                            return await msg.answer("&#127856; Текущее имя роли: {}".format(current_name))

                        staff[role]['info']['name'] = new_name
    
                        if msg.meta["data_chat"]:
                            msg.meta["data_chat"].changed = True

                        return await msg.answer("&#127856; Имя роли успешно изменено!")
            
                elif args[1] in add:
                    roles_visual = []
                    for role in staff.keys():
                        if role != "any": roles_visual.append(role)
                        
                    try:
                        role = args[2]
                    except:
                        return await msg.answer("&#127856; Роль не указана, доступные роли: {}".format(", ".join(roles_visual)))
                    
                    if args[2] not in roles_visual:
                        return await msg.answer("&#127856; Роль не найдена, доступные роли: {}".format(", ".join(roles_visual)))
                    
                    target_user_id = await parse_user_id(msg)
                    if not target_user_id:
                        return await msg.answer("&#127856; Вы должны указать пользователя, которому хотите выдать роль.")
                    
                    if target_user_id in staff[args[2]]["clients"]:
                        return await msg.answer("&#127856; Роль уже назначена.")
                    
                    for role, users in staff.items():
                        if "clients" not in users: continue
                        if target_user_id in users["clients"]:
                            staff[role]["clients"].remove(target_user_id)
                    
                    staff[args[2]]["clients"].append(target_user_id)
                    
                    msg.meta["data_meta"].changed = True
                    if msg.meta["data_chat"]:
                        msg.meta["data_chat"].changed = True
                        
                    return await msg.answer("&#127856; Роль успешно назначена.")
                elif args[1] in rem:
                    target_user_id = await parse_user_id(msg)
                    if not target_user_id:
                        return await msg.answer("&#127856; Вы должны указать пользователя, с которого хотите снять роль.")
                    
                    role_removed = False
                    for role, users in staff.items():
                        if "clients" not in users: continue
                        if target_user_id in users["clients"]:
                            staff[role]["clients"].remove(target_user_id)
                            role_removed = True
                    
                    if role_removed:
                        msg.meta["data_meta"].changed = True
                        if msg.meta["data_chat"]:
                            msg.meta["data_chat"].changed = True
                        
                        return await msg.answer("&#127856; Роль успешно снята.")
                    else:
                        return await msg.answer("&#127856; Роль отсутствует у пользователя.")
                elif args[1] in _list:
                    staff_message = f"{section_name}:\n\n"
                    
                    roles_visual = []
                    for role in staff.keys():
                        if role != "any": roles_visual.append(role)

                    for role, role_obj in staff.items():
                        if role == "any": continue
                        name = role_obj["info"]["name"]
                        priority = role_obj["info"]["priority"]
                        staff_message += f"[{priority}] {name} ({role}):\n"
                        if "clients" in role_obj and role_obj["clients"]:
                            role_users = []
                            for m in role_obj["clients"]:
                                username = await get_username(msg, m, only_first_name=False)
                                role_users.append(username)
                            staff_message += "\n".join("• %s" % _ for _ in role_users)
                        else:
                            staff_message += "—"
                        
                        staff_message += "\n\n"
                    return await msg.answer(staff_message, disable_mentions=1)
                else:
                    actions = []
                    for _ in (add, rem, _list, name):
                        actions.append(_[0])
                    return await msg.answer("&#127856; Действие не найдено, доступные действия: {}".format(", ".join(actions)))
            elif section_id == 'permissions':
                try:
                    args[1]
                except:
                    actions = []
                    for _ in (add, _list):
                        actions.append(_[0])
                    return await msg.answer("&#127856; Доступные действия: {}".format(", ".join(actions)))
                
                if args[1] in add:
                    try:
                        role = args[2]
                    except:
                        return await msg.answer("&#127856; Роль не указана, доступные роли: {}".format(", ".join(staff.keys())))
                    
                    if args[2] not in staff.keys():
                        return await msg.answer("&#127856; Роль не найдена, доступные роли: {}".format(", ".join(staff.keys())))
                    
                    try:
                        cmd = args[3]
                        for prefix in self.prefixes:
                            cmd = cmd.replace(prefix, "")
                    except:
                        return await msg.answer("&#127856; Команда не указана или указана с ошибкой.")

                    plugins = {}
                    for plugin in self.handler.plugins:
                        if plugin.name in plugins: continue
                        if hasattr(plugin, "hidden"):
                            if plugin.hidden: continue
                        if hasattr(plugin, "required_role"):
                            if hasattr(plugin, "commands") and plugin.commands:
                                name = plugin.name
                                if hasattr(plugin, "description"):
                                    if plugin.description and plugin.description[0]:
                                        name = plugin.description[0]
                                    
                                plugins[plugin.name] = (name, plugin.commands)
                        
                    plugin_by_cmd = None
                    for plugin_name, plugin_obj in plugins.items():
                        if cmd in plugin_obj[1]:
                            plugin_by_cmd = plugin_name
                    
                    if not plugin_by_cmd:
                        return await msg.answer("&#127856; Команда не найдена.")

                    changed = False
                    for role_name, role_obj in staff.items():
                        if role == role_name:
                            name = role_obj["info"]["name"]
                            if "permissions" not in role_obj:
                                staff[role_name]["permissions"] = []
                                
                            if plugin_by_cmd not in staff[role_name]["permissions"]:
                                if plugin_by_cmd in ["SyncPlugin", "DebugPlugin"]:
                                    return await msg.answer(f"&#127856; Доступ к команде «{plugins[plugin_by_cmd][0]}» изменить нельзя.")                                
                                
                                staff[role_name]["permissions"].append(plugin_by_cmd)
                                changed = True
                                
                                if role == "any":
                                    message = f"&#127856; Доступ к команде «{plugins[plugin_by_cmd][0]}» теперь с любой роли."
                                else:
                                    message = f"&#127856; Доступ к команде «{plugins[plugin_by_cmd][0]}» теперь с роли «{name}»."
                            else:
                                if role == "any":
                                    message = f"&#127856; Доступ к команде «{plugins[plugin_by_cmd][0]}» уже с любой роли."
                                else:
                                    message = f"&#127856; Доступ к команде «{plugins[plugin_by_cmd][0]}» уже с роли «{name}»."
                        else:
                            if "permissions" in role_obj:
                                if plugin_by_cmd in staff[role_name]["permissions"]:
                                    staff[role_name]["permissions"].remove(plugin_by_cmd)
                                    changed = True
                    if changed:
                        msg.meta["data_meta"].changed = True
                        if msg.meta["data_chat"]:
                            msg.meta["data_chat"].changed = True
                        
                    return await msg.answer(message)
                elif args[1] in _list:
                    plugins = {}
                    for plugin in self.handler.plugins:
                        if plugin.name in plugins: continue
                        if hasattr(plugin, "required_role"):
                            if hasattr(plugin, "commands") and plugin.commands:
                                cmd, name = plugin.commands[0], plugin.name
                                if hasattr(plugin, "description"):
                                    if plugin.description and plugin.description[0]:
                                        name = plugin.description[0]
                                        
                                plugins[plugin.name] = (plugin.name, name, cmd, plugin.required_role)
                    
                    perms = {}
                    for plugin_name, obj in plugins.items():
                        if plugin_name in ["SyncPlugin", "DebugPlugin"]:
                            continue
                        required_role = None
                        for role, role_obj in staff.items():
                            name = role_obj["info"]["name"]
                            if ("permissions" in role_obj) and role_obj["permissions"]:
                                if plugin_name in role_obj["permissions"]:
                                    required_role = role
                        required_role = required_role if required_role else (obj[3] if obj[3] else "any")
    
                        if required_role not in perms:
                            perms[required_role] = []
                            
                        if required_role == "any":
                            if plugin_name in ["RuGamingProfilePlugin", "RuGamingBalancePlugin", "RuGamingRolePlugin", "RuGamingGexpPlugin", "RuGamingGexpTopPlugin"]:
                                continue
                            
                        perms[required_role].append(obj)
                    
                    perms_message = f"{section_name}:\n"
                    for role, role_obj in staff.items():
                        if role == "any": continue
                        name = role_obj["info"]["name"]
                        priority = role_obj["info"]["priority"]
                        
                        perms_message += f"[{priority}] {name} ({role}):\n"
                        
                        if role in perms:
                            cmds = perms[role]
                            
                            for c in cmds:
                                perms_message += f"• {c[1]} (.{c[2]})\n"
                        else:
                            perms_message += "—\n"
                        perms_message += "\n\n"
                    
                    if "any" in perms:
                        perms_message += f"Доступно всем (any):\n"
                        for p in perms["any"]:
                            perms_message += f"• {p[1]} (.{p[2]})\n"     
                    else:
                        perms_message += f"Доступно всем:\n—\n"
                    
                    return await msg.answer(perms_message, disable_mentions=1)
                else:
                    actions = []
                    for _ in (add, _list):
                        actions.append(_[0])
                    return await msg.answer("&#127856; Действие не найдено, доступные действия: {}".format(", ".join(actions)))
            elif section_id == 'rewards':
                try:
                    args[1]
                except:
                    actions = []
                    for _ in (add, rem, _list):
                        actions.append(_[0])
                    return await msg.answer("&#127856; Доступные действия: {}".format(", ".join(actions)))

                if args[1] in add:
                    if "\n" not in text:
                        return await msg.answer("&#127856; Награда не указана.")
                    
                    try:
                        _, text_ = self.parse_message(msg, full=True)
                        text_for_find_target = text_.split('\n')[0]
                        reward = text_.split('\n')[1]
                    except:
                        return await msg.answer("&#127856; Награда не указана.")
                    
                    try:
                        level = int(args[2])
    
                        if level <= 0:
                            return await msg.answer("&#127856; Степень награды должна быть положительным числом, от 1 до {}.".format(len(self.rewards_levels)))
                        
                        if level > len(self.rewards_levels):
                            return await msg.answer("&#127856; Указана слишком высокая степень, максимальная: {}.".format(len(self.rewards_levels)))
                    except:
                        level = 1
                        
                    client_id = None
                    client_id = await parse_user_id(msg, custom_text=text_for_find_target)
                    if not client_id:
                        return await msg.answer("&#127856; Укажите пользователя, которого нужно наградить.")
                    
                    if str(client_id) not in clients:
                        clients[str(client_id)] = {}
                    
                    if "rewards" not in clients[str(client_id)]:
                        clients[str(client_id)]["rewards"] = []
                    
                    for r in clients[str(client_id)]["rewards"]:
                        if type(r) == str:
                            reward_obj = {
                                'reward': r,
                                'level': 0,
                                'awarded_by': None,
                                'timestamp': int(time.time()),
                                '_ver_': 1
                            }
                            clients[str(client_id)]["rewards"].append(reward_obj)
                            clients[str(client_id)]["rewards"].remove(r)
                    
                    reward_obj = {
                        'reward': reward,
                        'level': level-1,
                        'awarded_by': msg.from_id,
                        'timestamp': int(time.time()),
                        '_ver_': 1
                    }
                    
                    clients[str(client_id)]["rewards"].append(reward_obj)
                    
                    msg.meta["data_meta"].changed = True
                    if msg.meta["data_chat"]:
                        msg.meta["data_chat"].changed = True
                        
                    return await msg.answer("&#127856; Награда успешно выдана.")
                elif args[1] in rem:
                    try:
                        reward_position = args[2]
                    except:
                        return await msg.answer("&#127856; Позиция награды не указана.")
                    
                    try:
                        reward_position = int(args[2])
                    except:
                        return await msg.answer("&#127856; Позиция награды должна быть положительным числом.")
                    
                    if reward_position <= 0:
                        return await msg.answer("&#127856; Позиция награды должна быть положительным числом.")
                    
                    client_id = None
                    client_id = await parse_user_id(msg)
                    if not client_id:
                        return await msg.answer("&#127856; Укажите пользователя, с которого нужно снять награду")
                    
                    if str(client_id) not in clients:
                        clients[str(client_id)] = {}
                    
                    if "rewards" not in clients[str(client_id)]:
                        return await msg.answer("&#127856; Награды отсутствуют.")
                    
                    if not clients[str(client_id)]["rewards"]:
                        return await msg.answer("&#127856; Награды отсутствуют.")
                    
                    rewards_count = len(clients[str(client_id)]["rewards"])
                    if reward_position > rewards_count:
                        if rewards_count == 1:
                            reward_position = 1
                        else:
                            return await msg.answer(f"&#127856; Позиция награды должна быть положительным числом, от 1 до {rewards_count} включительно.")
                
                    for r in clients[str(client_id)]["rewards"]:
                        if type(r) == str:
                            reward_obj = {
                                'reward': r,
                                'level': 0,
                                'awarded_by': msg.from_id,
                                'timestamp': int(time.time()),
                                '_ver_': 1
                            }
                            clients[str(client_id)]["rewards"].append(reward_obj)
                            clients[str(client_id)]["rewards"].remove(r)
                    
                    reward_position = int((reward_position-1))
                    i = 0
                    for r in clients[str(client_id)]["rewards"]:
                        if i == reward_position:
                            clients[str(client_id)]["rewards"].remove(r)
                            break
                        i += 1
            
                    msg.meta["data_meta"].changed = True
                    if msg.meta["data_chat"]:
                        msg.meta["data_chat"].changed = True
                    
                    return await msg.answer("&#127856; Награда успешно снята.")
                elif args[1] in _list:
                    client_id = None
                    client_id = await parse_user_id(msg)
                    if not client_id:
                        return await msg.answer("&#127856; Укажите пользователя, награды когорого Вы хотите увидеть.")
                    
                    if str(client_id) in clients:
                        client = clients[str(client_id)]
                        if ("rewards" in client) and client["rewards"]:
                            username = await get_username(msg, client_id, only_first_name=False)
                            
                            rewards = []
                            for r in client["rewards"]:
                                if type(r) == str:
                                    rewards.append(f"&#127895; {r}")
                                else:
                                    reward_text = r['reward']
                                    reward_level = r['level']
                                    reward_icon = self.rewards_levels[reward_level] if reward_level <= len(self.rewards_levels) else self.rewards_levels[0]
                                    rewards.append(f"{reward_icon} {reward_text}")
                                    
                            rewards = "\n".join("%s" % _ for _ in rewards)
                            return await msg.answer("&#127942; Награды {}:\n{}".format(username, rewards))
                    return await msg.answer("&#127856; Награды отсутствуют.")
                else:
                    actions = []
                    for _ in (add, rem, _list):
                        actions.append(_[0])
                    return await msg.answer("&#127856; Действие не найдено, доступные действия: {}".format(", ".join(actions)))
        
            return await msg.answer("&#127856; Данная секция еще в разработке.")
        else:
            return await msg.answer("&#127856; Секция не найдена, доступные секции: {}".format(", ".join([sections[_]['_words_'][0] for _ in sections.keys()])))
