from __future__ import print_function
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, RegexHandler
from telegram import ReplyKeyboardMarkup
import telegram 
from subprocess import PIPE, STDOUT, Popen, check_output
import shlex
import json
from functools import wraps

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
filelist = {}
service = None
FILESTORAGE = "files/"

with open('users.json', 'rw') as user_file:
    jsondata = json.load(user_file)

#google_keyboard = [['USE','ADD']]
#markup = ReplyKeyboardMarkup(google_keyboard, one_time_keyboard=True)
CHOOSING, ACCOUNTING, DONE = range(3)

def get_credential_info(service_name, user_name, user_id):
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    file_name = str(service_name)+"-"+str(user_name)+"-"+str(user_id)+".json"
    credential_path = os.path.join(credential_dir, file_name)
    
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
            print("Unauthorized access denied for {}.".format(user_id))
            return
        return func(bot, update, *args, **kwargs)
    return wrapped

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

@restricted
def on_chat_message(bot, update):
    chat_id = update.message.chat_id
    user = update.message.from_user
    user_name = "%s%s" % (user.last_name, user.first_name)
    bot.sendMessage(chat_id, text=("%s say " + update.message.text) % user_name)

def google(bot, update):
    global credentials, chat_info

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

@restricted
def gdrive(bot, update, args):
    """Shows basic usage of the Google Drive API.

    Creates a Google Drive API service object and outputs the names and IDs
    for up to 10 files.
    """
    global valid, chat_info, filelist, service
    page_token = None

    if("google" not in chat_info):
        bot.sendMessage(update.message.chat_id, text=(
            "What is your google account?"
            "Start /google command."))
        return

    credentials = get_credential_info("gdrive", chat_info["google"], update.message.from_user.id)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    
    if(args[0] == "search"):
        count = 0
        filelist = {}
        msg = u"Searched Files\n"
        while True:
            query = ' '.join(map(str,args[1:]))
            response = service.files().list(q=query, 
                                            spaces='drive', 
                                            fields='nextPageToken, files(id, name)', 
                                            pageToken=page_token).execute()
            print(response)
            for file in response.get('files', []):
                # Process change
                file_info = {}
                name = file.get('name')
                id = file.get('id')
                file_info[name] = id
                filelist[count] = file_info
                msg += u"Found [{0}] : {1}".format(count, name) + " \n"
                count += 1
                print(msg)
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break;
        update.message.reply_text(msg)

    elif(args[0] == "get"):
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
        results = service.files().list(
            pageSize=10,fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            print('No files found.')
        else:
            msg = "Files: \n"
            for item in items:
                msg += '{0}'.format(item['name']) + " \n"
            update.message.reply_text(msg)

def restart(bot, update):
    bot.send_message(update.message.chat_id, "Bot is restarting...")
    count = 0
    for user in jsondata["users"]:
        if(user["id"] == update.message.from_user.id):
            jsondata["users"][count] = chat_info
        count = count + 1
    print("json: " + str(jsondata))
    with open('users.json','w') as save_file:
        save_file.write(json.dumps(jsondata))
        save_file.close()
    time.sleep(0.2)
    os.execl(sys.executable, sys.executable, *sys.argv)

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
    dispatcher.add_handler(CommandHandler('r', restart))

    updater.start_polling()
    updater.idle()
