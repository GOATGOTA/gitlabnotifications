import logging
from flask import Flask, redirect, url_for, request, render_template
from config import *
import requests
import logger
import json
import os
import telebot

bot = telebot.TeleBot(BOT_TOKEN)
server = Flask(__name__)
logger = telebot.logger
logger.setLevel(logging.DEBUG)


def send_telegram(text: str, chatid: str ):
    global token
    token = token
    url = "https://api.telegram.org/bot"
    channel_id = chatid
    url += token
    method = url + "/sendMessage"
    if channel_id != None:
        r = requests.post(method, data={
             "chat_id": channel_id,
             "text": text,
             "parse_mode" : "HTML"
        })

        if r.status_code != 200:
            raise Exception("post_text error")


# Создание базы данных



# Взаимодействия с базой данных




# Ответ на POST


def message(content):
    result = ''
    if content['object_kind'] == 'push':
        event = '🔥<b>Push в ' + content['project']['name'] + ' от ' + content['user_username'] + '</b>🔥\n'
        user = '👶Пользователь: ' + content['user_name'] + '\n'
        branch = '🌿Ветка: ' + '<b>' + content['ref'] + '</b>\n'
        if content['before'] == '0000000000000000000000000000000000000000':
            branch = '➕' + branch
        if content['after'] == '0000000000000000000000000000000000000000':
            branch = '➖' + branch
        pool = ''
        
        if len(content['commits']) != 0:
            pool += '\n' + '<b>' + str(len(content['commits'])) + '</b>' + ' Commit(s):\n'
            for elem in content['commits']:
                pool += '\n'
                pool += '🔗Ссылка: ' + '<a href=\'' + elem['url'] + '\'><b>тык</b></a>' + '\n' + '✉️Сообщение: ' + elem['message'].replace('\n\n', '. ').replace('\n', '') + '\n'
                pool += '🟢Добавлено: ' + str(len(elem['added'])) + ' - 🟡Изменено: ' + str(len(elem['modified'])) + ' - 🔴Удалено: ' + str(len(elem['removed'])) + '\n'
        result = event + user + branch + pool
        return result
    if content['object_kind'] == 'issue':
        event = '⚠️<b>Issue в ' + content['project']['name'] + ' от ' + content['user']['username'] + '</b>⚠️\n\n'
        pool = ''
        if 'object_attributes' in content:
            label = ' '
            if len(content['object_attributes']['labels']) != 0:    
                for mark in content['object_attributes']['labels']:
                    label += '#'                        
                    label += mark['title'] + ' '
            name = '📢Issue: ' + '<b>№' + str(content['object_attributes']['iid']) + ' ' + content['object_attributes']['title'] + '</b>' + label + '\n'
            url = '🔗Ссылка: ' + '<a href=\'' + content['object_attributes']['url'] + '\'><b>тык</b></a>'
            status = '📊Статус: Unknown🤨\n'
            if 'action' in content['object_attributes']:
                if content['object_attributes']['action'] == 'open':
                    status = '📊Статус: Открыт📖\n'
                if content['object_attributes']['action'] == 'close':
                    status = '📊Статус: Закрыт📕\n'
                if content['object_attributes']['action'] == 'update':
                    status = '📊Статус: Обновлён♻️\n'
                if content['object_attributes']['action'] == 'reopen':
                    status = '📊Статус: Переоткрыт🔄\n'
            pool += name + status + url + '\n'
        result = event + pool
        return result
    if content['object_kind'] == 'note':
        event = '📩<b>Комментарий в ' + content['project']['name'] +  ' от ' + content['user']['username'] + '</b>📩\n'
        number = ''
        if content['object_attributes']['noteable_type'] == 'Issue':
            number = ' #' + str(content['issue']['iid'])
        if content['object_attributes']['noteable_type'] == 'MergeRequest':
            number = ' #' + str(content['merge_request']['iid'])
        theme = '\nТема: ' + '<b>' + content['object_attributes']['noteable_type'] + number + '</b>\n'
        url = '🔗Ссылка: ' + '<a href=\'' + content['object_attributes']['url'] + '\'><b>тык</b></a>'
        message = ''
        if 'note' in content['object_attributes']:
            message = 'Комментарий: ' + content['object_attributes']['note'] + '\n'
        result = event + theme + message + url
        return result
    if content['object_kind'] == 'merge_request':
        event = '⛑<b>Merge Request в ' + content['project']['name'] + ' от ' + content['user']['username'] + '</b>⛑\n'
        from_to = '🌿Ветка: ' + '<b>' + content['object_attributes']['source_branch'] + ' -> ' + content['object_attributes']['target_branch'] + '</b>\n\n'
        description = 'Описание: ' + content['object_attributes']['description'] + '\n'
        url = '🔗Ссылка: ' + '<a href=\'' + content['object_attributes']['url'] + '\'><b>тык</b></a>' + '\n'
        status = ''
        if 'action' in content['object_attributes']:
            if content['object_attributes']['action'] == 'open':
                status = '📊Статус: Открыт📖\n'
            if content['object_attributes']['action'] == 'close':
                status = '📊Статус: Закрыт📕\n'
            if content['object_attributes']['action'] == 'update':
                status = '📊Статус: Обновлён♻️\n'
            if content['object_attributes']['action'] == 'reopen':
                status = '📊Статус: Переоткрыт🔄\n'
            if content['object_attributes']['action'] == 'approved':
                status = '📊Статус: Подтверждён🆗\n'
            if content['object_attributes']['action'] == 'unapproved':
                status = '📊Статус: Отказан🙅‍♂️\n'
            if content['object_attributes']['action'] == 'merge':
                status = '📊Статус: Поглощён😋\n'
        result = event + from_to + description + status + url
        return result

    return ''


# Endpoints


# @server.route('/tg', methods = ['POST'])
# def tg_webhook():
#     content = request.get_json()
#     if 'message' in content:
#         if content['message']['text'] == '/start':
#             text = 'Привет, это бот уведомлений GitLab. Давай познакомимся с моим функционалом:\n/add git_http_url - привязка уведомлений к этому чату;\n/update git_http_url - перепривязка уведомлений к этому чату;\n/remove git_http_url - прекращение уведомлений;'
#             send_telegram(text, content['message']['chat']['id']) 

#         if content['message']['text'].split(' ')[0] == '/add' and '.git' in content['message']['text']:
#             add_git(content['message']['text'].split(' ')[1], content['message']['chat']['id'])

#         if content['message']['text'].split(' ')[0] == '/update' and '.git' in content['message']['text']:
#             update_git(content['message']['text'].split(' ')[1], content['message']['chat']['id'])

#         if content['message']['text'].split(' ')[0] == '/remove' and '.git' in content['message']['text']:
#             remove_git(content['message']['text'].split(' ')[1], content['message']['chat']['id'])

#     return content


@bot.message_handler(commands=["start"])
def start(message):
    username = message.from_user.username
    bot.reply_to(message, f"Hello, {username}!\n Напиши")

@server.route(f"/{BOT_TOKEN}", methods = ["POST"])
def redirect_message():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200


# @server.route('/gitlab', methods=['POST'])
# def add_message_back():
#     content = request.get_json()
#     send_telegram(message(content), chat_search(content['project']['git_http_url']))
#     return content



if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=APP_URL)
    server.run()