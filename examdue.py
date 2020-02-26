#!/usr/bin/python3

from canvas import *
from datetime import datetime, time, timedelta, timezone

mytime = time(12) # section 012 at noon

# extra_time_IDs = [ 308978 ]

def combine(date, time_of_day, delta=timedelta(0)):
    if isinstance(date, str):
        date = isoparse(date)
    dt = datetime.combine(date, time_of_day) + delta
    iso = dt.astimezone(timezone.utc).isoformat()
    return iso.replace('+00:00', 'Z')

def set_exam_due(session, assid, quizid, date, extra_time_IDs):
    curl = canvasbase + f'courses/{courseid}/assignments/{assid}/overrides'
    duedelta = timedelta(hours=1)
    extradelta = timedelta(hours=1.5)
    begin = combine(date, mytime)
    end = combine(date, mytime, duedelta)
    extraend = combine(date, mytime, extradelta)
    response = session.post(curl, data={
        'assignment_override[course_section_id]': secid,
        'assignment_override[due_at]': end,
        'assignment_override[lock_at]': end,
        'assignment_override[unlock_at]': begin})
    print(response)
    print(response.json())
    if not extra_time_IDs:
        return
    response = session.post(curl, data={
        'assignment_override[student_ids][]': extra_time_IDs,
        'assignment_override[title]': '012 Extra time',
        'assignment_override[due_at]': extraend,
        'assignment_override[lock_at]': extraend,
        'assignment_override[unlock_at]': begin})
    print(response)
    print(response.json())
    for sid in extra_time_IDs:
        curl = canvasbase + f'courses/{courseid}/quizzes/{quizid}/extensions'
        r = session.post(curl, data={
            'quiz_extensions[][user_id]': sid,
            'quiz_extensions[][extra_time]': 25})

if __name__ == '__main__':
    try:
        assid = int(sys.argv[1])
        quizid = int(sys.argv[2])
        date = sys.argv[3]
        if len(sys.argv) > 4:
            extra_time_IDs = [int(arg) for arg in sys.argv[4:]]
    except (ValueError, IndexError):
        sys.exit(f'Usage: {sys.argv[0]} <assid> <quizid> <date> [extra-time IDs...]')

    with canvas_session() as session:
        set_exam_due(session, assid, quizid, date, extra_time_IDs)
