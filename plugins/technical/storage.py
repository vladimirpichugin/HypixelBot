# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

from handler.base_plugin import BasePlugin

import time, datetime
import motor.motor_asyncio


class sdict(dict):
    """Dictionary with field `changed`. `changed` is True when any element was
    accessed."""

    def __init__(self, *args, **kwargs):
        self.changed = False
        super().__init__(*args, **kwargs)

    def __getitem__(self, item):
        self.changed = True
        return super().__getitem__(item)

    def __setitem__(self, item, value):
        self.changed = True
        return super().__setitem__(item, value)

    def __delitem__(self, item):
        self.changed = True
        super().__delitem__(item)

    def getraw(self, item, default=None):
        try:
            return super().__getitem__(item)
        except KeyError:
            return default

    def setraw(self, item, value):
        super().__setitem__(item, value)

    def delraw(self, item):
        super().__delitem__(item)


class StoragePlugin(BasePlugin):
    __slots__ = ("client", "database", "users", "chats", "bot_stats", "users_plus",
        "meta", "cached_meta",
    )

    def __init__(self, host="localhost", port=27017, database="hypebot", username=None, password=None):
        """Allows users and chats to store persistent data with MongoDB or in
        memory. Both storages are siuated in `meta` as `data_user` and
        `data_chat` and represented as dictionary with possible basic values
        (dict, list, tuple, int, float, str, bool). On the beggining theese
        fields are populated and after message processing it is saved to
        database.

        Data is saved only if was acessed. You can use `sdict`'s methods and
        field `changed` for accessing data without saving it."""

        super().__init__()

        self.order = (-100, 100)

        self.client = motor.motor_asyncio.AsyncIOMotorClient(host, port, username=username, password=password)

        self.database = self.client[database]

        self.users = self.database["users"]
        self.chats = self.database["chats"]
        self.meta = self.database["meta"]
        self.bot_stats = self.database["stats"]
        self.users_plus = self.client["plus"]["clients"]

        self.cached_meta = None

    async def _save(self, xid, d, x):
        if isinstance(xid, str):
            xid = int(xid)

        if xid == 0 or not d or not d.changed:
            return None

        if "id" not in d:
            d["id"] = xid

        if "_id" not in d:
            return await x.insert_one(d)

        old_ver = d["_version"]
        d["_version"] += 1

        res = await x.replace_one({"_id": {"$eq": d["_id"]},
            "_version": {"$eq": old_ver}}, d)

        if res.modified_count == 0:
            return False

        return True

    async def save_user(self, user_id, data):
        #self.api.logger.debug(f"save_user: {user_id}, {data}")
        return await self._save(user_id, data, self.users)

    async def save_chat(self, peer_id, data):
        #self.api.logger.debug(f"save_chat: {peer_id}, {data}")
        
        # todo
        
        return await self._save(peer_id, data, self.chats)
    
    async def save_bot_stats(self, data):
        #self.api.logger.debug(f"save_bot_stats: {data}")
        return await self._save(int(datetime.datetime.today().strftime("%m%Y")), data, self.bot_stats)

    async def _load(self, xid, x, xid_key="id"):
        if isinstance(xid, str):
            xid = int(xid)

        if xid == 0:
            return None

        return sdict(await x.find_one({xid_key: {"$eq": xid}}) or
            {xid_key: xid, "_version": 0})

    async def load_user(self, user_id):
        #self.api.logger.debug(f"load_user: {user_id}")
        return await self._load(user_id, self.users)

    async def load_chat(self, peer_id):
        #self.api.logger.debug(f"load_chat: {peer_id}")
        return await self._load(peer_id, self.chats)

    async def load_meta(self, segment="main"):
        #self.api.logger.debug(f"segment: {segment}")
        if self.cached_meta:
            self.cached_meta.changed = False
            return self.cached_meta

        self.cached_meta = sdict(await self.meta.find_one({"_name": {"$eq": segment}}) or
            {"_name": segment, "_version": 0})

        self.cached_meta.show = True

        return self.cached_meta
    
    async def load_bot_stats(self):
        #self.api.logger.debug(f"load_bot_stats")
        return await self._load(int(datetime.datetime.today().strftime("%m%Y")), self.bot_stats)
        
    async def load_user_plus(self, from_id):
        #self.api.logger.debug(f"load_user_plus: {from_id}")
        return await self._load(from_id, self.users_plus, "_id")

    async def save_meta(self, d, segment="main"):
        if not d or not d.changed:
            return

        self.cached_meta = None

        if "_id" not in d:
            return await self.meta.insert_one(d)

        old_ver = d["_version"]
        d["_version"] += 1

        res = await self.meta.replace_one({"_name": {"$eq": segment},
            "_version": {"$eq": old_ver}}, d)

        if res.modified_count == 0:
            return False

        return True

    def prepare_ctrl(self, entity):
        async def _1l():
            return await self.load_meta()
        async def _1s(d):
            return await self.save_meta(d)

        if hasattr(entity, "user_id") and entity.user_id > 0:
            async def _3l():
                return await self.load_user(entity.user_id)

            async def _3s(d):
                return await self.save_user(entity.user_id, d)
        else:
            _3l = None
            _3s = None

        if hasattr(entity, "peer_id"):
            async def _2l():
                return await self.load_chat(entity.peer_id)

            async def _2s(d):
                return await self.save_chat(entity.peer_id, d)
        else:
            _2l = None
            _2s = None
        
        async def _4l():
            return await self.load_bot_stats()
        
        async def _4s(d):
            return await self.save_bot_stats(d)
        
        if hasattr(entity, "from_id") and entity.user_id > 0:
            async def _5l():
                return await self.load_user_plus(entity.from_id)
        else:
            _5l = None

        return {
            "load_meta": _1l,
            "save_meta": _1s,
            "load_chat": _2l,
            "save_chat": _2s,
            "load_user": _3l,
            "save_user": _3s,
            "load_bot_stats": _4l,
            "save_bot_stats": _4s,
            "load_user_plus": _5l
        }

    async def global_before_message_checks(self, msg):
        msg.meta["mongodb_client"] = self.client

        msg.meta["data_ctrl"] = self.prepare_ctrl(msg)

        msg.meta["data_meta"] = await self.load_meta()
        msg.meta["data_user"] = await self.load_user(msg.user_id)
        msg.meta["data_chat"] = await self.load_chat(msg.peer_id) if \
            msg.is_chat else None
        msg.meta["data_user_plus"] = await self.load_user_plus(msg.from_id)

    async def global_before_event_checks(self, evnt):
        evnt.meta["mongodb_client"] = self.client

        evnt.meta["data_ctrl"] = self.prepare_ctrl(evnt)
        
        evnt.meta["data_meta"] = await self.load_meta()
        
        if evnt.msg.is_chat:
            evnt.meta["data_chat"] = await self.load_chat(evnt.peer_id)
            evnt.meta["data_user"] = None
        else:
            evnt.meta["data_chat"] = None
            evnt.meta["data_user"] = await self.load_user(evnt.user_id)

    async def save_target_meta(self, entity):
        ctrl = entity.meta["data_ctrl"]
        
        if ctrl["save_meta"]:
            await ctrl["save_meta"](entity.meta["data_meta"])

        if ctrl["save_user"]:
            await ctrl["save_user"](entity.meta["data_user"])
        
        if ctrl["save_chat"] and entity.meta["data_chat"]:
            await ctrl["save_chat"](entity.meta["data_chat"])

    async def global_after_message(self, msg, plugin, result):
        ctrl = msg.meta["data_ctrl"]
        
        data = await ctrl["load_bot_stats"]()
        
        if data == None:
            data = {}
        
        if "plugins" not in data:
            data["plugins"] = {}
        plugins = data["plugins"]
        
        if plugin.name not in plugins:
            plugins[plugin.name] = {"history": []}
            
        obj = {}
        
        obj["timestamp"] = int(time.time())
        
        obj["message"] = {
            "peer_id": msg.peer_id,
            "from_id": msg.from_id,
            "full_text": msg.full_text,
            "payload": msg.payload,
            "timestamp": int(msg.date)
        }
        
        if hasattr(plugin, "game"):
            obj["plugin_info"] = {"game": plugin.game}
        
        plugins[plugin.name]["history"].append(obj)
        
        await ctrl["save_bot_stats"](data)
            
    async def global_after_message_process(self, msg, result):
        await self.save_target_meta(msg)

    async def global_after_event_process(self, evnt, result):
        await self.save_target_meta(evnt)
