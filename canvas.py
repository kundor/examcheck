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

def load_here_or_parent(filename):
    try:
        with open(filename) as fil:
            return json.load(fil)
    except IOError:
        filename = os.path.join(os.pardir, filename)
    try:
        with open(filename) as fil:
            return json.load(fil)
    except:
        warnings.warn('Unable to load ' + filename, RuntimeWarning)

sections = load_here_or_parent('sections.json')
sections = {sec['id'] : sec for sec in sections}
students = load_here_or_parent('students.json')
