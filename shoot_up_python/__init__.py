#!/usr/bin/env python
"""Just a thing I'm testing

Apparently, this is where the module-level docstring goes
"""

import httplib2
import os
import sys

from apiclient import discovery
from apiclient.http import MediaFileUpload
import oauth2client
from oauth2client import client
from oauth2client import tools

import time
import subprocess
import pyperclip
import configparser

try:
    import argparse
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    #parser.add_argument('image')
    flags = parser.parse_args()
except ImportError:
    flags = None

package_root = os.path.abspath(os.path.dirname(__file__))
CLIENT_SECRET_FILE = os.path.join(package_root, 'client_secret.json')
SETTINGS_FILE = os.path.join(package_root, 'settings.cfg')
APPLICATION_NAME = 'shoot_up_python'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    auth_scopes = {'drive': 'https://www.googleapis.com/auth/drive',
                   'urlshortener': 'https://www.googleapis.com/auth/urlshortener'}

    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)

    credentials = dict()
    for key in auth_scopes:
        credential_path = os.path.join(credential_dir,
                                       'shoot_up_python-' + key + '.json')
        store = oauth2client.file.Storage(credential_path)
        credentials[key] = store.get()
        if not credentials[key] or credentials[key].invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, auth_scopes[key])
            flow.user_agent = APPLICATION_NAME
#        if flags:
            credentials[key] = tools.run_flow(flow, store, flags)
#        else: # Needed only for compatability with Python 2.6
#            credentials = tools.run(flow, store)
            print('Storing ' + key + ' credentials to ' + credential_path)
    return credentials

def shoot_up():
    """
        Takes a screenshot with scrot and saves it.
        Uploads the screenshot to Google Drive.
        Copies the URL to the clipboard.
    """
    image_file_name = "Screenshot_" + time.strftime("%Y-%m-%d_%H-%M-%S") + ".png"

    #take the screenshot with scrot
    image_file_path = "/tmp/" + image_file_name
    subprocess.call(["sleep", "0.2"])
    subprocess.check_call(["scrot", "-s", image_file_path])

    conf = configparser.ConfigParser()
    print(SETTINGS_FILE)
    conf.read(SETTINGS_FILE)
    if 'google_drive' in conf:
        screenshot_folder_name = conf['google_drive']['screenshot_folder']

    #load all the credentials. We have one for drive and one for urlshortener
    credentials = get_credentials()
    http = dict()
    for key in credentials:
        http[key] = credentials[key].authorize(httplib2.Http())

    #start the upload process
    drive_service = discovery.build('drive', 'v2', http=http['drive'])
    files_resource = drive_service.files()

    screenshot_folder = files_resource.list(q="title contains '" + screenshot_folder_name + "'")\
                                      .execute()['items'][0]['id']

    metadata = {
        "originalFileName": image_file_name,
        "title": image_file_name,
        "mimeType": "image/png",
        "parents":
        [
            {
                "id": screenshot_folder
            }
        ]
    }

    #have to create the MediaFileUpload object when using a body in the insert call
    file = MediaFileUpload(image_file_path, mimetype="image/png", resumable=True)

    result = files_resource.insert(media_body=file, body=metadata).execute()

    #this will give us a direct link to the file if we trim '&export=download' off the end
    link = result.get('webContentLink', [])
    image_link = link.split('&')[0]

    #run this through a url shortener just because
    shortener_service = discovery.build('urlshortener', 'v1', http=http['urlshortener'])
    shortener_resource = shortener_service.url()
    shortener_request_body = {
        "longUrl": image_link
    }
    shortener_response = shortener_resource.insert(body=shortener_request_body).execute()
    short_url = shortener_response.get('id', [])
    print("Url is: " + short_url)

    pyperclip.copy(short_url)


if __name__ == '__main__':
    shoot_up()
