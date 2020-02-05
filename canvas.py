import os
import sys
import json
import time
import signal
import keyring
import warnings
import requests

cuser = os.getenv('CANVASUSER')
if cuser:
    token = keyring.get_password('canvas.colorado.edu', cuser)
else:
    warnings.warn('Cannot find environment variable CANVASUSER', RuntimeWarning)

courseid = 57435
secid = 37411 # 012
canvasbase = 'https://canvas.colorado.edu/api/v1/'

def canvas_session():
    s = requests.Session()
    s.headers.update({"Authorization": "Bearer " + token})
    s.params = {'per_page': 100}
    return s

def deferint(signum, frame):
    if deferint.nomore:
        print("Killing with fire")
        raise KeyboardInterrupt
    print("Waiting for request...")
    deferint.nomore = True

deferint.nomore = False

def alphaonly(string):
    return ''.join(filter(str.isalpha, string))

def codename(student):
    return alphaonly(student['sortable_name'].lower())

try:
    with open('sections.json') as fil:
        sections = json.load(fil)
    sections = {sec['id'] : sec for sec in sections}

    with open('students.json') as fil:
        students = json.load(fil)
except:
    warnings.warn('Unable to load sections.json and students.json', RuntimeWarning)
