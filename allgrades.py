#!/usr/bin/python3

from canvas import *

studict = {stu['id'] : stu['name'] for stu in students}

def stream_grades(session, courseid, quizid, seenscores={}):
    # Passing the same seenscores dict for multiple invocations will update the scores
    # The default seenscores, with no fourth argument, persists across all such invocations
    # (So if you use this for non-equivalent assignments, you must pass a score dict)
    curl = f'courses/{courseid}/quizzes/{quizid}/submissions'
    for json in follow_next(session, curl):
        subs = json['quiz_submissions']
        for sub in subs:
            if 'user_id' not in sub:
                print('What kinda submission is this, with no user_id?', sub, file=sys.stderr)
                continue
            sid = sub['user_id']
            if sid not in studict:
                print(f'I never heard of this user {sid}', file=sys.stderr)
                continue
            stuname = studict[sid]
            if 'score' not in sub:
                print(f'No score for {stuname}?', file=sys.stderr)
                continue
            thescore = sub['score']
            if not isinstance(thescore, float):
                print(f'Some crazy score {thescore} for {stuname}', file=sys.stderr)
                continue
#            if not thescore.is_integer():
#                print(f'Not integer score {thescore} for {sid}', file=sys.stderr)
            if sid in seenscores:
                if seenscores[sid] == thescore:
                    print(f'Same score {thescore} seen again for {stuname}', file=sys.stderr)
                    continue
                print(f'Different score {thescore} seen for {stuname}, previously {seenscores[sid]}', file=sys.stderr)
                if thescore < seenscores[sid]:
                    continue # keep max score in dictionary and output
            yield sid, thescore
            seenscores[sid] = thescore

def print_grades(session, courseid, quizid):
    for sid, score in stream_grades(session, courseid, quizid):
        print(f"{sid}\t{score}")

def all_grades(course_quiz_ids):
    scores = {}
    with canvas_session() as session:
        for (courseid, quizid) in course_quiz_ids:
            scores.update(stream_grades(session, courseid, quizid))
    return scores

def grades_found(localfile):
    if not os.path.exists(localfile):
        return False
    numstud = len(students)
    with open(localfile, 'rt') as fid:
        numrec = sum(1 for line in fid)
    return numrec > 0.8 * numstud # Less than 80% of student is assumed to be incomplete

def load_grades(localfile):
    thescores = {}
    with open(localfile, 'rt') as fid:
        for line in fid:
            stuid, score = line.split('\t')
            thescores[stuid] = score
    return thescores

def fetch_grades(course_quiz_ids, localfile='grades'):
    if grades_found(localfile):
        print(f'Not fetching grades, using file {localfile}', file=sys.stderr)
        return load_grades(localfile)
    scores = {}
    with open(localfile, 'wt') as fid, canvas_session() as session:
        for (courseid, quizid) in course_quiz_ids:
            for sid, score in stream_grades(session, courseid, quizid, scores):
                print(f'{sid}\t{score}', file=fid)
    return scores

if __name__ == '__main__':
    try:
        course_quiz_ids = {int(arg) for arg in sys.argv[1:]}
    except ValueError:
        sys.exit('Arguments must be course and quiz IDs in pairs (integers)')
    if not quizids:
        course_quiz_ids = todays_ids('quiz_id')
    if not course_quiz_ids:
       sys.exit('Must specify at least one quiz ID')

    with canvas_session() as s:
        for (courseid, quizid) in course_quiz_ids:
            print_grades(s, courseid, quizid)

