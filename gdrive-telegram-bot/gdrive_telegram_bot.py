from __future__ import print_function
from telegram.ext import Updater, CommandHandler
import subprocess

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
	update.message.reply_text(
		result)

def ifconfig(bot, update):
	result = subprocess.check_output ('ifconfig' , shell=True)
	update.message.reply_text(
		result)

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
            #msg += '{0} ({1})'.format(item['name'], item['id']) + " \n"
            #update.message.reply_text('{0} ({1})'.format(item['name'], item['id']))

        update.message.reply_text(msg)

            #request = service.files().get_media(fileId=item['id'])
            #fh = io.FileIO(item['name'], mode='wb')
            #downloader = MediaIoBaseDownload(fh, request)
            #done = False
            

		#while done is False:
        #    status, done = downloader.next_chunk()
        #    update.message.reply_text("Download %d%%." % int(status.progress() * 100))

if __name__ == '__main__':
    updater = Updater('420091787:AAFuiSJXkYK1pk1yhU3WRjoEOmw7vR8dh0Q')
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('hello', hello))
    updater.dispatcher.add_handler(CommandHandler('ls', ls))
    updater.dispatcher.add_handler(CommandHandler('ifconfig', ifconfig))
    updater.dispatcher.add_handler(CommandHandler('gdrive', gdrive))

    updater.start_polling()
    updater.idle()
