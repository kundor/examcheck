#!/usr/bin/python3

from canvas import *

rate = 20 # seconds between requests
minrest = 5 # wait at least this long (if a request took a long time)

curl = canvasbase + f'audit/grade_change/courses/{courseid}'

section = sections[secid]
dategot = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
mystuds = section['students']
numreports = 0
stuname = {stu['id']: stu['name'] for stu in students}

with canvas_session() as s:
    while numreports < len(mystuds):
      try:
        start = time.time()
        signal.signal(signal.SIGINT, deferint)
        with s.get(curl, params={'start_time': dategot}) as response:
            rj = response.json()
        gce = rj['events']
        linked = rj['linked']['assignments']
        assname = {l['id']: l['name'] for l in linked}
        caught = [(stuname[g['links']['student']], assname[g['links']['assignment']], g['grade_after']) for g in gce if g['links']['student'] in mystuds]
        if caught:
            print('\n'.join(str(c) for c in caught))
            numreports += len(caught)

        dategot = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(start))
        elapsed = time.time() - start
        signal.signal(signal.SIGINT, signal.default_int_handler)
        if deferint.nomore:
            break
        time.sleep(max(minrest, rate - elapsed))
      except KeyboardInterrupt:
        break

