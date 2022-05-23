# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

import os
import aiohttp, io
import datetime, io
from PIL import Image, ImageDraw, ImageFont, ImageOps

from handler.base_plugin import CommandPlugin

from utils import upload_photo
from utils import traverse, replace_mentions_from_text, remove_emoji


class Quote(CommandPlugin):
    __slots__ = ("description", "q", "qf", "f", "fs", "fss", )

    def __init__(self, *commands, prefixes=None, strict=False, required_role=None, ):
        """Answers with image containing stylish quote."""
        self.description = ["Генератор цитат"]

        super().__init__(*commands, prefixes=prefixes, strict=strict, required_role=required_role)

        self.q = Image.open(self.get_path("q.png")).resize((40, 40), Image.LANCZOS)
        self.q = self.q.convert('RGBA')
        self.qf = self.q.copy().transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)

        self.f = ImageFont.truetype(self.get_path("font.ttf"), 24)
        self.fs = ImageFont.truetype(self.get_path("font.ttf"), 16)
        self.fss = ImageFont.truetype(self.get_path("font.ttf"), 15)

    
    async def process_message(self, msg):
        settings = {
            'size': (700, 450, ),
            'text_color': (255, 255, 255, ),
            #'background_image': 'https://pp.userapi.com/c851236/v851236234/68144/t6TVwOwuXho.jpg'
        }
        clients_settings = {
            423920738: {
                'name': 'Vladimir Pichugin',
                'crop': {"x": 4.27, "y": 0, "x2": 95.59, "y2": 100}
            }
        }
        
        if not msg.fwd_messages and not msg.reply_message:
            return await msg.answer("&#127856; Перешлите мне сообщение, из которого нужно создать цитату.")
    
        quote_owner_id, text, sticker_url = None, "", None
        for m in traverse(msg.reply_message if msg.reply_message else await msg.get_full_forwarded()):
            if m.full_text or m.full_message_data["attachments"]:
                if quote_owner_id:
                    if quote_owner_id != m.from_id:
                        continue
                else:
                    quote_owner_id = m.from_id
                
                if m.full_message_data["attachments"] and not text:
                    if m.full_message_data["attachments"][0]["type"] == "sticker":
                        stickers = m.full_message_data["attachments"][0]["sticker"]["images"]
                        sticker_url = stickers[-2:][0]["url"]
                
                if m.full_text:
                    text += "\n" + m.full_text
                
                timestamp = datetime.datetime.fromtimestamp(m.timestamp).strftime('%d.%m.%Y')                
        
        if not text and not sticker_url:
            return await msg.answer("&#127856; Не найден текст для создания цитаты.")
        
        client = None
        avatar_image = None
        
        avatars_clients = self.get_path('/avatars_clients')
        if os.path.isdir(avatars_clients):
            clients_images = {int(_.split('.')[0]): _ for _ in os.listdir(avatars_clients)}
            if quote_owner_id in clients_images:
                avatar_image = Image.open(self.get_path(f'/avatars_clients/{clients_images[quote_owner_id]}'))
    
        avatar_crop = {'x': 0, 'y': 0, 'x2': 100, 'y2': 100}        
        if quote_owner_id in clients_settings:
            client = clients_settings[quote_owner_id]
            avatar_crop = client["crop"]

        if not client:
            if quote_owner_id > 0:
                client = await self.api.users.get(user_ids=quote_owner_id, fields="photo_max")
            else:
                client = await self.api.groups.getById(group_ids=abs(quote_owner_id), fields="photo_max")
            client = client[0]
            
            if "deactivated" in client:
                avatar_image = Image.open(self.get_path(f'/avatars_default/deactivated_200.png'))
            else:
                if "photo_max" in client:
                    async with aiohttp.ClientSession() as sess:
                        async with sess.get(client["photo_max"]) as response:
                            avatar_image = Image.open(io.BytesIO(await response.read()))

        if not avatar_image:
            avatar_image = Image.open(self.get_path(f'/avatars_default/camera_200.png'))
                    
        name = []
        if "first_name" in client:
            name.append(client["first_name"])
            if "last_name" in client: name.append(client["last_name"])
        else:
            name.append(client["name"] if "name" in client else "Неизвестный персонаж")

        sticker_image = None
        if sticker_url:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(sticker_url) as response:
                    sticker_image = Image.open(io.BytesIO(await response.read()))
                    sticker_image = sticker_image.convert('RGBA')
        
        if "background_image" in settings and settings["background_image"]:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(settings["background_image"]) as response:
                    settings["background_image"] = Image.open(io.BytesIO(await response.read())).convert('RGBA')
        else:
            settings["background_image"] = Image.open(self.get_path(f'/backgrounds/dark.jpg')).convert('RGBA')
            
        if text:
            text = await remove_emoji(text)
            text = await replace_mentions_from_text(text)
                        
        make_image_result = await self.run_in_executor(self.make_image, text, avatar_image, avatar_crop, sticker_image, name, timestamp, settings)
        try:
            attachment = await upload_photo(self.api, make_image_result)
            return await msg.answer(attachment=str(attachment))
        except:
            await msg.answer("При загрузке картинки готовой цитаты произошла ошибка, попробуйте позже.")
            raise

    def make_image(self, text, avatar_image, avatar_crop, sticker_image, name, timestamp, settings=None):
        rsize = (700, 450)
        text_color = (255, 255, 255)
        background_color = (0, 0, 0)
        background_image = None
        
        if settings:
            if "size" in settings:
                rsize = settings["size"]
            if "text_color" in settings:
                text_color = settings["text_color"]
            if "background_color" in settings:
                background_color = settings["background_color"]
            if "background_image" in settings:
                background_image = settings["background_image"]

        if background_image:
            res = background_image
            res = res.resize(rsize, Image.NEAREST)
        else:
            res = Image.new("RGBA", rsize, color=(background_color[0], background_color[1], background_color[2]))

        if sticker_image:
            res.paste(sticker_image, (280, 60), mask=sticker_image)
        
        if avatar_image:
            im = avatar_image
            
            width, height = im.width, im.height
            
            val = lambda t, x: (t / 100) * x
            
            def crop_center(pil_img, crop_width, crop_height):
                img_width, img_height = pil_img.size
                return pil_img.crop(((img_width - crop_width) // 2,
                                     (img_height - crop_height) // 2,
                                     (img_width + crop_width) // 2,
                                     (img_height + crop_height) // 2))
            
            crop_width = im.width - val(im.width, avatar_crop["x"])
            crop_height = im.height - val(im.height, avatar_crop["y"])
            im = crop_center(im, crop_width, crop_height)
            
            width, height = 200, 200
            
            indent = 0
            mask = Image.new("L", (width, height), 1)
            draw = ImageDraw.Draw(mask)
            
            x0, y0 = indent, indent
            x1, y1 = width-x0, height-y0
            
            draw.ellipse((x0, y0, x1, y1), fill=255)
            del draw
            output = ImageOps.fit(im, (width, height), centering=(0.1, 0.1))
            output.putalpha(mask)
            res.paste(output, (25, 125), mask=mask)
                
        tex = Image.new("RGBA", rsize, color=(background_color[0], background_color[1], background_color[2]))
        draw = ImageDraw.Draw(tex)
        
        width, height = 0, 0
        
        if len(text) > 70:
            font = self.fss
        else:
            font = self.f

        sidth = int(draw.textsize(" ", font=font)[0])
        
        new_text = ""
        for line in text.splitlines():
            for word in line.split():
                word_width = len(word) * sidth

                if width + word_width >= rsize[0] - 340:
                    width = 0
                    new_text += "\n"

                width += sidth + word_width
                new_text += word + " "

            width = 0
            new_text += "\n"
        
        new_text = new_text[:-1]

        width, height = draw.multiline_textsize(new_text, font=font)
        draw = ImageDraw.Draw(res)
        
        y = rsize[1] // 2 - height // 2
        x = 300 + (rsize[0] - 370 - width) // 2

        draw.multiline_text((x, y), new_text, font=font, fill=text_color)
        
        if height < 210:
            height = 210
            y = rsize[1] // 2 - height // 2

        res.paste(self.q, (240, y), mask=self.q)
        res.paste(self.qf, (rsize[0] - 65, y + height - 40), mask=self.qf)
        
        draw.multiline_text((25, rsize[1]-75), f"© {' '.join(name)}", font=self.fs, fill=text_color)
        draw.multiline_text((25, rsize[1]-55), f"@ {timestamp}", font=self.fs, fill=text_color)
        draw.multiline_text((25, rsize[1]-25), "vk.com/hypixelbot", font=self.fss, fill=text_color)
            
        buff = io.BytesIO()
        res.save(buff, format='png')
        
        return buff.getvalue()
