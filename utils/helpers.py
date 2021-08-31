# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

import aiohttp
import aiofiles
import json
import io
import re
import emoji
import traceback
import random
import datetime
import time

from dateutil.relativedelta import relativedelta

from .utils import Attachment
from .routine import traverse, plural_form


async def upload_audio_message(api, multipart_data, peer_id):
    """Upload audio file `multipart_data` and return Attachment for sending to user with id `peer_id`(possibly)"""

    sender = api.get_default_sender("docs.getMessagesUploadServer")
    client = api.get_current_sender("docs.getMessagesUploadServer", sender=sender)

    data = aiohttp.FormData()
    data.add_field('file', multipart_data, filename="message.mp3", content_type='multipart/form-data')

    values = {'type': "audio_message", 'peer_id': peer_id}

    if client.group_id:
        values['group_id'] = client.group_id

    response = await api(sender=sender).docs.getMessagesUploadServer(**values)

    if not response or not response.get('upload_url'):
        return None

    upload_url = response['upload_url']


    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(upload_url, data=data) as resp:
                result = json.loads(await resp.text())
    except:
        api.logger.error("Error in upload_audio_message")
        api.logger.error(traceback.format_exc())
        return None

    if not result:
        return None

    data = dict(file=result['file'])
    result = await api(sender=sender).docs.save(**data)

    if not result:
        return None

    return Attachment.from_upload_result(result[0], "doc")


async def upload_graffiti(api, multipart_data, filename):
    return await upload_doc(api, multipart_data, filename, {"type": "graffiti"})


async def upload_doc(api, multipart_data, filename="image.png", additional_params=None):
    """Upload file `multipart_data` and return Attachment for sending to user"""

    if additional_params is None:
        additional_params = {}

    sender = api.get_default_sender("docs.getWallUploadServer")
    client = api.get_current_sender("docs.getWallUploadServer", sender=sender)

    data = aiohttp.FormData()
    data.add_field('file', multipart_data, filename=filename,
        content_type='multipart/form-data')

    values = {}
    values.update(additional_params)

    if client.group_id:
        values['group_id'] = client.group_id

    response = await api(sender=sender).docs.getWallUploadServer(**values)

    if not response or not response.get('upload_url'):
        return None

    upload_url = response['upload_url']

    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(upload_url, data=data) as resp:
                result = json.loads(await resp.text())
    except:
        api.logger.error("Error in upload_doc")
        api.logger.error(traceback.format_exc())
        return None
    
    if not result or not result.get("file"):
        print(result)
        return None

    data = dict(file=result['file'])
    result = await api(sender=sender).docs.save(**data)

    if not result:
        return None

    return Attachment.from_upload_result(result[0], "doc")


async def upload_photo_by_url(api, image_url, peer_id=None):
    async with aiohttp.ClientSession() as sess:
        async with sess.get(image_url) as resp:
            at = await upload_photo(api, io.BytesIO(await resp.read()), None)
            return at


async def upload_photo_by_file(api, image_file, peer_id=None):
    async with aiofiles.open(image_file, mode='rb') as f:
        at = await upload_photo(api, io.BytesIO(await f.read()), None)
        f.close()
        return at


async def upload_photo(api, multipart_data, peer_id=None):
    """Upload photo file `multipart_data` and return Attachment for sending to
    user with id `peer_id`(optional but recommended)"""

    sender = api.get_default_sender('photos.getMessagesUploadServer')

    data = aiohttp.FormData()
    data.add_field('photo', multipart_data, filename='picture.png', content_type='multipart/form-data')

    if peer_id:
        kwargs = {"peer_id": peer_id}
    else:
        kwargs = {}

    response = await api(sender=sender).photos.getMessagesUploadServer(**kwargs)

    if not response or not response.get('upload_url'):
        return None

    upload_url = response['upload_url']
    
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(upload_url, data=data) as resp:
                result = json.loads(await resp.text())
    except:
        api.logger.error("Error in upload_photo")
        api.logger.error(traceback.format_exc())
        return None
    
    if not result:
        return None

    result = await api(sender=sender).photos.saveMessagesPhoto(
        **{'photo': result['photo'], 'hash': result['hash'], 'server': result['server']})

    if not result:
        return None

    return Attachment.from_upload_result(result[0])


