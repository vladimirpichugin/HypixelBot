# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

from math import ceil
from random import randint

from .utils import MessageEventData, Attachment, EventType


MAX_LENGHT = 4000


class Message:
    """
    Класс, объект которого передаётся в плагин для упрощённого ответа.
    """

    __slots__ = ('message_data', 'api', 'is_chat', 'chat_id', 'user_id', 'is_out',
                 'date', 'timestamp', 'time', 'answer_values', 'msg_id', 'text', 'full_text', 'meta', 'is_event',
                 'brief_attaches', 'brief_forwarded', '_full_attaches', '_full_forwarded',
                 'peer_id', "is_forwarded", 'true_msg_id', 'reserved_by',
                 'reply_message', 'conversation_message_id', 'from_id', 'fwd_messages', 'full_message_data', 'payload', '_payload', 'action', )

    def __init__(self, vk_api_object, message_data):
        self.message_data = message_data
        self.api = vk_api_object

        self.meta = {}
        self.reserved_by = None

        self.is_event = False
        self.is_chat = message_data.is_chat
        self.is_forwarded = message_data.is_forwarded
        self.reply_message = message_data.reply_message
        
        self.from_id = message_data.from_id
        self.user_id = message_data.user_id
        self.full_text = message_data.full_text
        self.text = self.full_text.lower().replace("&quot;", "\"")

        self.chat_id = message_data.chat_id
        self.peer_id = message_data.peer_id

        self.msg_id = message_data.msg_id
        self.true_msg_id = message_data.true_msg_id
        self.conversation_message_id = message_data.conversation_message_id
        self.is_out = message_data.is_out
        
        self.date = message_data.date
        self.time = message_data.date
        self.timestamp = message_data.date

        self.fwd_messages = message_data.fwd_messages
        self.brief_forwarded = message_data.forwarded
        self._full_forwarded = None
        
        self.brief_attaches = message_data.attaches
        self._full_attaches = None
        
        self.full_message_data = message_data.full_message_data
        self.answer_values = {'peer_id': self.peer_id, 'dont_parse_links': 1}
        
        self.action = message_data.action
        self.payload = message_data.payload
        self._payload = message_data.payload

    async def get_full_attaches(self):
        """Get list of all attachments as `Attachment` for this message"""

        if self._full_attaches is None:
            await self.get_full_data()

        return self._full_attaches

    async def get_full_forwarded(self):
        """Get list of all forwarded messages as `Message` for this message"""

        if self._full_forwarded is None:
            await self.get_full_data()

        return self._full_forwarded

    async def get_full_data(self, message_data=None):
        """Update lists of all forwarded messages and all attachments for this message"""
        
        if not message_data:
            message_data = self.full_message_data 
        
        self._full_attaches = []
        self._full_forwarded = []
        
        message = message_data if message_data else self.message_data
        
        if "attachments" in message:
            for raw_attach in message["attachments"]:
                attach = Attachment.from_raw(raw_attach) # Создаём аттач
                self._full_attaches.append(attach)  # Добавляем к нашему внутреннему списку аттачей

        if 'fwd_messages' in message:
            self._full_forwarded, self.brief_forwarded = await self.parse_forwarded_messages(message)
            
    async def parse_forwarded_messages(self, im):
        if 'fwd_messages' not in im:
            return (), ()

        result = []
        brief_result = []

        for mes in im['fwd_messages']:
            obj = MessageEventData.from_message_body(mes)

            obj.msg_id = self.msg_id
            obj.chat_id = self.chat_id
            obj.user_id = self.user_id
            obj.is_chat = self.is_chat
            obj.is_out = self.is_out
            obj.is_forwarded = True

            m = await Message.create(self.api, obj)

            big_result, small_result = await self.parse_forwarded_messages(mes)

            result.append((m, big_result))
            brief_result.append((m.msg_id, small_result))

        return tuple(result), tuple(brief_result)

    @staticmethod
    def prepare_message(message):
        """Split message to parts that can be send by `messages.send`"""

        message_length = len(message)

        if message_length <= MAX_LENGHT:
            return [message]

        def fit_parts(sep):
            current_length = 0
            current_message = ""

            sep_length = len(sep)
            parts = message.split(sep)
            length = len(parts)

            for j in range(length):
                m = parts[j]
                temp_length = len(m)

                if temp_length > MAX_LENGHT:
                    return

                if j != length - 1 and current_length + temp_length + sep_length <= MAX_LENGHT:
                    current_message += m + sep
                    current_length += temp_length + sep_length

                elif current_length + temp_length <= MAX_LENGHT:
                    current_message += m
                    current_length += temp_length

                elif current_length + temp_length > MAX_LENGHT:
                    yield current_message

                    current_length = temp_length
                    current_message = m

                    if j != length - 1 and current_length + sep_length < MAX_LENGHT:
                        current_message += sep
                        current_length += sep_length

            if current_message:
                yield current_message

        result = list(fit_parts("\n"))

        if not result:
            result = list(fit_parts(" "))

            if not result:
                result = []

                for i in range(int(ceil(message_length / MAX_LENGHT))):
                    result.append(message[i * MAX_LENGHT: (i + 1) * MAX_LENGHT])

                return result

        return result

    async def answer(self, message="", wait="no", **additional_values):
        "Send message to this message's sender (chat or user) with wait \
        settings `wait` and additional_values`additional_values` for \
        `messages.send`"

        if additional_values is None:
            additional_values = dict()

        sender = self.api.get_default_sender("messages.send")

        for k, v in additional_values.items():
            if k == "attachment":
                if isinstance(v, (list, tuple)):
                    v = ",".join(str(sv) for sv in v)
                elif not isinstance(v, str):
                    v = str(v)

                for sv in v.split(","):
                    if sv.startswith("sticker_"):
                        values = {"sticker_id": int(sv.replace("sticker_", "", 1)),
                                  **self.answer_values, **additional_values}
                        
                        values['random_id'] = randint(0, int(2e20))
                        
                        r = await self.api(sender=sender, wait=wait).messages.send(**values)

                        return [r]

        messages = self.prepare_message(str(message))
        messages_amount = len(messages)

        if "attachment" in additional_values:
            if isinstance(additional_values["attachment"], Attachment):
                attachment = str(additional_values["attachment"])

            elif isinstance(additional_values["attachment"], (list, tuple)):
                attachment = ""

                for a in additional_values["attachment"]:
                    if isinstance(a, Attachment):
                        attachment += str(a) + ","

                    elif isinstance(a, str):
                        attachment += a + ","

            else:
                attachment = additional_values["attachment"]

            del additional_values["attachment"]

        else:
            attachment = ""

        if not message and not attachment:
            raise AttributeError("No message or attachment")

        result = []

        for i, m in enumerate(messages):
            values = {'message': m, **self.answer_values, **additional_values}
            values['random_id'] = randint(0, int(2e20))
            
            if 'disable_mentions' not in values:
                values['disable_mentions'] = 1
                
            if i == 0:
                values["message"] = self.answer_values.get("before_message", "") + values["message"]

            if i == messages_amount - 1:
                values["message"] += self.answer_values.get("after_message", "")
                values["attachment"] = attachment

            r = await self.api(sender=sender, wait=wait).messages.send(**values)

            result.append(r)

        return result

    @staticmethod
    async def create(vk_api_object, data):
        msg = Message(vk_api_object, data)

        if data.full_message_data:
            await msg.get_full_data(data.full_message_data)

        return msg


