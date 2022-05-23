# Hypixel Bot
Статистика в вашей беседе ВКонтакте.

[![Hypixel Bot Download](https://img.shields.io/badge/HypixelBot-download-blue.svg?logo=github&style=for-the-badge)](https://github.com/vladimirpichugin/HypixelBot/archive/master.zip)

[![Python](https://img.shields.io/badge/Python->%3D3.7-blue.svg?style=flat-square)](https://python.org)
[![pymongo](https://img.shields.io/badge/pymongo-3.7.1-green.svg?style=flat-square)](https://pypi.org/project/requests)
[![motor](https://img.shields.io/badge/motor-1.2-green.svg?style=flat-square)](https://pypi.org/project/motor)
[![requests](https://img.shields.io/badge/requests-2.20.0-red.svg?style=flat-square)](https://pypi.org/project/requests)
[![aiohttp](https://img.shields.io/badge/aiohttp-3.7.4-purple.svg?style=flat-square)](https://pypi.org/project/aiohttp)
[![aiofiles](https://img.shields.io/badge/aiofiles-0.5.0-purple.svg?style=flat-square)](https://pypi.org/project/aiofiles)
[![emoji](https://img.shields.io/badge/emoji-1.6.1-yellow.svg?style=flat-square)](https://pypi.org/project/emoji)
[![python-dateutil](https://img.shields.io/badge/dateutil-2.6.1-darkgreen.svg?style=flat-square)](https://pypi.org/project/python-dateutil)

[![Донат](https://img.shields.io/badge/Донат-Qiwi-orange.svg)](https://pichug.in/donate?project=hypixelbot) [![Официальная группа](https://img.shields.io/badge/Официальная-группа-lightblue.svg)](https://vk.com/hypixelbot)

***

## Для начала
> **Python 3.7**

Если есть какие-то ошибки при запуске, то первым делом выполнить команду для установки зависимостей
```shell
python -m pip install -r requirements.txt
```
**Пример конфигурации в файле** `settings_prod_example.py`

## Запуск
```shell
python runner.py
```

### Получение токена
[Получить токен](https://dev.vk.com/api/access-token/getting-started#%D0%9A%D0%BB%D1%8E%D1%87%20%D0%B4%D0%BE%D1%81%D1%82%D1%83%D0%BF%D0%B0%20%D1%81%D0%BE%D0%BE%D0%B1%D1%89%D0%B5%D1%81%D1%82%D0%B2%D0%B0)

## Вызов команд
Вы можете выбрать любой префикс `(` `.` `!` `/` `)` и указывать его перед каждой командой, например: «.профиль». Это обязательно.
Обозначения параметров команд

Параметры указываются без фигурных скобок.
* Параметры, указанные в _фигурных скобках_, например, так `{число}` — это настраиваемые значения;
* Параметры, указанные в _квадратных скобках_, например, так `[минута|час]` — выбор значения из предлагаемого списка;
* Параметры со значением `«{период}»` — это пара значений `{число [неделя|сутки|час|минута|секунда]}`, определяющая срок применения команды. `{число}` — необязательный параметр. Например: `«.мут 2 часа»`
* Параметр `{перенос строки}` — перенос строки.


## Синхронизация
> Чтобы функционал бота использовался на _100%_, нужно назначить бота администратором беседы, [подробнее](https://vk.com/@hypixelbot-setup-admin).

**Синхронизировать бота:** `.sync`

## Управление ботом
Управление ботом происходит через команду: `.ctrl`<br>
**Не рекомендуется предоставлять доступ к этой команде другим ролям, это может навредить вашей беседе.**

С помощью команды **Владелец** сможет управлять: `никами, ролями, правами, наградами, браками`

## Другие команды

* [Статистика на Hypixel](https://vk.com/@hypixelbot-hypixel)
* [Правила беседы](https://vk.com/@hypixelbot-commands?anchor=4-pravila-besedy)
* [Бан](https://vk.com/@hypixelbot-commands?anchor=5-ban)
* [Мут](https://vk.com/@hypixelbot-commands?anchor=6-mut)
* [Кик](https://vk.com/@hypixelbot-commands?anchor=7-kik)
* [Роли и права](https://vk.com/@hypixelbot-commands?anchor=8-roli-i-prava)
* [Профиль](https://vk.com/@hypixelbot-commands?anchor=9-profil)
* [Награды](https://vk.com/@hypixelbot-commands?anchor=10-nagrady)
* [Дуэли](https://vk.com/@hypixelbot-commands?anchor=11-dueli)
* [Браки](https://vk.com/@hypixelbot-commands?anchor=12-braki)
* [Ролевые игры](https://vk.com/@hypixelbot-commands?anchor=13-rolevye-igry)
* [Генератор цитат](https://vk.com/@hypixelbot-commands?anchor=14-tsitaty)
* [API Интеграция](https://vk.com/@hypixelbot-commands?anchor=15-api-integratsia)

***

[![Донат](https://img.shields.io/badge/Донат-Qiwi-orange.svg)](https://pichug.in/donate?project=hypixelbot) [![Официальная группа](https://img.shields.io/badge/Официальная-группа-lightblue.svg)](https://vk.com/hypixelbot)