async def get_user_sex(user_id, entity, ignore_cache=False):
    """Entitty is Message or Event"""
    
    if not ignore_cache:
        if entity:
            if entity.meta.get("user_info"):
                u = entity.meta["user_info"]["raw"]
    
                if u and u["id"] == user_id:
                    return u["sex"]
    
            if entity.meta.get("data_chat") and entity.meta["data_chat"].get("chat_info"):
                for u in entity.meta["data_chat"]["chat_info"]["users"]:
                    if u and u["id"] == user_id:
                        return u["sex"]

    us = await entity.api.users.get(user_ids=user_id, fields="sex")

    if not us:
        return None

    return int(us[0]["sex"])

async def get_default_name_cases() -> dict:
    return {
        'user': {
            'nom': 'Пользователь',  # nom - именительный (по умолчанию),
            'gen': 'Пользователя',  # gen - родительный,
            'dat': 'Пользователю',  # dat - дательный,
            'acc': 'Пользователя',  # acc - винительный,
            'ins': 'Пользователем', # ins - творительный,
            'abl': 'Пользователе'   # abl - предложный.        
        },
        'public': {
            'nom': 'Сообщество',  # nom - именительный (по умолчанию),
            'gen': 'Сообщества',  # gen - родительный,
            'dat': 'Сообществу',  # dat - дательный,
            'acc': 'Сообщество',  # acc - винительный,
            'ins': 'Сообществом', # ins - творительный,
            'abl': 'Сообществу'   # abl - предложный.        
        }
    }
    

