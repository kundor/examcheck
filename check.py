#!/usr/bin/python3

import io
import os
import sys
import subprocess
from zipfile import ZipFile, BadZipFile
from collections import namedtuple
from openpyxl import load_workbook
from uniquecells import thecells, cleanval
from allgrades import allgrades
from modderupdate import checkmodder, Status, modders, studict
import IPython
from traitlets.config import get_config

if len(sys.argv) <= 2:
    sys.exit('Arguments: <quizid(s)> <submission zip file(s)> <original Module file>')
arg = 1

quizids = []
while arg < len(sys.argv) and sys.argv[arg].isnumeric():
    quizids.append(int(sys.argv[arg]))
    arg += 1
if not quizids:
    sys.exit(f'Could not find any quiz IDs. Usage: {sys.argv[0]} <quizid(s)> <submission zip file(s)> <original Module file>')

subfiles = []
if arg < len(sys.argv) - 1:
    subfiles = sys.argv[arg:-1]
else:
    subfiles = [os.path.expanduser('~/Downloads/submissions.zip')]

origfile = sys.argv[-1]

print(f'Using quiz IDs {quizids}, submission zips {subfiles}, original file {origfile}', file=sys.stderr)

sys.excepthook = IPython.core.ultratb.FormattedTB(mode='Verbose', color_scheme='Linux', call_pdb=1)

Info = namedtuple('Info', ('filename', 'creation', 'creator', 'modified', 'modder'))

def getinfo(workbook):
    return Info(filename,
                workbook.properties.created,
                workbook.properties.creator,
                workbook.properties.modified,
                workbook.properties.last_modified_by or '')

origwb = load_workbook(origfile, read_only=True)
origcells = thecells(origwb)
originfo = getinfo(origwb)
origwb.close()

cellfiles = {}
infos = []
grades = allgrades(quizids)

for subfile in subfiles:
    with ZipFile(subfile, 'r') as subs:
        for filename in sorted(subs.namelist()):
            if filename.endswith('.xlsx'):
                fdata = io.BytesIO(subs.read(filename))
            elif filename.endswith('.xls'):
                print(f'Converting {filename} to xlsx', file=sys.stderr)
                subs.extract(filename)
                subprocess.run(['libreoffice', '--headless', '--convert-to', 'xlsx', filename])
                fdata = open(filename + 'x', 'rb')
            else:
                print('Not a xlsx file: ' + filename, file=sys.stderr)
                continue
            codename = filename[:filename.find('_')]
            try:
                wb = load_workbook(fdata, read_only=True)
            except BadZipFile as e:
                print(filename, 'is not a zip file?', e, file=sys.stderr)
                continue
            infos.append(getinfo(wb))
            with open(codename + '.csv', 'wt') as csv:
                for ws in wb.worksheets:
                    ws.reset_dimensions()
                    for row in ws.rows:
                        print(','.join(str(c.value) if c.value is not None else '' for c in row).rstrip(','), file=csv)
                        for c in row:
                            if c.value is not None:
                                cval = cleanval(c.value)
                                if cval not in origcells:
                                    if cval not in cellfiles:
                                        cellfiles[cval] = [filename]
                                    else:
                                        cellfiles[cval].append(filename)
                    print('----------', file=csv)
            wb.close()
            fdata.close()

for info in infos:
    # Update all modder names afterward, so the long conversion process isn't held up by prompts
    codename = info.filename[:info.filename.find('_')]
    stat = checkmodder(codename, info.modder)
    # Status.Found, Status.Boo, Status.DNE, Status.Approved, Status.Unknown
    if stat is Status.DNE:
        continue
    stu = studict[codename]
    if stat is Status.Unknown:
        addit = input(f'User {stu["name"]}: modder {info.modder}. Add? ')
        if addit.lower() in {'y', 'yes'}:
            modders[codename].append(info.modder)




c = get_config()
c.InteractiveShellEmbed.colors = "Linux"
IPython.embed(config=c)
