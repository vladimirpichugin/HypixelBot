# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

from enum import Enum
import asyncio
import time


class EventType(Enum):
    ChatChange = 1


class ProxyParametrs:
    __slots__ = ("parent", "wait", "sender")

    def __init__(self, parent, sender=None, wait="yes"):
        self.sender = sender
        self.wait = wait
        self.parent = parent

    def __getattr__(self, outer_name):
        return self.parent.create_proxy(outer_name, self.sender, self.wait)


class Proxy:
    __slots__ = ("parent", "outer_name",
                 "wait", "sender")

    def __init__(self, parent, outer_name, sender=None, wait="yes"):
        self.parent = parent
        self.outer_name = outer_name

        self.wait = wait
        self.sender = sender

    def __getattr__(self, inner_name):
        async def wrapper(**data):
            return await self.parent.method(f"{self.outer_name}.{inner_name}",
                data, sender=self.sender, wait=self.wait)

        return wrapper


class Request(asyncio.Future):
    __slots__ = ("key", "data", "sender")

    def __init__(self, key, data, sender=None):
        self.key = key
        self.data = data if data else {}
        self.sender = sender

        super().__init__()


class RequestAccumulative(Request):
    __slots__ = ("join_func", "results")

    def __init__(self, key, data, sender=None, join_func=None):
        super().__init__(key, data, sender)

        self.results = []

        if join_func:
            self.join_func = join_func

        else:
            self.join_func = lambda x, y: ",".join([x, y]) if x else y

    def accumulate(self, data, amount=1):
        for ok, ov in data.items():
            if ok not in self.data:
                continue

            if ov in self.data[ok]:
                continue

            self.data[ok] = self.join_func(self.data[ok], ov)

        future = asyncio.Future()
        future.requests_amount = amount
        self.results.append(future)

        return future

    def process_result(self, result):
        for fut in self.results:
            if fut.done() or fut.cancelled():
                continue

            try:
                fut.set_result(result.pop(0))

            except (KeyError, IndexError, AttributeError):
                fut.set_result({})

            except asyncio.InvalidStateError:
                pass


class Sender:
    __slots__ = ('target', 'user', 'group')

    def __init__(self, target=None, user=False, group=False):
        if not (user or group):
            raise ValueError("Atleast one of argumebts `user` or `group` should be set to True")

        self.user = user
        self.group = group
        self.target = target


class Attachment(object):
    __slots__ = ('type', 'owner_id', 'id', 'access_key', 'url', 'raw')

    def __init__(self, attach_type, owner_id, aid, access_key=None, url=None, raw=None):
        self.type = attach_type
        self.owner_id = owner_id
        self.id = aid
        self.access_key = access_key
        self.url = url
        self.raw = raw

    @staticmethod
    def from_upload_result(result, attach_type="photo"):
        url = None

        for k in result:
            if "photo_" in k:
                url = result[k]
            elif "link_" in k:
                url = result[k]
            elif "url" == k:
                url = result[k]

        return Attachment(attach_type, result["owner_id"], result["id"], url=url, raw=result)

    @staticmethod
    def from_raw(raw_attach):
        a_type = raw_attach['type']
        attach = raw_attach[a_type]

        url = None

        for k, v in attach.items():
            if "photo_" in k:
                url = v
            elif "link_" in k:
                url = v
            elif "url" == k:
                url = v

        return Attachment(a_type, attach.get('owner_id', ''), attach.get('id', ''), attach.get('access_key'), url, attach)

    def value(self):
        if self.access_key:
            return f'{self.type}{self.owner_id}_{self.id}_{self.access_key}'

        return f'{self.type}{self.owner_id}_{self.id}'

    def __str__(self):
        return self.value()


