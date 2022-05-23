# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

import asyncio
import aiohttp
import json
import time
import traceback

from handler.base_plugin import CommandPlugin

from utils import upload_photo_by_file
from utils import create_report


class RuGamingGexpPlugin(CommandPlugin):
    __slots__ = ("description", "timeout", "api_command", "api_url", "api_headers", )
    
    def __init__(self, *commands, prefixes=None, strict=False, required_role=None, timeout=120, ):
        """RuGaming Member G-Exp"""
        self.description = ["RuGaming Member G-Exp"]
        
        self.timeout = timeout
        self.api_command = "rugaming_guild_gexp"
        
        super().__init__(*commands, prefixes=prefixes, strict=strict, required_role=required_role)   


    async def process_message(self, msg):
        if msg.peer_id != 2000000216:
            return
        
        self.api_headers = {
            "user-agent": self.bot.settings.USER_AGENT,
            "license-key": self.bot.settings.API_LICENSE_KEY
        }
        
        message = None
        err_code = 0
        
        args = msg.text.split(" ")

        args.pop(0)
        
        if msg.meta["payload_obj"]:
            if "uuid" in msg.meta["payload_obj"]:
                args = []
                if type(msg.meta["payload_obj"]["uuid"]) == str and len(msg.meta["payload_obj"]["uuid"]) > 0:
                    args = [str(msg.meta["payload_obj"]["uuid"])]


        if len(args) < 1:
            args.append(f'@id{msg.user_id}')

        cmd_args = " ".join(args)
        
        await msg.answer("&#128640; Загрузка G-Exp..")
        
        try:
            params = {
                "cmd": self.api_command,
                "args": cmd_args,
                "user_id": msg.user_id,
                "group_id": self.api.get_current_id(),
                "service": "vk",
                "fields[]": "data",
                "lang": "RUS",
                "v": 2
            }
            
            async with aiohttp.ClientSession() as sess:
                async with sess.post(self.bot.settings.API_URI, headers=self.api_headers, params=params, timeout=self.timeout) as resp:
                    http_status = resp.status
                    response = await resp.json()
            
            if http_status == 200:
                if response['ok'] == True:
                    message = str(response['response']['message'])
                    
                    ad_attachment = response['response'].get('vk', {}).get('attachment', '')
                    keyboard = response['response'].get('vk', {}).get('keyboard', None)
                    
                    attachments = ''
                    if 'media' in response['response']:
                        files = []
                        
                        t1 = time.time()
                        
                        for u in response['response']['media']['urls']:
                            files.append(u.replace('https://media.hypixelnetwork.ru/', '/var/www/media.hypixelnetwork.ru/'))
                        
                        attachments = await asyncio.gather(*[upload_photo_by_file(self.api, f, msg.peer_id) for f in files])
                        attachments = ",".join([str(a) for a in attachments])
                        
                        self.api.logger.debug(f"MEDIA {len(files)} files uploaded for {time.time()-t1} sec.")
                        
                        if ad_attachment:
                            attachments += ("," + ad_attachment)
                    
                    keyboard = json.dumps(keyboard) if keyboard else ''
                    
                    return await msg.answer(message, attachment=str(attachments), keyboard=keyboard)
                else:
                    if response['ok'] == False:
                        message = "&#128575; Произошла ошибка при обработке данных от вышестоящего API (6)."                        
                        err_code = 6
                        
                        if response and type(response) == dict and 'response' in response:
                            message = "&#128575; Произошла ошибка при обработке данных от вышестоящего API (7)."  
                            err_code = 7                            
                            
                            code = response['response'].get("code", None)
                            if code == -1000:
                                message = "&#10060; Бот отключен для проведения технического обслуживания, следите за новостями в сообществе [public194371480|Hypixel Статистика]."
                            elif code == -1001:
                                message = "&#10060; Команда отключена для проведения технического обслуживания."
                            elif code <= 0:
                                message = "&#128575; Произошла ошибка при обработке данных от вышестоящего API (8)."  
                                err_code = 8
                    else:
                        raise RuntimeError(f'Bad response json schema: response[ok] != False. Response: {response}')
            else:
                return await msg.answer("&#10060; Бот отключен для проведения технического обслуживания, следите за новостями в сообществе [public194371480|Hypixel Статистика].")
        except (aiohttp.client_exceptions.ContentTypeError, json.decoder.JSONDecodeError):
            self.api.logger.error(traceback.format_exc())
            message = "&#128575; Произошла ошибка при обработке данных от вышестоящего API (2, Malformed json)."
            err_code = 2
        except (aiohttp.client_exceptions.ClientConnectorError, aiohttp.client_exceptions.ServerDisconnectedError):
            self.api.logger.error(traceback.format_exc())
            message = "&#128575; Произошла ошибка при выполнении запроса к вышестоящему API (3, Соединение завершено).\n&#128073; Возможное решение: Попробуйте еще раз."
            err_code = 3
        except (ConnectionRefusedError, ConnectionError, ConnectionAbortedError, ConnectionResetError):
            self.api.logger.error(traceback.format_exc())
            message = "&#128575; Произошла ошибка при выполнении запроса к вышестоящему API (4, Соединение сброшено).\n&#128073; Возможное решение: Попробуйте еще раз."
            err_code = 4
        except (TimeoutError, asyncio.TimeoutError):
            self.api.logger.error(traceback.format_exc())
            message = "&#128575; Произошла ошибка при выполнении запроса к вышестоящему API (5, Время ожидания истекло).\n&#128073; Возможное решение: Попробуйте еще раз."
            err_code = 5
        except:
            self.api.logger.error(traceback.format_exc())
            message = "&#128575; Произошла ошибка. Мы искренне сожалеем о том, что вы столкнулись с такой ситуацией (-1)."
            err_code = -1
        
        if not message:
            message = "&#128575; Произошла ошибка. Мы искренне сожалеем о том, что вы столкнулись с такой ситуацией (-1)."
            err_code = -1
        
        keyboard = await create_report(err_code=err_code, plugin=self, msg=msg, return_keyboard=True)
        
        return await msg.answer(message, keyboard=keyboard)
