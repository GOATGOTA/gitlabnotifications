import logging
from flask import Flask, redirect, url_for, request, render_template
from config import *
import requests
import os
import telebot
import psycopg2
import validators

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

def delete_row(chatid):
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
        return cursor.fetchone()



# Ответ на POST


def message(content):
    result = ''
    if content['object_kind'] == 'push':
        event = '<b>' + content['user_name'] + ' pushed to ' + content['project']['name'] + '</b>\n'
        branch = 'Related branch: ' + content['ref']
        if content['before'] == '0000000000000000000000000000000000000000':
            branch = branch + ' (<b>new</b>)'
        if content['after'] == '0000000000000000000000000000000000000000':
            branch = branch + ' (<b>removed</b>)'
        branch += '\n'
        pool = ''

        if len(content['commits']) != 0:
            pool += '\n' + '<b>' + str(len(content['commits'])) + '</b>' + ' Commit(s):\n'
            for elem in content['commits']:
                pool += '\n'
                pool += '<a href=\'' + elem['url'] + '\'><b>'+ elem['message'].replace('\n\n', '. ').replace('\n', '') + '</b></a>' + '\n'
                pool += 'added: ' + str(len(elem['added'])) + ' - updated: ' + str(len(elem['modified'])) + ' - removed: ' + str(len(elem['removed'])) + '\n'
        result = event + branch + pool
        return result
    
    if content['object_kind'] == 'issue':
        event = '<b>Issue by ' + content['user']['username'] + '</b>\n'
        if 'object_attributes' in content:
            label = ' '
            if len(content['object_attributes']['labels']) != 0:
                label = []
                for mark in content['object_attributes']['labels']:
                    label.append(mark['title'])
                label = ', '.join(label)
            if label != ' ':
                name = ' #' + str(content['object_attributes']['iid']) + ' ' + content['object_attributes']['title'] + ' (' +  label + ')'
            else:
                name = ' #' + str(content['object_attributes']['iid']) + ' ' + content['object_attributes']['title']
            if 'action' in content['object_attributes']:
                if content['object_attributes']['action'] == 'open':
                    event = '<b>' + content['user']['username'] + 'opened ' + '<a href=\'' + content['object_attributes']['url'] + '\'>issue</a> ' + name +  '</b>'
                if content['object_attributes']['action'] == 'close':
                    event = '<b>' + content['user']['username'] + 'closed ' + '<a href=\'' + content['object_attributes']['url'] + '\'>issue</a> ' + name +  '</b>'
                if content['object_attributes']['action'] == 'update':
                    event = '<b>' + content['user']['username'] + 'updated ' + '<a href=\'' + content['object_attributes']['url'] + '\'>issue</a> ' + name +  '</b>'
                if content['object_attributes']['action'] == 'reopen':
                    event = '<b>' + content['user']['username'] + 'reopened ' + '<a href=\'' + content['object_attributes']['url'] + '\'>issue</a> ' + name +  '</b>'
        return event
    if content['object_kind'] == 'note':
        event = '<b>' + content['user']['name'] + 'left comment in '
        number = ''
        name = content['object_attributes']['noteable_type'].lower()
        if content['object_attributes']['noteable_type'] == 'Issue':
            name += ' #' + str(content['issue']['iid'])
        if content['object_attributes']['noteable_type'] == 'MergeRequest':
            name += ' #' + str(content['issue']['iid'])
        event += '<a href=\'' + content['object_attributes']['url'] + '\'>' + name + '</a></b>\n'
        message = ''
        if 'note' in content['object_attributes']:
            message = '<b>' + content['user']['username'] + ':</b> ' + content['object_attributes']['note'] + '\n'
        result = event + message
        return result
    if content['object_kind'] == 'merge_request':
        event = '<a href=\'' + content['object_attributes']['url'] + '\'>merge request</a> ' + content['object_attributes']['source_branch'] + ' -> ' + content['object_attributes']['target_branch'] + ' by ' + content['user']['name'] + '</b>\n'
        description = '<b>' + content['user']['username'] + ':</b> ' + content['object_attributes']['description']
        
        if 'action' in content['object_attributes']:
            if content['object_attributes']['action'] == 'open':
                event = '<b>' + 'Opened ' + event
            if content['object_attributes']['action'] == 'close':
                event = '<b>' + 'Closed ' + event
            if content['object_attributes']['action'] == 'update':
                event = '<b>' + 'Updated ' + event
            if content['object_attributes']['action'] == 'reopen':
                event = '<b>' + 'Reopen ' + event
            if content['object_attributes']['action'] == 'approved':
                event = '<b>' + 'Approved ' + event
            if content['object_attributes']['action'] == 'unapproved':
                event = '<b>' + 'Unapproved ' + event
            if content['object_attributes']['action'] == 'merge':
                event = '<b>' + 'Merged ' + event
        else:
            event = '<b>' + event
        result = event + description
        return result

    return ''


# Endpoints


@bot.message_handler(commands=["start"])
def start(message):
    username = message.from_user.username
    bot.reply_to(message, f"Hello, {username}!\nTo add GitLab repository notifications send command /add")

@bot.message_handler(commands=["add"])
def add(message):
    global answer
    bot.reply_to(message, f"Enter your HTTPS repository which ends with .git" )
    answer = True

@bot.message_handler(commands=["delete"])
def delete(message):
    delete_row(str(message.chat.id))
    bot.send_message(message.chat.id,"Notifications have been discontinued")

@bot.message_handler(content_types="text")
def message_reply(message):
    global answer
    if answer == True:
        if ".git" in message.text and "https" in message.text:
            count = check(message.text)
            answer = False
            if count == 0:
                insert(message.text, message.chat.id)
                bot.send_message(message.chat.id,"Your repository was successfully linked\nWeebhook url: https://gitlabnotifications.herokuapp.com/gitlab\nTo stop notifications send command /delete")
            if count == 1:
                update(message.text, message.chat.id)
                bot.send_message(message.chat.id,"Your repository was successfully updated\nWeebhook url: https://gitlabnotifications.herokuapp.com/gitlab\nTo stop notifications send command /delete")
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
    chat = chat_search(content['project']['git_http_url'])
    if chat != None:
        bot.send_message(chat[0], message(content), parse_mode="HTML")
    return content


if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=APP_URL)
    server.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
