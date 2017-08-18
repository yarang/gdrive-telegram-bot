#!/usr/bin/python
#-*- coding: utf-8 -*-
from __future__ import print_function
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, RegexHandler
from telegram import ReplyKeyboardMarkup
import telegram 

from subprocess import PIPE, STDOUT, Popen, check_output
import shlex
import logging

from functools import wraps

import httplib2
import os
import io

from googleapiclient.http import *
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import psycopg2
from psycopg2.extras import RealDictCursor
import json

import pycurl
from datetime import datetime

from psql_interface import *

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Drive API Python Quickstart'
TELEGRAM_MY_ID = 53971422

proc = None
valid = False
credentials = None
chat_info = None
filelist = {}
service = None
FILESTORAGE = "files/"
contents = None

with open('psql.json', 'rw') as psql_file:
    jsonpsql = json.load(psql_file)

conn = psycopg2.connect("host=" + jsonpsql["host"] + " dbname=" + jsonpsql['dbname'] + " user=" + jsonpsql['user']+" password=" + jsonpsql['password'])
cursor = conn.cursor(cursor_factory=RealDictCursor)

logging.basicConfig(filename='bot.log', level=logging.DEBUG)

#google_keyboard = [['USE','ADD']]
#markup = ReplyKeyboardMarkup(google_keyboard, one_time_keyboard=True)
CHOOSING, ACCOUNTING, DONE = range(3)

telegram_info = get_telegram_info(cursor, TELEGRAM_MY_ID)
google_info = get_google_info(cursor, TELEGRAM_MY_ID)

def http_body_callback(buf):
    global contents;
    contents = buf;

