#!/usr/bin/python3

from colorama import Fore
import IPython
from canvas import *
from textwrap import TextWrapper
from shutil import get_terminal_size
from operator import itemgetter
import icdiff

sys.excepthook = IPython.core.ultratb.FormattedTB(mode='Verbose', color_scheme='Linux')

def too_old(oldstamp, newstamp):
    return newstamp - oldstamp > 4*30*24*60*60 # 4 months

def semester_break(oldstamp, newstamp):
    theyear = time.gmtime()[0]
    sembounds = [date(theyear, 1, 1), date(theyear, 5, 5)] # January 1, May 5
    old = date.fromtimestamp(oldstamp)
    new = date.fromtimestamp(newstamp)
    sembnd = max(bnd for bnd in sembounds if bnd < new)
    return old < sembnd

def ask_wipe():
    info_files = ['students.json',
            'sections.json',
            'teachers.json',
            'groups.json',
            'exams.json',
            'uploads.json',
            'allnames',
            'all-modder',
            'instructor-sections']
    now = time.time()
    try:
        newest = max(os.path.getmtime(info) for info in info_files if os.path.exists(info))
    except ValueError:
        print('No old data')
        return
    if too_old(newest, now) or semester_break(newest, now):
        if yesno('It might be a new semester. Wipe data and start fresh? '):
            for info in info_files:
                os.remove(info)
        else:
            print('Not removing old data.')

def backupname(filename):
    """Change filename.ext to filename1.ext, incrementing until it doesn't exist"""
    base, ext = os.path.splitext(filename)
    num = 1
    while os.path.exists(f'{base}{num}{ext}'):
        num += 1
    return f'{base}{num}{ext}'

class TabLoader:
    def __init__(self, *keys, varlength=False):
        self.keys = keys
        self.varlength = varlength
    def __call__(self, fid):
        data = []
        for line in fid:
            fields = line.rstrip().split('\t')
            if self.varlength:
                fields = fields[:len(self.keys)-1] + [fields[len(self.keys)-1:]]
            data.append(dict(zip(self.keys, fields)))
        return data

def prepend(pre, lines):
    return pre + f'\n{pre}'.join(lines)

def maxlen(*args):
    return max(len(str(arg)) for arg in args)

def colordiff(old, new, width):
    """Return highlighted versions of strings old and new, wrapped to width"""
    cd = icdiff.ConsoleDiff(wrapcolumn=width-2, cols=2*width+10)
    lines = cd.make_table([old], [new])
    hlold = []
    hlnew = []
    for line in lines:
        oldend = line.find(' '*5)
        hlold += [line[:oldend]]
        newbeg = line.rstrip().rfind(' '*5) + 5
        hlnew += [line[newbeg:]]
    return prepend('- ', hlold), prepend('+ ', hlnew)

def wrapdict(label, rec, keys, width, maxkeylen):
    """Print key: value blocks, wrapping preferentially between keys"""
    blocks = [f'{label:<{maxkeylen+2}}']
    blocks += [f'{key}: {rec[key]}' for key in keys]
    wrapblocks(blocks, width)

def wrapchanged(label, old, new, keys, width):
    oldstr = ''
    newstr = ''
    diff = False
    for key in keys:
        if old[key] != new[key] or key == 'name':
            if isinstance(old[key], list):
                if sorted(old[key]) == sorted(new[key]):
                    continue
            ml = maxlen(old[key], new[key])
            oldstr += f'{str(old[key]):{ml}}  '
            newstr += f'{str(new[key]):{ml}}  '
            if old[key] != new[key]:
                diff = True
    if not diff:
        return False # no real changes, just ordering
    oldstr, newstr = colordiff(oldstr[:-2], newstr[:-2], width)
    print(label)
    print(oldstr)
    print(newstr)
    return True

def wrapblocks(blocks, width, indent="    "):
    # todo: figure out value lengths (from all records) so that all the entries are lined up the same way
    TW = TextWrapper(width=width, initial_indent=indent, subsequent_indent=indent + "  ")
    curwidth = 0
    sep = '  '
    for b in blocks:
        if not curwidth:
            print(b, end='')
            curwidth = len(b)
        elif curwidth + len(b) + 2 <= width:
            print(sep + b, end='')
            curwidth += len(b) + len(sep)
        elif len(b) <= width - len(indent):
            print('\n' + indent + b, end='')
            curwidth = len(indent) + len(b)
        else:
            wrapt = TW.wrap(b)
            print(*('\n' + line for line in wrapt), end='')
            curwidth = len(wrapt[-1])
        sep = ', '
    print()

