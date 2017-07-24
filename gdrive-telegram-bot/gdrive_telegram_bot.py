from __future__ import print_function
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, RegexHandler
from telegram import ReplyKeyboardMarkup
import telegram 
from subprocess import PIPE, STDOUT, Popen, check_output
import shlex
import json

import httplib2
import os
import io

from googleapiclient.http import *
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

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
proc = None
valid = False
credentials = None
chat_info = None

with open('users.json') as user_file:
	jsondata = json.load(user_file)

#google_keyboard = [['USE','ADD']]
#markup = ReplyKeyboardMarkup(google_keyboard, one_time_keyboard=True)
CHOOSING, ACCOUNTING, DONE = range(3)

def get_credential_info(service_name, user_name, user_id):
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    print("enter function")
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

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')

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

def start(bot, update):
    global valid
    global chat_info
    for user in jsondata["users"]:
        if(user["id"] == update.message.from_user.id):
            if(user["permission"] == "valid"):
                valid = True
                chat_info = user
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

def on_chat_message(bot, update):
    global valid
    if(valid):
        chat_id = update.message.chat_id
        user = update.message.from_user
        user_name = "%s%s" % (user.last_name, user.first_name)
        bot.sendMessage(chat_id, text=("%s say " + update.message.text) % user_name)
    else:
        update.message.reply_text("Can't identify user.")
    return

def google(bot, update):
    global credentials, chat_info
    print("start conv")
    if("google" in chat_info):
        update.message.reply_text("check your account : " + chat_info["google"])
        return CHOOSING
    else:
        update.message.reply_text("Add your account")
        return ACCOUNTING

def add_account(bot, update):
    update.message.reply_text("Add your account")
    return ACCOUNTING

def use_account(bot, update):
    global chat_info
    text = chat_info["google"]
    update.message.reply_text('Your account name: %s' % text.lower())
    return DONE

def input_account(bot, update, user_data):
    global chat_info
    text = update.message.text
    chat_info["google"] = text
    update.message.reply_text('Your account name: %s' % text.lower())
    return DONE

def done(bot, update, user_data):
    global chat_info
    update.message.reply_text("Your Account Name : "
                              "%s "
                              "Until next time!" % chat_info["google"])
    return ConversationHandler.END

def gdrive(bot, update, args):
    """Shows basic usage of the Google Drive API.

    Creates a Google Drive API service object and outputs the names and IDs
    for up to 10 files.
    """
    global valid, chat_info
    page_token = None
    if("google" not in chat_info):
        bot.sendMessage(update.message.chat_id, text=(
            "What is your google account?"
            "Start /google command."))
        return

    if(valid):
        print(update.message.from_user)
        credentials = get_credential_info("gdrive", chat_info["google"], update.message.from_user.id)
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('drive', 'v3', http=http)

        if(args[0] == "search"):
            while True:
                query = ' '.join(map(str,args[1:]))
                response = service.files().list(q=query, 
                                                spaces='drive', 
                                                fields='nextPageToken, files(id, name)', 
                                                pageToken=page_token).execute()
                for file in response.get('files', []):
                    # Process change
                    update.message.reply_text('Found file: %s' % (file.get('name')))
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break;
        else:
            results = service.files().list(
                pageSize=10,fields="nextPageToken, files(id, name)").execute()
            items = results.get('files', [])
            if not items:
                print('No files found.')
            else:
                #update.message.reply_text('Files:')
                msg = "Files: \n"
                for item in items:
                    msg += '{0}'.format(item['name']) + " \n"
                update.message.reply_text(msg)
    else:
        update.message.reply_text("Can't identify user.")

if __name__ == '__main__':
    updater = Updater('420091787:AAFuiSJXkYK1pk1yhU3WRjoEOmw7vR8dh0Q')
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

    updater.start_polling()
    updater.idle()
