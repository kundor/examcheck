#!/usr/bin/python3
import os
if 'DISPLAY' not in os.environ:
    os.environ['DISPLAY'] = ':0'
from canvas import *
from collections import Counter

try:
    secid = int(sys.argv[1])
    if len(sys.argv) > 2:
        quizid = int(sys.argv[2])
    else:
        quizid = None
except (ValueError, IndexError):
    sys.exit('Arguments must be section ID followed by quiz IDs (integers). SecIDs: ' + str({sid: sections[sid]['shortname'] for sid in secids}))

if not quizid:
    course_quiz_ids = todays_ids('quiz_id')
    courseids = {ca[0] for ca in course_quiz_ids}
    assert len(courseids) == 1
    courseid = courseids.pop()
    quizids = {ca[1] for ca in course_quiz_ids}
    assert len(quizids) == 1
    quizid = quizids.pop()

ignore_list = []

#mysecs = [sections[si] for si in secids]
mysec = sections[secid]
secname = mysec['shortname']
mystuds = mysec['students']
studict = {stu["id"]: stu for stu in students}

sesh = canvas_session()
curl = canvasbase + f'courses/{courseid}/quizzes/{quizid}/submissions'

def renew():
    subs = []
    for rj in follow_next(sesh, curl):
        subs += rj['quiz_submissions']
    return subs

subs = renew()

mysubs = [sub for sub in subs if sub['user_id'] in mystuds]

mycounts = Counter(s['workflow_state'] for s in mysubs)

print('In my sections:')
for k in mycounts:
    print(f'{k:>15}: {mycounts[k]}')

alpha_list = sorted(mystuds, key=lambda s: studict[s]['sortable_name'])
sub_dict = {sub['user_id'] : sub for sub in subs}

def list_all():
    n = 0
    for sid in alpha_list:
        n += 1
        stu = studict[sid]
        if 'email' in stu:
            eml = stu['email']
        else:
            eml = stu['login_id'] + '@colorado.edu'
        if sid not in sub_dict:
            print(f'{stu["name"]:26} No submission' + ' '*23 + eml)
        else:
            sub = sub_dict[sid]
            stat = sub['workflow_state']
            if sub['started_at']:
                _, start = sub['started_at'].split('T')
            else:
                start = '-'*9
            if sub['end_at']:
                _, end = sub['end_at'].split('T')
            else:
                end = '-'*9
            print(f'{stu["name"]:26} {stat:14} {start} {end}  {eml}')

def just_none():
    n = 0
    email_list = []
    for sid in alpha_list:
        if n and n % 35 == 0:
            input('----More----')
        stu = studict[sid]
        if 'email' in stu:
            eml = stu['email']
        else:
            eml = '(no email)' + stu['login_id'] + '@colorado.edu'
        if sid not in sub_dict:
            print(f'{stu["name"]:26} No submission' + ' '*23 + eml)
            email_list.append(eml)
            n += 1
            continue
        sub = sub_dict[sid]
        stat = sub['workflow_state']
        if stat in ('untaken', 'complete'):
            continue
        if sub['started_at']:
            _, start = sub['started_at'].split('T')
        else:
            start = '-'*9
        if sub['end_at']:
            _, end = sub['end_at'].split('T')
        else:
            end = '-'*9
        print(f'{stu["name"]:26} {stat:14} {start} {end}  {eml}')
        email_list.append(eml)
        n += 1
    print(n, 'total')
    return email_list

# elist = just_none()
# tl = [e for e in elist if not any(iname in e for iname in ignore_list)]
# print('; '.join(tl))

list_all()