def comparelists(oldlist, newlist, primary_key=None):
    """Print a diff of lists of dicts (assumed to have the same keys).
    Values are assumed to be strings, numbers, or lists."""
    thekeys = oldlist[0].keys() # Might want to check if all entries have same keys,
    # and use the union or the most common set of keys
    if len({frozenset(o.keys()) for o in oldlist} | {frozenset(n.keys()) for n in newlist}) != 1:
        print('Warning: not all records have the same keys!')
    if primary_key is None:
        good_keys = ['id', 'codename', 'name']
        try:
            primary_key = next(gk for gk in good_keys if gk in thekeys)
        except StopIteration:
            primary_key = next(k for k in thekeys) # dict_keys aren't iterators, durr
    width, _ = get_terminal_size()
    old = {o[primary_key]: o for o in oldlist}
    new = {n[primary_key]: n for n in newlist}
    maxkeylen = max(len(str(k)) for k in old.keys() | new.keys())
    realdiff = False
    if old.keys() - new.keys():
        print(Fore.RED + 'Only in old:' + Fore.RESET)
        for key in old.keys() - new.keys():
            wrapdict(key, old[key], thekeys - {primary_key}, width, maxkeylen)
        realdiff = True
    if new.keys() - old.keys():
        print(Fore.GREEN + 'Only in new:' + Fore.RESET)
        for key in new.keys() - old.keys():
            wrapdict(key, new[key], thekeys - {primary_key}, width, maxkeylen)
        realdiff = True
    print(Fore.YELLOW + 'Changes:' + Fore.RESET)
    for key in old.keys() & new.keys():
        if old[key] != new[key]:
            if wrapchanged(key, old[key], new[key], thekeys - {primary_key}, width):
                realdiff = True
    return realdiff

def diffwrite(filename, data, as_string=None, loader=json.load):
    if not as_string:
        as_string = json.dumps(data, indent=2)
    try:
        with open(filename, 'xt') as fid: # write, failing if it exists
            fid.write(as_string)
        return
    except FileExistsError:
        with open(filename) as fil:
            old_data = loader(fil)
        print(f' ** {filename} **')
        if not comparelists(old_data, data):
            print('No difference, doing nothing')
            return
        while True:
            answer = input('Clobber old file? [B]ackup/[c]lobber/do [n]othing: ').lower()
            if 'backup'.startswith(answer): # includes blank answer
                bkup = backupname(filename)
                print(f'Moving {filename} to {bkup}')
                os.rename(filename, bkup)
                with open(filename, 'xt') as fid:
                    fid.write(as_string)
                return
            if 'clobber'.startswith(answer):
                print('Clobbering old file')
                with open(filename, 'wt') as fid:
                    fid.write(as_string)
                return
            if 'nothing'.startswith(answer):
                print('Discarding new data')
                return
            print(f"I don't understand '{answer}'!")

def namelist(stuids, studict, color='', addsec=False):
    """Given a list of IDs, print names [and sections if requested] in given color,
       if found in studict; otherwise just the id."""
    reset = ''
    if color:
        reset = Fore.RESET
    names = []
    for stu in stuids:
        try:
            thename = color + studict[stu]['name'] + reset
            if addsec:
                thename += f" ({studict[stu]['section']})"
            names += [thename]
        except KeyError:
            names += [color + str(stu) + reset]
    return ', '.join(names)

def askkey(dikt, key, title):
    """Return dikt[key], prompting user if key isn't found"""
    if key not in dikt:
        print(f"Key '{key}' not found. Which group is {title}?")
        print('\n'.join(dikt.keys()))
        key = input('? ')
    if key not in dikt:
        print('OK FORGET IT')
        return
    return dikt[key]

def isodate(jsondate):
    if not jsondate:
        return
    return isoparse(jsondate).astimezone().date().isoformat()

def restrict_boo(teachers):
    """Remove coordinator from all sections unless she's the only teacher"""
    osecs = [] # all sections with a teacher other than Boo
    for t in teachers:
        if t['name'] == COORDINATOR:
            continue
        osecs += t['sections']
    for t in teachers:
        if t['name'] == COORDINATOR:
            t['sections'] = [sec for sec in t['sections'] if sec not in osecs]

