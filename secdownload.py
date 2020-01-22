#!/usr/bin/python3

from canvas import *
import shutil
import sys

if len(sys.argv) > 1 and not sys.argv[-1].isdecimal():
    savedir = sys.argv.pop()
    print('Saving to', savedir)
else:
    savedir = input('Directory to save in? ')

try:
    assids = {int(arg) for arg in sys.argv[1:]}
except ValueError:
    sys.exit('Arguments must be upload assignment IDs (integers)')
if not assids:
    sys.exit('Must specify at least one upload assignment ID')

rate = 15
minrest = 5

#curls = [canvasbase + f'sections/{secid1}/assignments/{assid}/submissions',
#         canvasbase + f'sections/{secid}/assignments/{assid}/submissions']
curls = [canvasbase + f'sections/{secid}/assignments/{assid}/submissions' for assid in assids]

section = sections[secid]
#section1 = sections[secid1]
mystuds = section['students'] # + section1['students']
studict = {stu['id'] : stu for stu in students}
dnlds = {}
weirdids = {353646} # Test Student

os.makedirs(savedir, exist_ok=True)
os.chdir(savedir)

with canvas_session() as s:
    curi = 0
    while len(dnlds) < len(mystuds):
      try:
        start = time.time()
        signal.signal(signal.SIGINT, deferint)

        curi = (curi + 1) % len(curls)
        with s.get(curls[curi]) as r:
            rj = r.json()

        if deferint.nomore:
            break

        for sub in rj:
            sid = sub['user_id']
            try:
                stu = studict[sid]
            except KeyError:
                if sid not in weirdids:
                    weirdids.add(sid)
                    print('Wth?', sub)
                continue
            if 'attachments' not in sub:
                continue
            numatt = len(sub['attachments'])
            if sid in dnlds:
                if numatt != dnlds[sid]:
                    print(f'{stu["name"]}: {numatt} attachments now, ?')
                    dnlds[sid] = numatt
                continue
            if numatt != 1:
                print(f'{stu["name"]}: {numatt} attachments, ?')
            dst = codename(stu) + '_' + sub['attachments'][-1]['filename']
            url = sub['attachments'][-1]['url']
            print('Fetching', dst, '... ', end='', flush=True)
            with s.get(url, stream=True) as fileget, open(dst, 'wb') as out:
                shutil.copyfileobj(fileget.raw, out)
            dnlds[sid] = numatt
            print(f'done {len(dnlds)}.')
            if deferint.nomore:
                break

        elapsed = time.time() - start
        signal.signal(signal.SIGINT, signal.default_int_handler)
        if deferint.nomore:
            break
        time.sleep(max(minrest, rate - elapsed))
      except KeyboardInterrupt:
        break

