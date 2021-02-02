import os
import re
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

COORDINATOR = 'Joseph Timmer'
# COORDINATOR = 'Elizabeth L. Grulke'
courseids = [70043, # Math 1112-REMOTE
             70047] # Math 1112-ONLINE
#secid = 57825 # 009
#sectime = Time(11, 30) # section 009 at 11:30
canvasbase = 'https://canvas.colorado.edu/api/v1/'

def canvas_session():
    s = requests.Session()
    s.headers.update({"Authorization": "Bearer " + token})
    s.params = {'per_page': 100}
    return s

def follow_next(session, curl, **kwargs):
    if not curl.startswith('http'):
        curl = canvasbase + curl
    while curl:
        with session.get(curl, **kwargs) as response:
            curl = response.links.get('next', {}).get('url')
            yield response.json()

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

def yesno(prompt):
    answer = input(prompt)
    return answer.lower() in {'y', 'yes'}

def dated_assigns(filename):
    assigns = load_file(filename, json.load)
    assigns = [a for a in assigns if a['date']]
    for a in assigns:
        a['date'] = isoparse(a['date']).date()
    return assigns

def todays_assigns(filename, today=None):
    if today is None:
        today = date.today()
    return [e for e in dated_assigns(filename) if e['date'] == today]

def most_recent(filename):
    today = date.today()
    past_assigns = [e for e in dated_assigns(filename) if e['date'] <= today]
    if not past_assigns:
        return
    mintime = min(today - e['date'] for e in past_assigns)
    return [e for e in past_assigns if today - e['date'] == mintime]

def listnames(seq):
    return ', '.join(s['name'] for s in seq)

def todays_exams():
    """Return exams for today"""
    theexams = todays_assigns('exams.json')
    if theexams:
        print('Using assignments ' + listnames(theexams), file=sys.stderr)
        return theexams
    theexams = most_recent('exams.json')
    if theexams and yesno(f'Use assignments {listnames(theexams)} from {theexams[0]["date"]}? '):
        return theexams
    return []

def todays_ids(idtype):
    """Return exam IDs of given type (id or quiz_id) for today"""
    return [(e['course_id'], e[idtype]) for e in todays_exams()]

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
    for sec in sections:
        sec['shortname'] = re.search('[^-]*$', sec['name']).group()
    sections = {sec['id'] : sec for sec in sections}
students = load_file('students.json', json.load)
