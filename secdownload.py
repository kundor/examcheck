#!/usr/bin/python3

from canvas import *
import shutil

savedir = None

if len(sys.argv) > 2 and not sys.argv[-1].isdecimal():
    savedir = sys.argv.pop()

#try:
#    secid = int(sys.argv[1])
#except (ValueError, IndexError):
#    sys.exit('First argument must be section ID. SecIDs: ' + str({sid: sections[sid]['shortname'] for sid in secids}))

try:
    assids = [int(arg) for arg in sys.argv[2:]]
except ValueError:
    sys.exit('Arguments must be upload assignment IDs (integers) followed by optional [save directory]')

if not assids:
    theuploads = todays_assigns('uploads.json')
    if theuploads:
       print('Using assignments ' + ', '.join(u['name'] for u in theuploads))
       assids = [u['id'] for u in theuploads]
       modnum = ''.join(filter(str.isdigit, theuploads[0]['name']))
    else:
       sys.exit('Must specify at least one upload assignment ID')
else:
    modnum = assids[0]

if not savedir:
    savedir = 'mymod' + str(modnum)
print('Saving to', savedir)

rate = 15
minrest = 5

#curls = [canvasbase + f'sections/{secid1}/assignments/{assid}/submissions',
#         canvasbase + f'sections/{secid}/assignments/{assid}/submissions']
curls = [canvasbase + f'sections/{secid}/assignments/{assid}/submissions' for secid in secids for assid in assids]

sections = [sections[secid] for secid in secids]
mystuds = sum((section['students'] for section in sections), start=[])
studict = {stu['id'] : stu for stu in students}
dnlds = {}
weirdids = {436635} # Test Student

os.makedirs(savedir, exist_ok=True)
os.chdir(savedir)

with canvas_session() as s:
    curi = 0
    while len(dnlds) < len(mystuds):
      try:
        start = time.time()
        signal.signal(signal.SIGINT, deferint)

        curi = (curi + 1) % len(curls)
        for rj in follow_next(s, curls[curi]):
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
                dnlds[sid] = numatt
                for att in sub['attachments']:
                    dst = Path(f'{codename(stu)}_{sid}_' + att['filename'])
                    if dst.exists():
                        print(dst, 'found')
                        continue
                    url = att['url']
                    print('Fetching', dst, '... ', end='', flush=True)
                    with s.get(url, stream=True) as fileget, open(dst, 'wb') as out:
                        shutil.copyfileobj(fileget.raw, out)
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