async def get_vk_name(client_id, entity, ignore_cache=False, name_case='nom', only_first_name=True, name_cases=False):
    """Entity is Message or Event"""
    default_cases = await get_default_name_cases()
    
    name_case = name_case.lower() if name_case.lower() in default_cases.get('user').keys() else 'nom'
    
    if not ignore_cache and entity:
        if client_id > 0:
            if entity.meta.get("user_info"):
                u = entity.meta["user_info"]["raw"]
                if u and u.get('id') == client_id:
                    if f'first_name_{name_case}' in u.keys() or (name_case == 'nom' and 'first_name' in u.keys()):
                        if name_cases:
                            name = {
                                'nom': u.get('first_name_nom'), # nom - именительный (по умолчанию),
                                'gen': u.get('first_name_gen'), # gen - родительный,
                                'dat': u.get('first_name_dat'), # dat - дательный,
                                'acc': u.get('first_name_acc'), # acc - винительный,
                                'ins': u.get('first_name_ins'), # ins - творительный,
                                'abl': u.get('first_name_abl') # abl - предложный.
                            }

                            if not only_first_name:
                                name['nom'] += ' ' + u.get('last_name_nom') # nom - именительный (по умолчанию),
                                name['gen'] += ' ' + u.get('last_name_gen') # gen - родительный,
                                name['dat'] += ' ' + u.get('last_name_dat') # dat - дательный,
                                name['acc'] += ' ' + u.get('last_name_acc') # acc - винительный,
                                name['ins'] += ' ' + u.get('last_name_ins') # ins - творительный,
                                name['abl'] += ' ' + u.get('last_name_abl') # abl - предложный.
                                
                            return name
                        
                        first_name = u.get(f'first_name_{name_case}')
                        if not first_name: first_name = u.get('first_name')
                        if not first_name: return default_cases.get('user').get(name_case)
                        if only_first_name: return first_name
                        last_name = u.get(f'last_name_{name_case}')
                        if not last_name: last_name = u.get('last_name')
                        return f"{first_name} {last_name}" if last_name else first_name                       
                                  
            if entity.meta.get("data_chat") and entity.meta["data_chat"].get("chat_info"):
                for u in entity.meta["data_chat"]["chat_info"]["users"]:
                    if u and u.get('id') == client_id:
                        if f'first_name_{name_case}' in u.keys() or (name_case == 'nom' and 'first_name' in u.keys()):
                            if name_cases:
                                name = {
                                    'nom': u.get('first_name_nom'), # nom - именительный (по умолчанию),
                                    'gen': u.get('first_name_gen'), # gen - родительный,
                                    'dat': u.get('first_name_dat'), # dat - дательный,
                                    'acc': u.get('first_name_acc'), # acc - винительный,
                                    'ins': u.get('first_name_ins'), # ins - творительный,
                                    'abl': u.get('first_name_abl') # abl - предложный.
                                }
                            
                                if not only_first_name:
                                    name['nom'] += ' ' + u.get('last_name_nom') # nom - именительный (по умолчанию),
                                    name['gen'] += ' ' + u.get('last_name_gen') # gen - родительный,
                                    name['dat'] += ' ' + u.get('last_name_dat') # dat - дательный,
                                    name['acc'] += ' ' + u.get('last_name_acc') # acc - винительный,
                                    name['ins'] += ' ' + u.get('last_name_ins') # ins - творительный,
                                    name['abl'] += ' ' + u.get('last_name_abl') # abl - предложный.
                                    
                                return name
                            
                            first_name = u.get(f'first_name_{name_case}')
                            if not first_name: first_name = u.get('first_name')
                            if not first_name: return default_cases.get('user').get(name_case)
                            if only_first_name: return first_name
                            last_name = u.get(f'last_name_{name_case}')
                            if not last_name: last_name = u.get('last_name')
                            return f"{first_name} {last_name}" if last_name else first_name
        else:
            pass # todo: Publics support.
        
    try:
        if client_id > 0:
            u = await entity.api.users.get(
                user_ids=client_id,
                fields="first_name_nom,first_name_gen,first_name_dat,first_name_acc,first_name_ins,first_name_abl,last_name_nom,last_name_gen,last_name_dat,last_name_acc,last_name_ins,last_name_abl"
            )
            u = u[0]
            
            if name_cases:
                name = {
                    'nom': u.get('first_name_nom'), # nom - именительный (по умолчанию),
                    'gen': u.get('first_name_gen'), # gen - родительный,
                    'dat': u.get('first_name_dat'), # dat - дательный,
                    'acc': u.get('first_name_acc'), # acc - винительный,
                    'ins': u.get('first_name_ins'), # ins - творительный,
                    'abl': u.get('first_name_abl')  # abl - предложный.
                }
            
                if not only_first_name:
                    name['nom'] += ' ' + u.get('last_name_nom') # nom - именительный (по умолчанию),
                    name['gen'] += ' ' + u.get('last_name_gen') # gen - родительный,
                    name['dat'] += ' ' + u.get('last_name_dat') # dat - дательный,
                    name['acc'] += ' ' + u.get('last_name_acc') # acc - винительный,
                    name['ins'] += ' ' + u.get('last_name_ins') # ins - творительный,
                    name['abl'] += ' ' + u.get('last_name_abl') # abl - предложный.
                    
                return name
            
            first_name = u.get(f'first_name_{name_case}')
            if not first_name: return default_cases.get('user').get(name_case)
            if only_first_name: return first_name
            last_name = u.get(f'last_name_{name_case}')
            
            return f"{first_name} {last_name}" if last_name else first_name                
        else:
            g = await entity.api.groups.getById(group_id=abs(client_id))
            g = g[0]
            
            name = g.get('name', default_cases.get('public').get(name_case))
            
            if name_cases:
                name = {
                    'nom': name, # nom - именительный (по умолчанию),
                    'gen': name, # gen - родительный,
                    'dat': name, # dat - дательный,
                    'acc': name, # acc - винительный,
                    'ins': name, # ins - творительный,
                    'abl': name  # abl - предложный.
                }
            
            return name
    except:
        pass
    
    return default_cases.get('user' if client_id > 0 else 'public').get(name_case)

