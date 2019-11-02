#!/usr/bin/python3

import sys
import IPython
from canvas import *

sys.excepthook = IPython.core.ultratb.FormattedTB(mode='Verbose', color_scheme='Linux', call_pdb=1)

rate = 20 # seconds between requests
minrest = 5 # wait at least this long (if a request took a long time)

assids = {506718, 548130}  # Module 7 exam, Module 7 Exam (*V*)

curl = canvasbase + f'audit/grade_change/courses/{courseid}'

section = sections[secid]
#section1 = sections[secid1]
dategot = '2019-02-25T00:00:00Z'
mystuds = section['students'] # + section1['students']
reports = set()
stuname = {stu['id']: stu['name'] for stu in students}

with canvas_session() as s:
    while len(reports) < len(mystuds):
      try:
        start = time.time()
        signal.signal(signal.SIGINT, deferint)
        with s.get(curl, params={'start_time': dategot}) as response:
            gce = response.json()['events']
        caught = [f"{stuname[g['links']['student']]}: {g['grade_after']}" for g in gce if g['links']['assignment'] in assids and g['links']['student'] in mystuds]
        if caught:
            print('\n'.join(c for c in caught))
            reports.update(caught)

        dategot = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(start))
        elapsed = time.time() - start
        signal.signal(signal.SIGINT, signal.default_int_handler)
        if deferint.nomore:
            break
        time.sleep(max(minrest, rate - elapsed))
      except KeyboardInterrupt:
        break

