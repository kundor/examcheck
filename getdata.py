#!/usr/bin/python3 -i

import re
from colorama import Fore
from canvas import *

with canvas_session() as s:
    curl = canvasbase + f'courses/{courseid}/users'
    s.params = {'per_page': 100, 'include[]': 'enrollments', 'enrollment_type[]': 'teacher'}

    with s.get(curl) as response:
        rj = response.json()
    teachers = []
    for tch in rj:
        try:
            teachers += [{'id': tch['id'], 'name': tch['name'], 'sections': [[ee['course_section_id'], ee['sis_section_id'][17:21].rstrip('-')] for ee in tch['enrollments']]}]
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
            t['sections'] = [sec for sec in t['sections'] if sec not in osecs]

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
    with open('teachers.json', 'wt') as fid:
        fid.write(teacherdat)
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
    with open('students.json', 'wt') as fid:
        json.dump(studentinf, fid, indent=2)

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
                     students=[stu['id'] for stu in studentinf if stu['section'] == rec['name'][10:]],
                     teacher=next(t['name'] for t in teachers if rec['id'] in [ts[0] for ts in t['sections']]),
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
    with open('sections.json', 'wt') as fid:
        fid.write(sectiondat)


    curl = canvasbase + f'courses/{courseid}/assignments'

    s.params = {'per_page': 100, 'search_term': 'Upload'}
    with s.get(curl) as response:
        rj = response.json()
    moduploads = [{k : ass[k] for k in ('due_at', 'id', 'name')} for ass in rj]

    s.params = {'per_page': 100, 'search_term': 'Exam'}
    with s.get(curl) as response:
        rj = response.json()
    exams = [{k : ass[k] for k in ('due_at', 'id', 'name', 'quiz_id')} for ass in rj if 'quiz_id' in ass]

with open('allnames', 'wt') as fid:
    for stu in studentinf:
        fid.write(codename(stu) + '\t' + stu['name'] + '\t' + stu['section'] + '\n')

with open('instructor-sections', 'wt') as fid:
    for tch in teachers:
        fid.write(tch['name'] + '\t' + '\t'.join(sorted(sec[1] for sec in tch['sections'])) + '\n')
   
if input('Create all-modder with full names?').casefold() in {'y', 'yes'}:
    with open('all-modder', 'wt') as fid:
        for stu in studentinf:
            fid.write(codename(stu) + '\t' + stu['name'] + '\n')
else:
    print('Not making all-modder')

