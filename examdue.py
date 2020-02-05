#!/usr/bin/python3

from canvas import *

assid = 589944
quizid = 85617
date = '2020-02-17'
unlock = 'T19:00:00Z'
due = 'T20:00:00Z'
extradue = 'T20:30:00Z'

extra_time_IDs = [ 308978 ]

with canvas_session() as s:
    curl = canvasbase + f'courses/{courseid}/assignments/{assid}/overrides'
    r = s.post(curl, data={
        'assignment_override[course_section_id]': secid,
        'assignment_override[due_at]': date + due,
        'assignment_override[lock_at]': date + due,
        'assignment_override[unlock_at]': date + unlock})
    print(r)
    print(r.json())
    for sid in extra_time_IDs:
        # Is extend_from_end_at enough to add time to lock_at/due_at without creating a separate override?
        # Needs to be tested
        curl = canvasbase + f'courses/{courseid}/quizzes/{quizid}/extensions'
        r = s.post(curl, data={
            'quiz_extensions[][user_id]': sid,
            'quiz_extensions[][extra_time]': 25,
            'quiz_extensions[][extend_from_end_at]': 30})

