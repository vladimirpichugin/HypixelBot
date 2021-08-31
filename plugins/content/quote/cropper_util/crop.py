# coding: utf-8

import os
from PIL import Image, ImageDraw, ImageFont, ImageOps

def crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))

bg_orig = os.path.join(os.getcwd(), 'backgrounds')
bg_crop = os.path.join(os.getcwd(), 'cropped')

backgrounds = os.listdir(bg_orig)
backgrounds_cropped = os.listdir(bg_crop)

for bg in backgrounds:
    if bg not in backgrounds_cropped:
        im = Image.open(os.path.join(bg_orig, bg))
        im = crop_center(im, 500, 500)
        im.save(os.path.join(bg_crop, bg))
        
    