class Chat:
    __slots__ = ("api", "id", "type", "title", "admin_id", "users", "photos", "_data")

    @staticmethod
    async def create(api, chat_id):
        data = await api.messages.getChat(chat_id=chat_id)

        photos = []

        for k, v in data.items():
            if k.startswith("photo_"):
                photos.append(v)

        return Chat(api, data["id"], data["type"], data["title"], data["admin_id"], data["users"], photos, _data=data)

    def __init__(self, api, _id, _type, _title, _admin_id, _users, _photos, _data=None):
        self.api = api
        self.id = _id
        self.type = _type
        self.title = _title
        self.users = _users
        self.admin_id = _admin_id

        self._data = _data

        self.photos = _photos


class Event:
    __slots__ = ("api", "type", "meta", "reserved_by")

    def __init__(self, api, evnt_type):
        self.api = api
        self.type = evnt_type

        self.meta = {}
        self.reserved_by = None


class ChatChangeEvent(Event):
    __slots__ = ("api", "msg", "action_type", "meta", "is_chat", "chat_id", "peer_id", "user_id")

    def __init__(self, api, msg):
        super().__init__(api, EventType.ChatChange)
        self.msg = msg
        self.action_type = msg.action.get("type")
        
        self.is_chat = msg.is_chat
        self.chat_id = msg.chat_id
        self.peer_id = msg.peer_id
        self.user_id = msg.user_id
        
