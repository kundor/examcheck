#!/usr/bin/python3

from canvas import *

studict = {stu['id'] : stu['name'] for stu in students}

def stream_grades(session, quizid, seenscores={}):
    curl = canvasbase + f'courses/{courseid}/quizzes/{quizid}/submissions'
    while curl:
        with session.get(curl) as response:
            subs = response.json()['quiz_submissions']
            curl = response.links['next']['url'] if 'next' in response.links else None
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
            if not thescore.is_integer():
                print(f'Not integer score {thescore} for {sid}', file=sys.stderr)
            if sid in seenscores:
                if seenscores[sid] == thescore:
                    print(f'Same score {thescore} seen again for {stuname}', file=sys.stderr)
                    continue
                print(f'Different score {thescore} seen for {stuname}, previously {seenscores[sid]}', file=sys.stderr)
                if thescore < seenscores[sid]:
                    continue # keep max score in dictionary and output
            yield sid, round(thescore)
            seenscores[sid] = thescore

def print_grades(session, quizid):
    for sid, score in stream_grades(session, quizid):
        stuname = studict[sid]
        print(f"{stuname}\t{score}")

def all_grades(quizids):
    scores = {}
    with canvas_session() as session:
        for quizid in quizids:
            scores.update(stream_grades(session, quizid))
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
            thescores[int(stuid)] = int(score)
    return thescores

def fetch_grades(quizids, localfile='grades'):
    if gradesfound(localfile):
        print('Not fetching grades, using file {localfile}', file=sys.stderr)
        return load_grades(localfile)
    return all_grades(quizids)

if __name__ == '__main__':
    try:
        quizids = {int(arg) for arg in sys.argv[1:]}
    except ValueError:
        sys.exit('Arguments must be quiz IDs (integers)')
    if not quizids:
        quizids = todays_ids('quiz_id')
    if not quizids:
       sys.exit('Must specify at least one quiz ID')

    with canvas_session() as s:
        for quizid in quizids:
            print_grades(s, quizid)