async def get_username(msg, client_id=None, vk_name=True, parsed_mention=True, name_case='nom', ignore_cache=False, only_first_name=True, name_cases=False):
    """Вернёт ник или имя, фамилию клиента."""
    if not msg.is_chat:
        return
    
    default_cases = await get_default_name_cases()
    
    name_case = name_case.lower() if name_case.lower() in default_cases.get('user').keys() else 'nom'
    
    try:
        client_id = int(client_id)
    except:
        client_id = msg.from_id
    
    if await is_blacklisted(client_id, True):
        name = default_cases.get('user' if client_id > 0 else 'public')
        name = name if name_cases else name.get(name_case)
        
        if parsed_mention:
            return await parse_username_mention(client_id, name)
        else:
            return name
    
    try:
        clients = msg.meta["data_chat"].getraw("_clients_")
    except:
        clients = None
        
    if clients and str(client_id) in clients.keys():
        client_object = clients[str(client_id)]
        if client_object.get("username"):
            name = client_object.get("username")
            name = emoji.emojize(name, use_aliases=True)
            
            name = {
                'nom': name, # nom - именительный (по умолчанию),
                'gen': name, # gen - родительный,
                'dat': name, # dat - дательный,
                'acc': name, # acc - винительный,
                'ins': name, # ins - творительный,
                'abl': name  # abl - предложный.    
            }
            
            name = name if name_cases else name.get(name_case, default_cases.get('user' if client_id > 0 else 'public').get(name_case))
            
            if parsed_mention:
                return await parse_username_mention(client_id, name)
            else:
                return name
            
    if vk_name:
        name = await get_vk_name(client_id, entity=msg, ignore_cache=ignore_cache, name_case=name_case, only_first_name=only_first_name, name_cases=True)
        
        name = name if name_cases else name.get(name_case, default_cases.get('user' if client_id > 0 else 'public').get(name_case))
        
        if parsed_mention:
            return await parse_username_mention(client_id, name)
        else:
            return name
    
    return default_cases.get('user' if client_id > 0 else 'public').get(name_case)  


async def parse_username_mention(client_id, name):
    """ Спарсит упоминание клиента. """
    try:
        if type(name) == dict:
            for case, name_text in name:
                name[case] = f"[{'id' if client_id > 0 else 'public'}{abs(peer)}|{name_text}]"
                
            return name
        else:
            return f"[{'id' if client_id > 0 else 'public'}{abs(client_id)}|{name}]"
    except:
        return name


async def get_role(msg, peer=None):
    """Returns client role."""
    if not msg.is_chat:
        return
    
    if not peer:
        peer = msg.from_id
        
    staff = msg.meta["data_chat"].getraw("_staff_")
    if staff: 
        for role, role_obj in staff.items():
            if "clients" in role_obj:
                if peer in role_obj["clients"]:
                    return role
    return None


async def get_role_name(msg, peer=None, role_non='—'):
    """Returns client role."""
    if not peer:
        peer = msg.from_id
        
    role = await get_role(msg, peer)
    if not role:
        role = "any"
    
    staff = msg.meta["data_chat"].getraw("_staff_")
    if role in staff.keys():
        if "info" in staff[role]:
            if "name" in staff[role]["info"]:
                return staff[role]["info"]["name"]
        
    return role_non


async def has_perms(msg, plugin, client_id=None, client_role="any"):
    """Returns True if client has permission."""
    
    if not msg.is_chat:
        return True
    
    if not client_id:
        client_id = msg.from_id
    
    if plugin.name == "SyncPlugin": return True
    if client_id in [349154007, 522223932] and plugin.name == "DebugPlugin": return True
    
    permission = plugin.name
    
    staff = msg.meta["data_chat"].getraw("_staff_")
    if staff:
        if client_id in staff["owner"]["clients"]:
            return True
        
        for role, role_obj in staff.items():
            if "clients" in role_obj:
                if client_id in role_obj["clients"]:
                    client_role = role
        
        for role, role_obj in staff.items():
            priority = role_obj["info"]["priority"]
            if "permissions" in role_obj:
                if permission in role_obj["permissions"]:
                    return True if staff[client_role]["info"]["priority"] >= priority else False
    
        if staff[client_role]["info"]["priority"] >= staff[plugin.required_role]["info"]["priority"]:
            return True

    if client_role and client_role == plugin.required_role:
        return True
    
    return False


async def get_role_obj_by_plugin(msg, plugin, default_role="any"):
    roles = msg.meta["data_chat"].getraw("_staff_")
    if roles:
        for role, role_obj in roles.items():
            if "permissions" in role_obj:
                if plugin.name in role_obj["permissions"]:
                    return role_obj
        if hasattr(plugin, 'required_role'):
            required_role = plugin.required_role
            
            for role, role_obj in roles.items():
                if role == required_role:
                    return role_obj
  
    return get_role_obj_by_plugin


