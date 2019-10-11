#!/usr/bin/python3

from canvas import *
import sys

quizid = 73848 #mod 4 exam

curl = canvasbase + f'courses/{courseid}/quizzes/{quizid}/submissions'

studict = {stu['id'] : stu['name'] for stu in students}

with canvas_session() as s:
    while curl:
        with s.get(curl) as response:
            subs = response.json()['quiz_submissions']
            curl = response.links['next']['url'] if 'next' in response.links else None
        for sub in subs:
            if 'user_id' not in sub:
                print('What kinda submission is this, with no user_id?', sub, file=sys.stderr)
                continue
            if sub['user_id'] not in studict:
                print(f'I never heard of this user {sub["user_id"]}', file=sys.stderr)
                continue
            stuname = studict[sub['user_id']]
            if 'score' not in sub:
                print(f'No score for {stuname}?', file=sys.stderr)
                continue
            if not isinstance(sub['score'], float):
                print(f'Some crazy score {sub["score"]} for {stuname}', file=sys.stderr)
                continue
            if not sub['score'].is_integer():
                print(f'Not integer score {sub["score"]} for {sub["user_id"]}', file=sys.stderr)
            print(f"{stuname}\t{round(sub['score'])}")

