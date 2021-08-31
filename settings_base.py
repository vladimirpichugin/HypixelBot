# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

from plugins import *

class BaseSettings:
    USERS = ()
    PROXIES = ()

    SCOPE = 140489887
    APP_ID = 2274003
    
    DEBUG = False
    
    DEFAULTS["PREFIXES"] = DEFAULT_PREFIXES = ("", ".", "/", ",", "!", "-", "+", )
    DEFAULTS["PREFIXES_STRICT"] = False
    
    PLUGINS = ()