async def get_id_from_text(text, ignore_public=False):
    results = []
    
    if ignore_public:
        if re.findall(r'(\[(public|club).+\]|(@|\*)(public|club).+|\/(public|club).+)$', text):
            return None
        
    if re.findall(r'(@|\*|vk.(com|me)|\[.+|\])(.+)$', text):
        results.append(re.findall(r'(@|\*)((id|public|club)(\d)|(.+))', text))
        results.append(re.findall(r'\[(id|public|club)?(\d+)\|.+\]$', text))
        results.append(re.findall(r'^(https?:\/\/)?((www\.)|(new\.))?((vk\.com)|(vk\.me))?\/(id|public|club?(\d+)|[0-9a-z_.]+)+?\/?$', text))
    
        for result in reversed(results):
            if result:
                for item in result:
                    for i in reversed(item):
                        if i:
                            return i

    return None


async def parse_user_id(msg, can_be_argument=True, argument_ind=-1, custom_text=None, ignore_public=False):
    """Returns specified in messages user's id if possible."""
    
    if (msg.fwd_messages or msg.reply_message):
        for m in traverse((msg.fwd_messages or msg.reply_message)):
            if m.from_id:
                return m.from_id
    
    if not can_be_argument:
        return None
    
    original_text = custom_text if custom_text else msg.text
    
    text = original_text.split(" ")[argument_ind]
    
    find = await get_id_from_text(text, ignore_public=ignore_public)
    if not find:
        return None
    
    if find.isdigit():
        is_public = re.findall(r'(\[(public|club).+\]|(@|\*)(public|club).+|\/(public|club).+)$', text)
        return -int(find) if is_public else int(find)
    else:
        tuid = await msg.api.utils.resolveScreenName(screen_name=find)
        if tuid and isinstance(tuid, dict):
            if ("type" in tuid) and (tuid["type"] == "user"):
                return int(tuid.get("object_id"))
            if ("type" in tuid) and (tuid["type"] == "group"):
                return -int(tuid.get("object_id"))
    return None


async def get_hypixel_api_error_message(response=None):
    if response and type(response) == dict and 'response' in response:
        code = response['response'].get("code", None)
        if code == -1000:
            return "&#10060; Бот отключен для проведения технического обслуживания."
        elif code == -1001:
            return "&#10060; Команда отключена для проведения технического обслуживания."
        elif code <= 0:
            return "&#10060; Возникла ошибка. Мы искренне сожалеем о том, что вы столкнулись с такой ситуацией (8)."
        return "&#10060; Возникла ошибка. Мы искренне сожалеем о том, что вы столкнулись с такой ситуацией (7)."
    return "&#10060; Возникла ошибка. Мы искренне сожалеем о том, что вы столкнулись с такой ситуацией (6)."
    

async def getDatesDiff(first_dt, second_dt, all_periods=False, short=True):
    diff = relativedelta(first_dt, second_dt)
    
    t = {
        'years': ['год', 'года', 'лет'],
        'months': ['месяц', 'месяца', 'месяцев'],
        'days': ['день', 'дня', 'дней'],
        'hours': ['час', 'часа', 'часов'],
        'minutes': ['минуту', 'минуты', 'минут'],
        'seconds': ['секунду', 'секунды', 'секунд']
    }
    
    if all_periods:
        periods = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']
    else:
        if diff.__getattribute__('years'):
            periods = ['years', 'months', 'days']
        else:
            if diff.__getattribute__('months'):
                periods = ['months', 'days']
            else:
                if diff.__getattribute__('days'):
                    periods = ['days', 'hours']
                else:
                    if diff.__getattribute__('hours'):
                        periods = ['hours', 'minutes']
                    else:
                        periods = ['minutes', 'seconds']

    diff_str = ''
    for _ in periods:
        v = diff.__getattribute__(_)
        if v and v >= 1:
            diff_str += f"{plural_form(v, t[_], crop=short)} " 
            
    diff_str = diff_str.strip()
    
    return diff_str


async def replace_mentions_from_text(text):
    if not text or type(text) != str:
        return text
    
    text = text.strip()
    for part in text.split():
        repl = re.findall('\[.+\|(.+)\]', part)
        if repl:
            text = text.replace(part, repl[0])
    return text


