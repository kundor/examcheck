#!/usr/bin/python3

from canvas import *
from datetime import datetime, timedelta, timezone
from getdata import get_overrides

# extra_time_IDs = [ 308978 ]

def combine(date, time_of_day, delta=timedelta(0)):
    if isinstance(date, str):
        date = isoparse(date)
    dt = datetime.combine(date, time_of_day) + delta
    iso = dt.astimezone(timezone.utc).isoformat()
    return iso.replace('+00:00', 'Z')

def extend_time(session, exam, student_id, secid, minutes=30):
    """Extend allowed time for one student (does not affect due time)"""
    curl = canvasbase + f'courses/{exam["course_id"]}/quizzes/{exam["quiz_id"]}/extensions'
    response = session.post(curl, data={
        'quiz_extensions[][user_id]': student_id,
        'quiz_extensions[][extra_time]': minutes})
    print(response, '\n', response.json())


def set_exam_due(session, exam, extra_time_IDs=[], secid=secid, sectime=sectime):
    curl = canvasbase + f'courses/{exam["course_id"]}/assignments/{exam["id"]}/overrides'
    duedelta = timedelta(hours=1)
    extradelta = timedelta(hours=1.5)
    begin = combine(exam['date'], sectime)
    end = combine(exam['date'], sectime, duedelta)
    extraend = combine(exam['date'], sectime, extradelta)
    response = session.post(curl, data={
        'assignment_override[course_section_id]': secid,
        'assignment_override[due_at]': end,
        'assignment_override[lock_at]': end,
        'assignment_override[unlock_at]': begin})
    print(response)
    print(response.json())
    if not extra_time_IDs:
        return
    secname = section_name(secid)
    response = session.post(curl, data={
        'assignment_override[student_ids][]': extra_time_IDs,
        'assignment_override[title]': secname + ' Extra time',
        'assignment_override[due_at]': extraend,
        'assignment_override[lock_at]': extraend,
        'assignment_override[unlock_at]': begin})
    print(response)
    print(response.json())
    for sid in extra_time_IDs:
        extend_time(session, exam, sid, secid, 25)

def is_section(override, secid):
    return 'course_section_id' in override and override['course_section_id'] == secid

def matched_section(overrides, secid):
    """Return first override targeting given section, or None"""
    return next((o for o in overrides if is_section(o, secid)), None)

def section_name(secid):
    secname = sections[secid]['name']
    _, _, short = secname.partition('-')
    return short if short else secname

def set_all_exams(session, secid=secid, sectime=sectime, extraIDs=[]):
    exams = load_file('exams.json', json.load)
    secname = section_name(secid)
    for exam in exams:
        if not exam['date'] or '(*V*)' in exam['name']:
            continue
        overs = get_overrides(session, exam['course_id'], exam['id'])
        matchover = matched_section(overs, secid)
        if matchover:
            endtimes = matchover["lock_at"]
            if matchover["due_at"] != endtimes:
                endtimes += "; " + matchover["due_at"]
            print(f'Override already present for section {secname}, times '
                  f'{matchover["unlock_at"]} -- {endtimes}')
            continue
        print(f'Setting {exam["name"]} for section {secname}')
        set_exam_due(session, exam, extraIDs, secid, sectime)

if __name__ == '__main__':
    try:
        courseid = int(sys.argv[1])
        assid = int(sys.argv[2])
        quizid = int(sys.argv[3])
        date = isoparse(sys.argv[4])
        if len(sys.argv) > 5:
            extra_time_IDs = [int(arg) for arg in sys.argv[5:]]
    except (ValueError, IndexError):
        sys.exit(f'Usage: {sys.argv[0]} <courseid> <assid> <quizid> <date> [extra-time IDs...]')

    myexam = {'course_id': courseid, 'id': assid, 'quiz_id': quizid, 'date': date}

    with canvas_session() as session:
        set_exam_due(session, myexam, extra_time_IDs)