def confirm_sections(sectch, teachers):
    """Prompt for any changes to teacher assignments"""
    teachnames = [t['name'] for t in teachers]
    for sec in sorted(sectch):
       print(f"{sec}: {sectch[sec]}")

    while True:
        secnum = input("Change section? ")
        if not secnum:
            break
        if secnum not in sectch:
            print("Not a section. (Enter nothing to continue)")
            continue
        newname = input('Correct teacher? ')
        if newname not in teachnames:
            print('Not a teacher?!?')
            continue
        oldteacher = next(t for t in teachers if t['name'] == sectch[secnum])
        newteacher = next(t for t in teachers if t['name'] == newname)
        thesection = next(sec for sec in oldteacher['sections'] if sec[2] == secnum)
        oldteacher['sections'].remove(thesection)
        newteacher['sections'].append(thesection)

def format_sections(sections):
    sectiondat = json.dumps(sections, sort_keys=True, indent=1)
    sectiondat = re.sub('\n   ', ' ', sectiondat)
    sectiondat = re.sub('\n  \]', ']', sectiondat)
    sectiondat = re.sub('\[ ', '[', sectiondat)
    sectiondat = re.sub('\n  "id"', '"id"', sectiondat)
    sectiondat = re.sub('\[\n {', '[{', sectiondat)
    sectiondat = re.sub('"\n }', '"}', sectiondat)
    return sectiondat

def get_enrolled(session, enroll_type):
    params = {'include[]': 'enrollments', 'enrollment_type[]': enroll_type}
    enrolt = []
    for courseid in courseids:
        curl = f'courses/{courseid}/users'
        enrolt = sum(follow_next(session, curl, params=params), enrolt)
    return enrolt

def get_assignments(session, courseid, groupid):
    curl = canvasbase + f'courses/{courseid}/assignment_groups/{groupid}'
    with session.get(curl, params={'include[]': 'assignments'}) as response:
        asses = response.json()['assignments']
    keys = ('id', 'due_at', 'unlock_at', 'lock_at', 'name', 'quiz_id', 'course_id')
    return [{key : a.get(key) for key in keys} for a in asses]

def get_overrides(session, courseid, assid):
    curl = canvasbase + f'courses/{courseid}/assignments/{assid}/overrides'
    with session.get(curl) as response:
        return response.json()

def fetch_teachers(session):
    teachers = []
    rawteach = get_enrolled(session, 'teacher')
    id_names = {(tch['id'], tch['name']) for tch in rawteach}
    assert len(id_names) == len({idn[0] for idn in id_names}) == len({idn[1] for idn in id_names}) 
    for (tID, tname) in id_names:
        thesections = []
        for tch in rawteach:
            if tch['id'] == tID:
                thesections += [(ee['course_id'],
                                 ee['course_section_id'],
                                 ee['sis_section_id'][17:21].rstrip('-')) for ee in tch['enrollments']]
        thesections = sorted(thesections, key=itemgetter(2))
        teachers += [{'id': tID, 'name': tname, 'sections': thesections}]

    restrict_boo(teachers)
    sectch = {sec[2]: tch['name'] for tch in teachers for sec in tch['sections']}
    confirm_sections(sectch, teachers)

    teacherdat = json.dumps(teachers, indent=2).replace('{\n    "id"', '{ "id"')
    teacherdat = re.sub(r'\[\s*([0-9]*),\s*("[\w-]*")\s*\]', r'[ \1, \2 ]', teacherdat)
    diffwrite('teachers.json', teachers, teacherdat)
    # Fix: sometimes extra teachers are present
    return teachers, sectch

def fetch_students(session):
    stuen = get_enrolled(session, 'student')
    keys = ['id', 'name', 'sortable_name', 'sis_user_id', 'login_id', 'email']
    studentinf = [dict(section=stu['enrollments'][0]['sis_section_id'][17:21].rstrip('-'),
                       course_id=stu['enrollments'][0]['course_id'],
                       **{k: stu[k] for k in keys}) for stu in stuen]
    diffwrite('students.json', studentinf)
    return studentinf

def fetch_sections(session, studentinf, sectch, studict):
    sections = []
    keys = ['id', 'name', 'sis_section_id', 'course_id']
    for courseid in courseids:
        curl = canvasbase + f'courses/{courseid}/sections'
        with session.get(curl, params={'include[]': 'students'}) as response:
            rj = response.json()
        sections += [dict(allstudents=[st['id'] for st in rec['students']],
                     students=sorted(stu['id'] for stu in studentinf if stu['section'] == rec['name'][10:]),
                     teacher=sectch[rec['name'][10:]],
                     **{k : rec[k] for k in keys}) for rec in rj if rec['students']]
    for sec in sections:
        allstus = set(sec['allstudents'])
        secstus = set(sec['students'])
        if allstus != secstus:
            msg = f'Section {sec["name"]}: not including {namelist(allstus - secstus, studict, Fore.RED, True)}'
            if secstus - allstus:
                msg += f'also including {namelist(secstus - allstus, studict, Fore.GREEN, False)}'
            print(msg)
        del sec['allstudents']
    diffwrite('sections.json', sections, format_sections(sections))
    return sections