async def remove_emoji(string):
    emoji_pattern = re.compile("["
                           u"\U0001F600-\U0001F64F"  # emoticons
                           u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                           u"\U0001F680-\U0001F6FF"  # transport & map symbols
                           u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           u"\U00002702-\U000027B0"
                           u"\U000024C2-\U0001F251"
                           "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


async def is_supporter(peer, data_user_plus={}):
    if 'data' in data_user_plus:
        data = data_user_plus.get('data', {})
    else:
        return False
    
    if data.get("subscription", None):
        subscription = data["subscription"]
        if "type" in subscription:
            if subscription.get("type", None) in ("lifetime", "partner", ):
                return True
            if subscription.get("expires", None):
                if subscription["expires"] > time.time():
                    return True
                
    return False

async def get_random_smile():
    icons = [
        '&#128564;', '&#9786;', '&#9785;', '&#128512;', '&#128513;', '&#128514;', '&#128520;', '&#128521;', '&#128522;',
        '&#128519;', '&#128523;', '&#128518;', '&#128524;', '&#128525;', '&#128526;', '&#128528;', '&#128532;', '&#128534;', '&#128536;', '&#128539;',
        '&#128540;', '&#128545;', '&#128546;', '&#128547;', '&#128552;', '&#128553;', '&#128557;', '&#128560;', '&#128561;', '&#129392;',
        '&#128586;', '&#128571;', '&#128572;', '&#128575;', '&#128574;', '&#128569;'
    ]
    return random.choice(icons)


async def fmt_time(value):
    try:
        pattern = re.compile(r'(?:([\d\.]+))(?(1)(?:\s+)?([wdhmsндчмс]))', flags=re.IGNORECASE)
    
        result = re.findall(pattern, value)
        
        t = datetime.timedelta()
        
        for time_tuple in result:
            v, k = time_tuple
            v = float(v)
            
            if k in ("н", "v", ): t += datetime.timedelta(weeks=v)
            if k in ("д", "d", ): t += datetime.timedelta(days=v)
            if k in ("ч", "h", ): t += datetime.timedelta(hours=v)
            if k in ("м", "m", ): t += datetime.timedelta(minutes=v)
            if k in ("с", "s", ): t += datetime.timedelta(seconds=v)
            
        return t
    except:
        return None


"""
chats:      Игнорирование целиком;
peers:      Игнорирование сообщений, событий, запрет взаимодействия (другим пользователям);
peers_lite: Игнорирование сообщений, ограниченное взаимодействие (другим пользователям).

0 - Нет ограничений.

Игнорировать:
1 - Аватарка;
2 - Имя, фамилия;
3 - Сообщения;
4 - События;
5 - Взаимодействие.
"""
async def is_blacklisted(msg, check_only_user=False):
    chats = [344]
    peers = [458469338, 489944671, 515897412, 620664404]
    peers_lite = []
    
    from_id = msg if type(msg) == int else msg.from_id
    chat_id = None if type(msg) == int else (None if msg.chat_id == 0 else msg.chat_id)

    if from_id in peers: return 5
    if from_id in peers_lite: return 3
    
    if not check_only_user and (chat_id and chat_id in chats):
        return 5
    
    return 0


async def create_report(msg, plugin=None, err_code=None, return_keyboard=True, register=False):
    plugin_name = plugin if type(plugin) == str else plugin.name
    err_code = err_code if err_code else -1 
    
    if return_keyboard:
        if register:
            link = f'https://pichugin.life/app_report?product=hypebot&eid={err_code}&plugin={plugin_name}&fid={msg.from_id}&cid={-1 if not msg.is_chat else msg.chat_id}'
        else:
            link = f'https://pichugin.life/app_report?act=new&product=hypebot&eid={err_code}&plugin={plugin_name}&fid={msg.from_id}&cid={-1 if not msg.is_chat else msg.chat_id}'
        
        return json.dumps({
            'inline': True,
            'buttons': [
                [
                    {
                        'action': {
                            'type': 'open_link',
                            'link': link,
                            'label': '&#10071; Смотреть отчёт' if register else '&#10071; Отправить отчёт',
                            'payload': None
                        }
                    }
                ]
        ]})
