import os
import sys
import json
import time
import signal
import keyring
import warnings
import requests
from pathlib import Path
from datetime import date, time as Time
from dateutil.parser import isoparse

cuser = os.getenv('CANVASUSER')
if cuser:
    token = keyring.get_password('canvas.colorado.edu', cuser)
else:
    warnings.warn('Cannot find environment variable CANVASUSER', RuntimeWarning)

courseid = 57435
secid = 37411 # 012
sectime = Time(12) # section 012 at noon
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

def todays_assigns(filename):
    """Return exam IDs of given type (id or quiz_id) for today"""
    exams = load_file(filename, json.load)
    today = date.today()
    return [e for e in exams if e['date'] and isoparse(e['date']).date() == today]

def todays_ids(idtype):
    theexams = todays_assigns('exams.json')
    if theexams:
       print('Using assignments ' + ', '.join(e['name'] for e in theexams), file=sys.stderr)
       return [e[idtype] for e in theexams]

def get_fid(filename):
    """Try to open a file in the current directory, parent directory, or this file's location."""
    dirs = ('', os.pardir, Path(__file__).parent.resolve())
    for d in dirs:
        try:
            return open(os.path.join(d, filename))
        except IOError:
            continue

def load_file(filename, loader):
    try:
        with get_fid(filename) as fid:
            return loader(fid)
    except:
        warnings.warn('Unable to load ' + filename, RuntimeWarning)

sections = load_file('sections.json', json.load) # None, if it can't be found
if sections:
    sections = {sec['id'] : sec for sec in sections}
students = load_file('students.json', json.load)