def fetch_groups(session):
    allgroups = []
    examIDs = []
    uploadIDs = []
    finalIDs = []
    for courseid in courseids:
        curl = canvasbase + f'courses/{courseid}/assignment_groups'
        with session.get(curl) as response:
            assgroups = response.json()
        for ag in assgroups:
            ag['course_id'] = courseid
        agm = {ag['name'] : ag['id'] for ag in assgroups}
        examid = askkey(agm, 'Module Exams', 'module exams')
        uploadid = askkey(agm, 'Exam Spreadsheet Uploads', 'spreadsheet uploads')
        finalid = askkey(agm, 'Final Exam', 'the final exam')
        if examid:
            examIDs.append((courseid, examid))
        if uploadid:
            uploadIDs.append((courseid, uploadid))
        if finalid:
            finalIDs.append((courseid, finalid))
        allgroups += assgroups
    diffwrite('groups.json', allgroups)
    return examIDs, uploadIDs, finalIDs

def fetch_uploads(session, uploadsIDs):
    uploads = []
    for (cID, gID) in uploadsIDs:
        rawuploads = get_assignments(session, cID, gID)
        uploads += [{'name': up['name'],
            'id': up['id'],
            'date': isodate(up['lock_at']),
            'course_id': cID}
            for up in rawuploads]
    diffwrite('uploads.json', uploads)
    return uploads

def fetch_exams(session, course_group_IDs):
    exams = []
    for (cID, gID) in course_group_IDs:
        if gID:
            exams += get_assignments(session, cID, gID)
    badindices = []
    for n, exam in enumerate(exams):
        if not exam['quiz_id']:
            badindices.append(n)
            continue 
        overrides = get_overrides(session, exam['course_id'], exam['id']) 
        unlock = isodate(exam['unlock_at'])
        lock = isodate(exam['lock_at'])
        duedates = {isodate(o['due_at']) for o in overrides if o['due_at']}
        if unlock:
            duedates.add(unlock)
        if lock:
            duedates.add(lock)
        if len(duedates) == 1: 
            exam['date'] = duedates.pop()
        else:
            print(f'Exam {exam["name"]}: Could not determine date. '
                  f'Unlocks at {unlock}, locks at {lock}, overrides '
                    + ', '.join(duedates))
            exam['date'] = None
    for n in sorted(badindices, reverse=True):
        del exams[n]
    diffwrite('exams.json', exams)
    return exams

if __name__ == '__main__':
    ask_wipe()
    with canvas_session() as session:
        teachers, sectch = fetch_teachers(session)
        studentinf = fetch_students(session)
        studict = {stu['id'] : stu for stu in studentinf}
        sections = fetch_sections(session, studentinf, sectch, studict)
        examsIDs, uploadsIDs, finalIDs = fetch_groups(session)
        # pairs with course_id, group_id
        uploads = fetch_uploads(session, uploadsIDs) 
        exams = fetch_exams(session, [*examsIDs, *finalIDs])

    allnames = [{'sid': stu['id'], 'name': stu['name'], 'section': stu['section']} for stu in studentinf]
    allnamestr = '\n'.join('\t'.join(str(s[k]) for k in ('sid', 'name', 'section')) for s in allnames) + '\n'
    diffwrite('allnames', allnames, allnamestr, loader=TabLoader('sid', 'name', 'section'))

    instsec = [{'name': tch['name'], 'sections': sorted(sec[2] for sec in tch['sections'])} for tch in teachers]
    instsecstr = '\n'.join(tch['name'] + '\t' + '\t'.join(tch['sections']) for tch in instsec) + '\n'
    diffwrite('instructor-sections', instsec, instsecstr, loader=TabLoader('name', 'sections', varlength=True))

    if yesno('Create all-modder with full names? '):
        with open('all-modder', 'wt') as fid:
            for stu in studentinf:
                fid.write(f"{stu['id']}\t{stu['name']}\n")
    else:
        print('Not making all-modder. (`cut -f -2 allnames > all-modder` has same effect)')

    IPython.start_ipython(['--quick', '--no-banner'], user_ns=globals())