class MessageEventData(object):
    __slots__ = (
        "date", "time", "timestamp", "user_id", "from_id", "true_msg_id",
        "msg_id", "conversation_message_id", "is_out", "chat_id", "peer_id",
        "full_text", "is_chat", "payload", "reply_message", "action",
        "allowed_keyboard", "allowed_inline_keyboard", "allowed_button_actions",
        "is_forwarded", "forwarded", "attaches", "fwd_messages", "fwd_messages_orig",
        "lang_id", "full_message_data", 
    ) # is_hidden, geo, attachments
    
    @staticmethod
    def from_message_body(obj):
        data = MessageEventData()
        
        if "message" in obj:
            obj = obj.get("message")
        
        data.attaches = {}
        data.forwarded = []

        c = 0
        for a in obj.get("attachments", []):
            c += 1

            data.attaches[f'attach{c}_type'] = a['type']
            try:
                data.attaches[f'attach{c}'] = f'{a[a["type"]]["owner_id"]}_{a[a["type"]]["id"]}'
            except KeyError:
                data.attaches[f'attach{c}'] = ""

        if 'fwd_messages' in obj:
            data.forwarded = MessageEventData.parse_brief_forwarded_messages(obj)
            data.fwd_messages_orig = obj["fwd_messages"]
            for _ in obj["fwd_messages"]:
                data.fwd_messages = []
                data.fwd_messages.append(MessageEventData.from_message_body(_))
                data.fwd_messages = tuple(data.fwd_messages)
            
        if 'reply_message' in obj:
            data.reply_message = MessageEventData.from_message_body(obj['reply_message'])
        
        if "id" in obj:
            data.msg_id = int(obj["id"])
            data.true_msg_id = data.msg_id
            
        if "conversation_message_id" in obj:
            data.conversation_message_id = int(obj["conversation_message_id"])
        
        if "peer_id" in obj:
            data.peer_id = int(obj["peer_id"])
            if data.peer_id >= 2000000000:
                data.is_chat = True
                data.chat_id = data.peer_id-2000000000
                data.msg_id = data.conversation_message_id
            else:
                data.conversation_message_id = data.msg_id
        
        if "payload" in obj:
            data.payload = obj["payload"]
        
        if "from_id" in obj:
            data.from_id = int(obj['from_id'])
            data.user_id = data.from_id
        else:
            data.user_id = int(obj['user_id'])
            data.from_id = data.user_id
        
        if "text" in obj:
            data.full_text = obj['text']
        
        data.date = int(obj['date'] if "date" in obj else time.time()) 
        data.time = data.date
        data.timestamp = data.date
        
        data.is_out = obj.get('out', False)
        data.is_forwarded = False

        data.action = obj.get("action", None)
        
        if "client_info" in obj:
            client_info = obj["client_info"]
            data.lang_id = client_info.get("lang_id", 0)
            data.allowed_button_actions = client_info.get("button_actions", [])
            data.allowed_inline_keyboard = client_info.get("keyboard", False)
            data.allowed_keyboard = client_info.get("inline_keyboard", False)
        
        data.full_message_data = obj
            
        return data

    @staticmethod
    def parse_brief_forwarded_messages(obj):
        if 'fwd_messages' not in obj:
            return ()

        result = []

        for mes in obj['fwd_messages']:
            result.append((mes.get('id', None), MessageEventData.parse_brief_forwarded_messages(mes)))

        return tuple(result)

    @staticmethod
    def parse_brief_forwarded_messages_from_lp(data):
        result = []

        token = ""
        i = -1
        while True:
            i += 1

            if i >= len(data):
                if token:
                    result.append((token, ()))

                break

            if data[i] in "1234567890_-":
                token += data[i]
                continue

            if data[i] in (",", ")"):
                if not token:
                    continue

                result.append((token, ()))
                token = ""
                continue

            if data[i] == ":":
                stack = 1

                for j in range(i + 2, len(data)):
                    if data[j] == "(":
                        stack += 1

                    elif data[j] == ")":
                        stack -= 1

                    if stack == 0:
                        jump_to_i = j
                        break

                sub_data = data[i + 2: jump_to_i]

                result.append((token, MessageEventData.parse_brief_forwarded_messages_from_lp(sub_data)))

                i = jump_to_i + 1
                token = ""
                continue

        return tuple(result)

    def __init__(self):
        self.action = None
        self.is_chat = False
        self.is_forwarded = False
        self.is_out = False

        self.chat_id = 0
        self.peer_id = 0
        self.user_id = 0
        self.from_id = 0
        self.full_text = ""
        self.date = None
        self.time = None
        self.timestamp = None
        self.msg_id = 0
        self.true_msg_id = 0
        self.attaches = None
        self.forwarded = None
        self.fwd_messages = None
        self.fwd_messages_orig = None
        self.full_message_data = None
        self.reply_message = None
        self.conversation_message_id = None
        self.payload = None
        self.lang_id = 0
        self.allowed_button_actions = []
        self.allowed_keyboard = False
        self.allowed_inline_keyboard = False
