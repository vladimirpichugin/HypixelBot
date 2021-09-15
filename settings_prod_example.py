# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>


from plugins import *
from settings_base import BaseSettings

class BotSettings(BaseSettings):
    DEBUG = False
    
    USERS = (
        ("group", "token", ),
    )
    
    DEFAULTS["PREFIXES"] = DEFAULT_PREFIXES = (".", "/", ",", "!", "-", "+", )
    
    USER_AGENT = "HypeBot/1.0"
    API_URI = ""
    API_LICENSE_KEY = ""
    
    PLUGINS = (
        StoragePlugin(host="localhost", port=27017, database="hypebot", username="hypebot", password="password"),
        ControlPlugin("ctrl", "control", "контроль", "ктрл", required_role="owner", ),
        ChatMetaPlugin(),
        UserMetaPlugin(),
        StatisticsPlugin("статачата", "статабеседы", "стата чата", "статистика чата", "стата беседы", "статистика беседы", "топ беседы", "топбеседы", ),
        
        UsernamePlugin("nick", "ник", ),
        ProfilePlugin("profile", "профиль", "профайл",  "p", "п", "кто я", "кто это", ),

        BanPlugin("бан", "ban", "permban", "pban", "пермбан", "пбан", required_role="staff"),
        AutoKickPlugin(),
        MutePlugin("мут", "mute", "permmute", "pmute", "перммут", "пмут", required_role="staff"),
        MemberInvitePlugin(),
        BotInvitePlugin(),
        KickPlugin("кик", "kick", required_role="staff"),
        
        Quote("цитата", "цитировать", "цитатка", "ц", ),
  
        ContentMarriagesPlugin("брак", "развод", "браки"),
        ContentRolePlayingGamesPlugin(),
        ContentDuelsPlugin("дуэль"),
        
        RuGamingProfilePlugin("gmember", "участник", ),
        RuGamingBalancePlugin("balance", "баланс", "жуки", ),
        RuGamingRolePlugin("role", "роль", ),
        RuGamingGexpPlugin("gexp", "гехп", ),
        RuGamingGexpTopPlugin("gexptop", "gtop", "гехптоп", "гтоп", ),

        HypixelMAVPlugin("i", "mav", "мав", ),
        
        HypixelOnlinePlugin("w", "where", "online", "где", "онлайн", ),
        
        HypixelPlayerPlugin("игрок", "s", "stats", "info", "player", "статс", "стата", "с", "инфо", ),
        HypixelPlayerPlugin("sw", "св", "скайварс", "скайвар", game="SkyWars", ),
        HypixelPlayerPlugin("swr", "свр", "rsw", "рсв", game="SkyWarsRanked", ),
        HypixelPlayerPlugin("bw", "bedwars", "бв", "бедварс", game="BedWars", ),
        HypixelPlayerPlugin("duels", game="Duels", ),
        HypixelPlayerPlugin("sb", "skyblock", "сб", "скайблок", game="SkyBlock", ),
        HypixelPlayerPlugin("tnt", "tntgames", "тнт", game="TNTGames", ),
        HypixelPlayerPlugin("mm", "murder", "murdermystery", game="MurderMystery", ),
        HypixelPlayerPlugin("cvc", "копс", "cops", "crims", "copsandcrims", game="CAC", ),
        HypixelPlayerPlugin("mw", "walls", "megawalls", "мв", game="MegaWalls", ),
        HypixelPlayerPlugin("sg", "bsg", "blitz", "сг", "бсг", game="BSG", ),
        HypixelPlayerPlugin("cg", "classic", "классик", game="Classic", ),
        
        HypixelSBAuctionsPlugin("ah", "auction", "auctions", "аукцион", "аукционы", ),      
        
        HypixelPlayerCSPlugin("cs", "compare", "cr", "сравни", ),
        HypixelPlayerCSPlugin("cssw", "swcs", "swcr", "crsw", game="SkyWars", ),
        HypixelPlayerCSPlugin("csbw", "bwcs", "bwcr", "crbw", game="BedWars", ),
        
        HypixelGuildPlugin("гильдия", "guild", "g", ),

        SyncPlugin("sync", "синхронизировать", "синхронизация"),   
        HelpPlugin("help", ),        
        
        AntiFloodPlugin(),
        
        NoQueuePlugin(),
    )
