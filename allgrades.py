#!/usr/bin/python3

from canvas import *

studict = {stu['id'] : stu['name'] for stu in students}
scores = {}

def streamgrades(session, quizid):
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
            if sid in scores:
                if scores[sid] == thescore:
                    print(f'Same score {thescore} seen again for {stuname}', file=sys.stderr)
                    continue
                print(f'Different score {thescore} seen for {stuname}, previously {scores[sid]}', file=sys.stderr)
                if thescore < scores[sid]:
                    continue # keep max score in dictionary and output
            yield stuname, round(thescore)
            scores[sid] = thescore

def printgrades(session, quizid):
    for stuname, score in streamgrades(session, quizid):
            print(f"{stuname}\t{score}")

def allgrades(quizids):
    with canvas_session() as session:
        for quizid in quizids:
            for _ in streamgrades(session, quizid):
                pass
    return scores

if __name__ == '__main__':
    try:
        quizids = {int(arg) for arg in sys.argv[1:]}
    except ValueError:
        sys.exit('Arguments must be quiz IDs (integers)')
    if not quizids:
        sys.exit('Must specify at least one quiz ID')

    with canvas_session() as s:
        for quizid in quizids:
            printgrades(s, quizid)

