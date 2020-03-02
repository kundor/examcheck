#!/usr/bin/python3
import sys
import os
import re
from enum import Enum
from collections import namedtuple
from canvas import codename, students, alphaonly, load_file

Status = Enum('Status', ('Found', 'Approved', 'DNE', 'Boo', 'Unknown'))
FileInfo = namedtuple('FileInfo', ('codename', 'stuid', 'subid'))

# Name equivalence classes
namequivs = [{'Abby', 'Abigail'},
             {'Addy', 'Addison'},
             {'Alex', 'Xander', 'Sandy', 'Alexander', 'Alexandra'},
             {'Andy', 'Drew', 'Andrew'},
             {'Ben', 'Benjamin'},
             {'Cal', 'Calvin'},
             {'Cam', 'Cameron'},
             {'Charles', 'Charlie', 'Charly', 'Chuck'},
             {'Chris', 'Christopher'},
             {'Dan', 'Danny', 'Daniel'},
             {'Eddy', 'Edmund'},
             {'Ellie', 'Elizabeth', 'Beth', 'Liz'},
             {'Gabe', 'Gabriel'},
             {'Harry', 'Harold'},
             {'Ish', 'Ishmael', 'Ismael'},
             {'Jake', 'Jacob'},
             {'Jeff', 'Jeffrey'},
             {'Jack', 'Jackson', 'Jon', 'Jonny', 'John', 'Jonathan', 'Johnathon'},
             {'Joe', 'Joseph'},
             {'Josh', 'Joshua'},
             {'Kate', 'Katie', 'Katherine', 'Katharine'},
             {'Lili', 'Lily', 'Lilly', 'Lillian'},
             {'Maddie', 'Madison', 'Madeline', 'Madeleine'},
             {'Matt', 'Matthew'},
             {'Max', 'Maxwell'},
             {'Mike', 'Michael'},
             {'Mitch', 'Mitchell'},
             {'Nate', 'Nathan', 'Nathaniel'},
             {'Nic', 'Nicolas'},
             {'Nick', 'Nicholas'},
             {'Livi', 'Olivia'},
             {'Becca', 'Rebecca'},
             {'Rob', 'Bob', 'Bobby', 'Robbie', 'Robert'},
             {'Sam', 'Samuel', 'Sammy', 'Samantha'},
             {'Steve', 'Stephen', 'Steven'},
             {'Theo', 'Teddy', 'Theodore'},
             {'Tim', 'Timmy', 'Timothy', 'Timothee'},
             {'Tom', 'Tommy', 'Thomas'},
             {'Will', 'Bill', 'Willy', 'William'},
             {'Zac', 'Zak', 'Zach', 'Zack', 'Zachary'}]
namequivs = [{nam.casefold() for nam in nams} for nams in namequivs]

studict = {stu['id'] : stu for stu in students}

def fileinfo(filename):
    """Get the metadata included in Canvas-generated filenames"""
    codename, stuid, subid, *fn = filename.split('_')
    return FileInfo(codename, int(stuid), int(subid))

def namebag(name):
    name = re.sub("[,\./_-]", ' ', name.casefold()).replace("'", "").split()
    for n in range(len(name)):
        for i, nams in enumerate(namequivs):
            if name[n] in nams:
                name[n] = i
    # strings in name stand for themselves, integers stand for an equivalence class
    return set(name)

def congloms(names):
    """Stick together names in names, e.g. ['John', 'William', 'Harlow'] ->
       JohnWilliamHarlow, WilliamHarlow, Harlow, JWilliamHarlow, JWHarlow, JWH"""
    namegloms = []
    inits = ''
    for i in range(len(names)):
        conglom = ''.join(names[i:])
        namegloms.append(conglom)
        if inits:
            namegloms.append(inits + conglom)
        inits += names[i][0]
    if len(inits) > 1:
        namegloms.append(inits)
    return namegloms

