#!/usr/bin/python3

from canvas import *

unlock = 'T19:00:00Z'
due = 'T20:00:00Z'
extradue = 'T20:30:00Z'

# extra_time_IDs = [ 308978 ]

def set_exam_due(session, assid, quizid, date, extra_time_IDs):
    curl = canvasbase + f'courses/{courseid}/assignments/{assid}/overrides'
    response = s.post(curl, data={
        'assignment_override[course_section_id]': secid,
        'assignment_override[due_at]': date + due,
        'assignment_override[lock_at]': date + due,
        'assignment_override[unlock_at]': date + unlock})
    print(response)
    print(response.json())
    if not extra_time_IDs:
        return
    response = s.post(curl, data={
        'assignment_override[student_ids][]': extra_time_IDs,
        'assignment_override[title]': '012 Extra time',
        'assignment_override[due_at]': date + extradue,
        'assignment_override[lock_at]': date + extradue,
        'assignment_override[unlock_at]': date + unlock})
    print(response)
    print(response.json())
    for sid in extra_time_IDs:
        curl = canvasbase + f'courses/{courseid}/quizzes/{quizid}/extensions'
        r = s.post(curl, data={
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
