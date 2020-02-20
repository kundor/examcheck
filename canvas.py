import os
import sys
import json
import time
import signal
import keyring
import warnings
import requests
from pathlib import Path

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

def get_fid(filename):
    """Try to open a file in the current directory, parent directory, or this file's location."""
    dirs = ('', os.pardir, Path(__file__).parent.resolve())
    for d in dirs:
        try:
            fid = open(os.path.join(d, filename))
            return fid
        except IOError:
            continue
    warnings.warn('Unable to load ' + filename, RuntimeWarning)

def load_json(filename):
    fid = get_fid(filename)
    if fid:
        json = json.load(fid)
        fid.close()

sections = load_json('sections.json') # None, if it can't be found
if sections:
    sections = {sec['id'] : sec for sec in sections}
students = load_json('students.json')
