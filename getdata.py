#!/usr/bin/python3 -i

import re
from colorama import Fore
import IPython
from canvas import *
from textwrap import TextWrapper
from shutil import get_terminal_size
from operator import itemgetter

sys.excepthook = IPython.core.ultratb.FormattedTB(mode='Verbose', color_scheme='Linux', call_pdb=1)

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

def wrapdict(label, rec, keys, width, maxkeylen):
    """Print key: value blocks, wrapping preferentially between keys"""
    blocks = [f'{label:<{maxkeylen+2}}']
    blocks += [f'{key}: {rec[key]}' for key in keys]
    wrapblocks(blocks, width)

def wrapchanged(label, old, new, keys, width, maxkeylen):
    blocks = [f'{label:<{maxkeylen+2}}']
    for key in keys:
        if old[key] != new[key]:
            if isinstance(old[key], list):
                if sorted(old[key]) == sorted(new[key]):
                    continue
            blocks.append(f'{key}: {old[key]} -> {new[key]}')
    wrapblocks(blocks, width)

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
    if old.keys() - new.keys():
        print(Fore.RED + 'Only in old:' + Fore.RESET)
        for key in old.keys() - new.keys():
            wrapdict(key, old[key], thekeys - {primary_key}, width, maxkeylen)
    if new.keys() - old.keys():
        print(Fore.GREEN + 'Only in new:' + Fore.RESET)
        for key in new.keys() - old.keys():
            wrapdict(key, new[key], thekeys - {primary_key}, width, maxkeylen)
    print(Fore.YELLOW + 'Changes:' + Fore.RESET)
    for key in old.keys() & new.keys():
        if old[key] != new[key]:
            wrapchanged(key, old[key], new[key], thekeys - {primary_key}, width, maxkeylen)

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
        comparelists(old_data, data)
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


with canvas_session() as s:
    curl = canvasbase + f'courses/{courseid}/users'
    s.params = {'per_page': 100, 'include[]': 'enrollments', 'enrollment_type[]': 'teacher'}

    with s.get(curl) as response:
        rj = response.json()
    teachers = []
    for tch in rj:
        try:
            thesections = sorted(([ee['course_section_id'], ee['sis_section_id'][17:21].rstrip('-')] for ee in tch['enrollments']), key=itemgetter(1))
            teachers += [{'id': tch['id'], 'name': tch['name'], 'sections': thesections}]
        except KeyError:
            print('Problem with record:', tch)

    # Boo is in every section
    osecs = []
    for t in teachers:
        if t['name'] == 'Elizabeth Grulke':
            continue
        osecs += t['sections']
    for t in teachers:
        if t['name'] == 'Elizabeth Grulke':
            t['sections'] = sorted((sec for sec in t['sections'] if sec not in osecs), key=itemgetter(1))

    sectch = {sec[1]: tch['name'] for tch in teachers for sec in tch['sections']}
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
        if newname not in sectch.values():
            print('Not a teacher?!?')
            continue
        oldteacher = next(t for t in teachers if t['name'] == sectch[secnum])
        newteacher = next(t for t in teachers if t['name'] == newname)
        thesection = next(sec for sec in oldteacher['sections'] if sec[1] == secnum)
        oldteacher['sections'].remove(thesection)
        newteacher['sections'].append(thesection)

    teacherdat = json.dumps(teachers, indent=2).replace('{\n    "id"', '{ "id"')
    teacherdat = re.sub(r'\[\s*([0-9]*),\s*("[\w-]*")\s*\]', r'[ \1, \2 ]', teacherdat)
    diffwrite('teachers.json', teachers, teacherdat)
    # Fix: sometimes extra teachers are present


    s.params['enrollment_type[]'] = 'student'
    stuen = []
    while curl:
        with s.get(curl) as response:
            stuen += response.json()
            curl = response.links.get('next', {}).get('url')
    keys = ['id', 'name', 'sortable_name', 'sis_user_id', 'login_id']
    studentinf = [dict(section=stu['enrollments'][0]['sis_section_id'][17:21].rstrip('-'),
                       **{k: stu[k] for k in keys}) for stu in stuen] 
    diffwrite('students.json', studentinf)

    studict = {stu['id'] : stu for stu in studentinf}

    def namelist(stuids, color='', addsec=False):
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

    curl = canvasbase + f'courses/{courseid}/sections'
    s.params = {'per_page': 100, 'include[]': 'students'}

    with s.get(curl) as response:
        rj = response.json()
    keys = ['id', 'name', 'sis_section_id']
    sections = [dict(allstudents=[st['id'] for st in rec['students']],
                     students=sorted(stu['id'] for stu in studentinf if stu['section'] == rec['name'][10:]),
                     teacher=sectch[rec['name'][10:]],
                     **{k : rec[k] for k in keys}) for rec in rj if rec['students']]
    for sec in sections:
        allstus = set(sec['allstudents'])
        secstus = set(sec['students'])
        if allstus != secstus:
            msg = f'Section {sec["name"]}: not including {namelist(allstus - secstus, Fore.RED, True)}'
            if secstus - allstus:
                msg += f'also including {namelist(secstus - allstus, Fore.GREEN, False)}'
            print(msg)
        del sec['allstudents']
    sectiondat = json.dumps(sections, sort_keys=True, indent=1)
    sectiondat = re.sub('\n   ', ' ', sectiondat)
    sectiondat = re.sub('\n  \]', ']', sectiondat)
    sectiondat = re.sub('\[ ', '[', sectiondat)
    sectiondat = re.sub('\n  "id"', '"id"', sectiondat)
    sectiondat = re.sub('\[\n {', '[{', sectiondat)
    sectiondat = re.sub('"\n }', '"}', sectiondat)
    diffwrite('sections.json', sections, sectiondat)

    curl = canvasbase + f'courses/{courseid}/assignments'

    s.params = {'per_page': 100, 'search_term': 'Upload'}
    with s.get(curl) as response:
        rj = response.json()
    moduploads = [{k : ass[k] for k in ('due_at', 'id', 'name')} for ass in rj]

    s.params = {'per_page': 100, 'search_term': 'Exam'}
    with s.get(curl) as response:
        rj = response.json()
    exams = [{k : ass[k] for k in ('due_at', 'id', 'name', 'quiz_id')} for ass in rj if 'quiz_id' in ass]

allnames = [{'codename': codename(stu), 'name': stu['name'], 'section': stu['section']} for stu in studentinf]
allnamestr = '\n'.join('\t'.join(s[k] for k in ('codename', 'name', 'section')) for s in allnames) + '\n'
diffwrite('allnames', allnames, allnamestr, loader=TabLoader('codename', 'name', 'section'))

instsec = [{'name': tch['name'], 'sections': sorted(sec[1] for sec in tch['sections'])} for tch in teachers]
instsecstr = '\n'.join(tch['name'] + '\t' + '\t'.join(tch['sections']) for tch in instsec) + '\n'
diffwrite('instructor-sections', instsec, instsecstr, loader=TabLoader('name', 'sections', varlength=True))

if input('Create all-modder with full names? ').casefold() in {'y', 'yes'}:
    with open('all-modder', 'wt') as fid:
        for stu in studentinf:
            fid.write(codename(stu) + '\t' + stu['name'] + '\n')
else:
    print('Not making all-modder. (`cut -f -2 allnames > all-modder` has same effect)')