def usernamematch(stu, name):
    """True for jodo[0-9]*, jdoe..., johnd, doejq, doejohn, etc."""
    if len(name.split()) != 1:
        return False
    prenum = name.rstrip('0123456789').casefold()
    k = len(prenum)
    if k < 4:
        return False
    if prenum == stu['login_id'][:4]:
        return True
    last, first = stu['sortable_name'].casefold().split(', ')
    firsts = congloms(first.split())
    lasts = congloms(last.split())

    for fn in firsts:
        fn = alphaonly(fn)
        if len(fn) < 2:
            continue
        for ln in lasts:
            ln = alphaonly(ln)
            if len(ln) < 2:
                continue
            for i in range(max(1, k - len(ln)), min(k, len(fn)) + 1):
                if prenum == fn[:i] + ln[:k - i]:
                    return True
            for i in range(max(1, k - len(ln) - 1), min(k, len(fn)) + 1):
                if re.fullmatch(fn[:i] + '[._-]' + ln[:k-i-1], prenum):
                    return True
            for i in range(max(1, k - len(fn)), min(k, len(ln)) + 1):
                if prenum == ln[:i] + fn[:k - i]:
                    return True
            for i in range(max(1, k - len(fn) - 1), min(k, len(ln)) + 1):
                if re.fullmatch(ln[:i] + '[._-]' + fn[:k-i-1], prenum):
                    return True

def emailmatch(stu, name):
    """See if a name seems to match username@domain for student. Only checks the part of name which appears to be an email"""
    if name.count('@') != 1:
        return False
    for nm in name.split():
        if '@' in nm:
            name = nm.strip('()[]<>"')
            break
    user, domain = name.split('@')
    if '.' not in domain:
        return False
    return usernamematch(stu, user)

def loadmod(fid):
    modders = {}
    for line in fid:
        mflds = line[:-1].split('\t')
        modders[int(mflds[0])] = mflds[1:]
    return modders

modders = load_file('all-modder', loadmod)

def checkmodder(sid, modder):
    try:
        stu = studict[sid]
    except KeyError:
        print(sid, 'not found in students.json.')
        return Status.DNE
    if sid not in modders:
        print(f'{sid} ({stu["name"]}) not found in all-modder')
        return Status.DNE
    moddbag = namebag(modder)
    oldbags = [namebag(omod) for omod in modders[sid]]
    if modder in modders[sid]:
        return Status.Found
    elif modder == 'Elizabeth L. Grulke':
        return Status.Boo
    elif modder in ('Microsoft Office User', 'Microsoft Office 用户'):
        return Status.Approved
    elif modder.strip().casefold() in [mname.strip().casefold() for mname in modders[sid]]: # auto-approve
        return Status.Approved
    elif moddbag and (any(moddbag.issubset(obag) for obag in oldbags) or oldbags[0].issubset(moddbag)):
        print(f'Adding modder {modder} for user {stu["name"]}')
        return Status.Approved
    elif usernamematch(stu, modder):
        print(f'Adding "username" {modder} for user {stu["name"]}')
        return Status.Approved
    elif emailmatch(stu, modder):
        print(f'Approving email {modder} for user {stu["name"]}')
        return Status.Approved
    return Status.Unknown

def checkadd(sid, modder):
    stat = checkmodder(sid, modder)
    if stat is Status.Approved:
        modders[sid].append(modder)
    elif stat is Status.Unknown:
        stuname = studict[sid]['name'] 
        addit = input(f'User {stuname}: modder {modder}. Add? ')
        if addit.lower() in {'y', 'yes'}:
            modders[sid].append(modder)
            return Status.Approved
    return stat

def writeout(basename='allmod'):
    n = 1
    while True:
        try:
            with open(f'{basename}{n}', 'xt') as new:
                for sid, mods in modders.items():
                    new.write(f'{sid}\t' + '\t'.join(mods) + '\n')
        except FileExistsError:
            n += 1
            continue
        break

if __name__ == '__main__':
    if not os.path.isfile('all-modder') or not os.path.isfile('students.json'):
        sys.exit('Must run in directory containing all-modder and students.json files')

    if len(sys.argv) != 2:
        sys.exit('Exactly one argument needed: directory to find modders from info file')

    mdir = sys.argv[1]
    ifile = os.path.join(mdir, 'info')

    if not os.path.isdir(mdir) or not os.path.isfile(ifile):
        sys.exit(f'Directory {mdir} does not exist or does not contain info file')

    with open(ifile, 'rt') as inf:
        osid = 0
        omodr = ''
        for line in inf:
            fields = line[:-1].split('\t')
            name, stuid, subid = fileinfo(fields[0])
            modder = fields[6]
            if stuid == osid:
                if modder == omodr:
                    print(f'{name} seen a second time; same modder {omodr}')
                else:
                    print(f'{name} seen a second time; different modder {modder} vs. {omodr}')
                continue
            osid = stuid
            omodr = modder
            stat = checkadd(stuid, modder)
    writeout()
