#!/usr/bin/python3

from canvas import *

studict = {stu['id'] : stu['name'] for stu in students}

def stream_grades(session, quizid, seenscores={}):
    # Passing the same seenscores dict for multiple invocations will update the scores
    # The default seenscores, with no third argument, persists across all such invocations
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
        print(f"{sid}\t{score}")

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
    if grades_found(localfile):
        print(f'Not fetching grades, using file {localfile}', file=sys.stderr)
        return load_grades(localfile)
    scores = {}
    with open(localfile, 'wt') as fid, canvas_session() as session:
        for quizid in quizids:
            for sid, score in stream_grades(session, quizid, scores):
                print(f'{sid}\t{score}', file=fid)
    return scores

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

