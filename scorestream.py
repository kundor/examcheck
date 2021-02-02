#!/usr/bin/python3

import IPython
from canvas import *

sys.excepthook = IPython.core.ultratb.FormattedTB(mode='Verbose', color_scheme='Linux', call_pdb=1)

rate = 20 # seconds between requests
minrest = 5 # wait at least this long (if a request took a long time)

try:
    courseid = int(sys.argv[1])
    assids = {int(arg) for arg in sys.argv[2:]}
except ValueError:
    sys.exit('Arguments must be course ID followed by assignment IDs (integers)')
if not assids:
    course_ass_ids = todays_ids('id')
    courseids = {ca[0] for ca in course_ass_ids}
    assert len(courseids) == 1
    courseid = courseids.pop()
    assids = {ca[1] for ca in course_ass_ids}
if not assids:
   sys.exit('Must specify at least one assignment ID')

curl = canvasbase + f'audit/grade_change/courses/{courseid}'

section = sections[secid]
#section1 = sections[secid1]
dategot = '2020-01-15T00:00:00Z'
mystuds = section['students'] # + section1['students']
scores = {}
stuname = {stu['id']: stu['name'] for stu in students}

with canvas_session() as s:
    while len(scores) < len(mystuds):
      try:
        start = time.time()
        signal.signal(signal.SIGINT, deferint)
        try:
          with s.get(curl, params={'start_time': dategot}) as response:
            response_date = response.headers['Date']
            gce = response.json()['events']
          for g in gce:
              sid = g['links']['student']
              if g['links']['assignment'] in assids and sid in mystuds:
                  thescore = g['grade_after']
                  if sid in scores:
                      if thescore != scores[sid]:
                          print(f"{stuname[sid]}: {thescore} now?")
                          scores[sid] = thescore
                      continue
                  scores[sid] = thescore
                  print(f"{len(scores):2}. {stuname[sid]}: {thescore}")

          response_date = time.strptime(response_date[:-4], '%a, %d %b %Y %H:%M:%S')
          dategot = time.strftime('%Y-%m-%dT%H:%M:%SZ', response_date)
          #time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(start))
          #using local time doesn't work when it's not in sync with Canvas's server time
        except KeyError:
          pass
        elapsed = time.time() - start
        signal.signal(signal.SIGINT, signal.default_int_handler)
        if deferint.nomore:
            break
        time.sleep(max(minrest, rate - elapsed))
      except KeyboardInterrupt:
        break

