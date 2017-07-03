from __future__ import print_function
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import telegram 
from subprocess import PIPE, STDOUT, Popen
import shlex

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
    update.message.reply_text('Hello World!')

def hello(bot, update):
    update.message.reply_text(
        'Hello {}'.format(update.message.from_user.first_name))

def ls(bot, update):
	result = subprocess.check_output ('ls -al' , shell=True)
	update.message.reply_text(result)

def apt(bot, update):
    cmd = 'apt upgrade'
    my_env = os.environ
    args = shlex.split(cmd)
    #print(my_env['PATH'])
    proc = Popen(args, env=my_env, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    (output, error) = proc.communicate()
    bot.sendMessage(update.message.chat_id, output)
    update.message.reply_text(output)

def ifconfig(bot, update):
	result = subprocess.check_output ('ifconfig' , shell=True)
	update.message.reply_text(result)

def on_chat_message(bot, update):
    chat_id = update.message.chat_id
    user = update.message.from_user
    user_name = "%s%s" % (user.last_name, user.first_name)
    bot.sendMessage(chat_id, text=("%s say " + update.message.text) % user_name)
    return

def gdrive(bot, update):
    """Shows basic usage of the Google Drive API.

    Creates a Google Drive API service object and outputs the names and IDs
    for up to 10 files.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

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

if __name__ == '__main__':
    updater = Updater('420091787:AAFuiSJXkYK1pk1yhU3WRjoEOmw7vR8dh0Q')
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('hello', hello))
    dispatcher.add_handler(CommandHandler('ls', ls))
    dispatcher.add_handler(CommandHandler('ifconfig', ifconfig))
    dispatcher.add_handler(CommandHandler('gdrive', gdrive))
    dispatcher.add_handler(CommandHandler('apt', apt))
    dispatcher.add_handler(MessageHandler([Filters.text], on_chat_message))

    updater.start_polling()
    updater.idle()
