#!/usr/bin/python3

from canvas import *

assid = 589988
date = '2020-02-05'
unlock = 'T19:00:00Z'
due = 'T20:00:00Z'

with canvas_session() as s:
    curl = canvasbase + f'courses/{courseid}/assignments/{assid}/overrides'
    r = s.post(curl, data={
        'assignment_override[course_section_id]': secid,
        'assignment_override[due_at]': date + due,
        'assignment_override[lock_at]': date + due,
        'assignment_override[unlock_at]': date + unlock})
    print(r)
    print(r.json())