def get_credential_info(service_name, user_name, user_id):
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    file_name = str(service_name)+"-"+str(user_name)+"-"+str(user_id)+".json"
    print(file_name)
    credential_path = os.path.join(credential_dir, file_name)
    print(credential_path)
    
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def restricted(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        if not valid:
            print("Unauthorized access denied for {}.".format(TELEGRAM_MY_ID))
            return
        return func(bot, update, *args, **kwargs)
    return wrapped

def start(bot, update):
    global valid
    chat_info = get_user_info(cursor, update.message.from_user.id)
    if(chat_info is not None and chat_info['permission'] == 'valid'):
        valid = True
    if(valid):
        update.message.reply_text('Hello World!')
    else:
        update.message.reply_text('Sorry!')
    return

def hello(bot, update):
    update.message.reply_text(
        'Hello {}'.format(update.message.from_user.first_name))
    return

def commander(bot, update, args):
    global valid
    if(valid):
        bot.sendMessage(chat_id=update.message.chat_id, text="Call commander")
        cmd_text = ' '.join(args)
        print(cmd_text)
        result = check_output(cmd_text, shell=True)
        bot.sendMessage(chat_id=update.message.chat_id, text=result)
    else:
        update.message.reply_text("Can't identify user.")
    return

@restricted
def on_chat_message(bot, update):
    chat_id = update.message.chat_id
    user = update.message.from_user
    user_name = "%s%s" % (user.last_name, user.first_name)
    bot.sendMessage(chat_id, text=("%s say " + update.message.text) % user_name)

def google(bot, update):
    global google_info
    # 사용자 정보가 있는지 확인.
    logging.debug(str(google_info))
    if(google_info is not None and google_info['service_id']):
        update.message.reply_text("Check your account : " + google_info['service_id'])
        return CHOOSING
    else:
        update.message.reply_text("Add your account")
        return ACCOUNTING

def add_account(bot, update):
    # 이전 사용자 정보가 있는 경우 
    # 이전 사용자 정보가 없는 경우
    update.message.reply_text("Add your account")
    return ACCOUNTING

def use_account(bot, update):
    global google_info
    # 현재 사용자 그대로 사용
    text = google_info['service_id']
    update.message.reply_text('Your account name: %s' % text.lower())
    return DONE

def input_account(bot, update, user_data):
    global google_info
    # 새로운 사용자 정보 받기
    text = update.message.text
    if (google_info is None): google_info = {}
    google_info['service_id'] = text
    update.message.reply_text('Input account name: %s' % text.lower())
    return DONE

def done(bot, update, user_data):
    global google_info
    # 이전 사용자가 있으면 selected를 false로 바꾸어야 한다.
    # 이전 사용자가 없으면 selected를 선택할 필요가 없다.
    # 사용할 사용자에 대한 selected만 있으면 된다.
    # 사용자 정보가 없으면 추가한다.
    found = False
    query = "update services set selected='false' where service_name='google' and id=" + str(update.message.from_user.id)
    cursor.execute(query)
    conn.commit()
    query = "select * from services where service_name='google' and id=" + str(update.message.from_user.id)
    cursor.execute(query)
    conn.commit()
    res = cursor.fetchall()
    logging.debug("res: " + str(res))
    logging.debug("google: " + str(google_info))
    for item in res:
        if(item['service_id'] == google_info['service_id']):
            found = True
    if(found == True):
        query = "update services set selected=True where id=" + str(TELEGRAM_MY_ID) + " and service_id='" + google_info['service_id'] + "'" 
    else:
        query = "insert into services(id, service_name, service_id, selected) values (" + str(TELEGRAM_MY_ID) + ", 'google', '" + google_info['service_id'] + "', 'True')"
    cursor.execute(query)
    conn.commit()
    update.message.reply_text("Your Account Name : "
                              "%s "
                              "Until next time!" % google_info['service_id'])
    return ConversationHandler.END

@restricted
def gdrive(bot, update, args):
    """Shows basic usage of the Google Drive API.

    Creates a Google Drive API service object and outputs the names and IDs
    for up to 10 files.
    """
    global chat_info, filelist, service, google_info
    page_token = None
    if(google_info is None):
        bot.sendMessage(update.message.chat_id, text=(
            "What is your google account?\n"
            "Start /google command."))
        return
    credentials = get_credential_info("gdrive", google_info["service_id"], update.message.from_user.id)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http, cache_discovery=False)
    if(len(args) > 0 and args[0] == "search"):
        count = 0
        page_count = 0
        filelist = {}
        print(args[1:])
        query = ' '.join(map(unicode,args[1:]))
        print(query)
        while True:
            page_msg = u"Searched Files\n"
            response = service.files().list(q=query.encode('utf-8'), 
                                            spaces='drive', 
                                            fields='nextPageToken, files(id, name)', 
                                            pageSize = 50,
                                            pageToken=page_token).execute()
            print(response)
            for file in response.get('files', []):
                # Process change
                file_info = {}
                name = file.get('name')
                id = file.get('id')
                file_info[name] = id
                filelist[count] = file_info
                page_msg += u"Found [{0}] : {1}".format(count, name) + " \n"
                count += 1
            update.message.reply_text(page_msg)
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break;
    elif(len(args) > 0 and args[0] == "get"):
        number = int(args[1])
        name = filelist[number].keys()[0]
        id = filelist[number][name]
        filename = FILESTORAGE + name
        request = service.files().get_media(fileId=id)
        request_str = json.loads(request.to_json())
        fh = io.FileIO(filename,"wb")
        downloader = MediaIoBaseDownload(fh, request)
        final = False
        while final is False:
            status, final = downloader.next_chunk()
            print("Download %d ." % int(status.progress() * 100))
        chat_id=update.message.chat_id
        bot.send_document(chat_id=chat_id, document=open(filename.encode('utf-8'), 'rb'))
        os.remove(filename.encode('utf-8'))
    else:
        print("check else")
        results = service.files().list(
            pageSize=10,fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            print('No files found.')
        else:
            msg = u"Files: \n"
            for item in items:
                msg += u'{0}'.format(item['name']) + " \n"
            update.message.reply_text(msg)

@restricted
def restart(bot, update):
    bot.send_message(update.message.chat_id, "Bot is restarting...")
    count = 0
    time.sleep(0.2)
    os.execl(sys.executable, sys.executable, *sys.argv)

if __name__ == '__main__':
    updater = Updater(telegram_info['service_accesstoken'])
    dispatcher = updater.dispatcher
    google_handler = ConversationHandler(
        entry_points=[CommandHandler('google', google)],
        states={
            CHOOSING: [RegexHandler('^(USE)$',
                                    use_account),
                       RegexHandler('^(ADD)$',
                                    add_account),
                       ],
            ACCOUNTING: [MessageHandler(Filters.text,
                                           input_account,
                                           pass_user_data=True),
                            ],
            DONE: [MessageHandler(Filters.text,
                                          done,
                                          pass_user_data=True),
                           ],
        },
        fallbacks=[RegexHandler('^Done$', done, pass_user_data=True)]
    )
    dispatcher.add_handler(google_handler)
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('hello', hello))
    dispatcher.add_handler(CommandHandler('gdrive', gdrive, pass_args=True))
    dispatcher.add_handler(CommandHandler('cmd', commander, pass_args=True))
    dispatcher.add_handler(MessageHandler([Filters.text], on_chat_message))
    dispatcher.add_handler(CommandHandler('r', restart))
    updater.start_polling()
    updater.idle()
