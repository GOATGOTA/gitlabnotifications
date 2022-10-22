import logging
from flask import Flask, redirect, url_for, request, render_template
from config import *
import requests
import os
import telebot
import psycopg2

bot = telebot.TeleBot(BOT_TOKEN)
server = Flask(__name__)
logger = telebot.logger
logger.setLevel(logging.DEBUG)

try:
    connection = psycopg2.connect(host=host,user=user,password=password,database=db_name)

except Exception as _ex:
    print('Error')

def init_table():
    init = """
    CREATE TABLE IF NOT EXISTS public.gits (git varchar(128), chat_id varchar(64));"""
    with connection.cursor() as cursor:
        cursor.execute(init)
    connection.commit()

def check(git):
    init = '''
    SELECT COUNT(*) FROM public.gits WHERE git = %s;'''
    with connection.cursor() as cursor:
        cursor.execute(init,(git,))
        return cursor.fetchone()[0]

def insert(git, chatid):
    init = '''
    INSERT INTO public.gits (git, chat_id) VALUES (%s,%s)'''
    with connection.cursor() as cursor:
        cursor.execute(init,(git, chatid))
    connection.commit()

def update(git, chatid):
    init = '''
    UPDATE public.gits SET chat_id = %s WHERE git = %s;'''
    with connection.cursor() as cursor:
        cursor.execute(init,(chatid, git))
    connection.commit()

def delete(chatid):
    init = '''
    DELETE FROM public.gits WHERE chat_id = %s;'''
    with connection.cursor() as cursor:
        cursor.execute(init,(chatid,))
    connection.commit()

def chat_search(git):
    init = '''
    SELECT chat_id FROM public.gits WHERE git = %s;'''
    with connection.cursor() as cursor:
        cursor.execute(init,(git,))
        return cursor.fetchone()[0]



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


@bot.message_handler(commands=["start"])
def start(message):
    username = message.from_user.username
    bot.reply_to(message, f"Hello, {username}!\nTo add GitLab repository notifications send command /add")

@bot.message_handler(commands=["add"])
def add(message):
    bot.reply_to(message, f"Enter your HTTPS repository which ends with .git" )

@bot.message_handler(commands=["delete"])
def delete(message):
    delete(message.chat.id)
    bot.send_message(message.chat.id,"Notifications have been discontinued")

@bot.message_handler(content_types="text")
def message_reply(message):
    if ".git" in message.text and "https" in message.text:
        count = check(message.text)
        if count == 0:
            insert(message.text, message.chat.id)
            bot.send_message(message.chat.id,"Your repository was successfully linked\nTo stop notifications send command /delete")
        if count == 1:
            update(message.text, message.chat.id)
            bot.send_message(message.chat.id,"Your repository was successfully updated\nTo stop notifications send command /delete")
    else:
        bot.send_message(message.chat.id,"Incorrect repository HTTPS")


@server.route(f"/{BOT_TOKEN}", methods = ["POST"])
def redirect_message():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200


@server.route('/gitlab', methods=['POST'])
def add_message_back():
    content = request.get_json()
    bot.send_message(chat_search(content['project']['git_http_url']), message(content), parse_mode="HTML")



if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=APP_URL)
    server.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
