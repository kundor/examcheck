#!/usr/bin/python3
import sys
import os
import re
from termcolor import colored
from canvas import codename, students, json, alphaonly

if not os.path.isfile('all-modder') or not os.path.isfile('students.json'):
    print('Must run in directory containing all-modder and students.json files')
    sys.exit(2)

if len(sys.argv) != 2:
    print('Exactly one argument needed: directory to find modders from info file')
    sys.exit(3)

mdir = sys.argv[1]
ifile = os.path.join(mdir, 'info')

if not os.path.isdir(mdir) or not os.path.isfile(ifile):
    print(f'Directory {mdir} does not exist or does not contain info file')
    sys.exit(4)

# Name equivalence classes
namequivs = [{'Abby', 'Abigail'},
             {'Addy', 'Addison'},
             {'Alex', 'Xander', 'Sandy', 'Alexander', 'Alexandra'},
             {'Andy', 'Drew', 'Andrew'},
             {'Ben', 'Benjamin'},
             {'Cal', 'Calvin'},
             {'Cam', 'Cameron'},
             {'Chris', 'Christopher'},
             {'Dan', 'Danny', 'Daniel'},
             {'Eddy', 'Edmund'},
             {'Ish', 'Ishmael', 'Ismael'},
             {'Jack', 'Jackson'},
             {'Jeff', 'Jeffrey'},
             {'Jon', 'Jonathan'},
             {'Kate', 'Katie', 'Katherine', 'Katharine'},
             {'Maddie', 'Madison'},
             {'Matt', 'Matthew'},
             {'Mike', 'Michael'},
             {'Nate', 'Nathan', 'Nathaniel'},
             {'Nick', 'Nicholas'},
             {'Livi', 'Olivia'},
             {'Becca', 'Rebecca'},
             {'Rob', 'Bob', 'Bobby', 'Robbie', 'Robert'},
             {'Steve', 'Stephen', 'Steven'},
             {'Theo', 'Teddy', 'Theodore'},
             {'Tom', 'Tommy', 'Thomas'},
             {'Will', 'Bill', 'Willy', 'William'},
             {'Zac', 'Zak', 'Zach', 'Zack', 'Zachary'}]
namequivs = [{nam.casefold() for nam in nams} for nams in namequivs]

studict = {codename(stu) : stu for stu in students}

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

numexact = nummou = numgrulk = numnotfound = numspacecase = numauto = numuser = numemail = numprompt = 0
with open(ifile, 'rt') as inf:
    oname = ''
    omodr = ''
    for line in inf:
        fields = line[:-1].split('\t')
        name = fields[0]
        name = name[:name.find('_')]
        modder = fields[6]
        if name == oname:
            if modder == omodr:
                print(f'{name} seen a second time; same modder {omodr}')
            else:
                print(f'{name} seen a second time; different modder {modder} vs. {omodr}')
            continue
        oname = name
        omodr = modder
        try:
            stu = studict[name]
        except KeyError:
            print(name, 'not found in students.json.')
            numnotfound += 1
            continue
        mflds = [name, stu['name']]
        moddbag = namebag(modder)
        oldbags = [namebag(omod) for omod in mflds[1:]]
        if modder in mflds[1:]:
            numexact += 1
        elif modder == 'Elizabeth L. Grulke':
            numgrulk += 1
        elif modder in ('Microsoft Office User', 'Microsoft Office 用户'):
            nummou += 1
        elif modder.strip().casefold() in [mname.strip().casefold() for mname in mflds]: # auto-approve
            numspacecase += 1
        elif moddbag and (any(moddbag.issubset(obag) for obag in oldbags) or oldbags[0].issubset(moddbag)):
            print(f'Adding modder {modder} for user {stu["name"]}')
            numauto += 1
        elif usernamematch(stu, modder):
            print(f'Adding "username" {modder} for user {stu["name"]}')
            numuser += 1
        elif emailmatch(stu, modder):
            print(f'Approving email {modder} for user {stu["name"]}')
            numemail += 1
        else:
            print(colored('Dunno about', 'red'), f'{modder} for user {stu["name"]}')
            numprompt += 1

print(numnotfound, 'not found')
print(numexact, 'exact matches')
print(numgrulk, 'unmodified')
print(nummou, 'Microsoft Office User')
print(numspacecase, 'space/case approvals')
print(numauto, 'auto-approvals')
print(numuser, 'username-type')
print(numemail, 'email')
print(numprompt, 'prompted')
total = numexact + nummou + numgrulk + numnotfound + numspacecase + numauto + numprompt
print(total, 'total')
