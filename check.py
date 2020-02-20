#!/usr/bin/python3 -i

import io
import os
import sys
from zipfile import ZipFile
from collections import namedtuple
from openpyxl import load_workbook
from uniquecells import thecells, cleanval
import IPython
from traitlets.config import get_config

sys.excepthook = IPython.core.ultratb.FormattedTB(mode='Verbose', color_scheme='Linux', call_pdb=1)

if len(sys.argv <= 2):
    sys.exit('Arguments: <quizid(s)> <submission zip file(s)> <original Module file>')
arg = 1

quizids = []
while arg < len(sys.argv) and sys.argv[arg].isnumeric():
    quizids.append(int(sys.argv[arg]))
    arg += 1
if not quizids:
    sys.exit(f'Could not find any quiz IDs. Usage: {sys.argv[0]} <quizid(s)> <submission zip file(s)> <original Module file>')a

subfiles = []
if arg < len(sys.argv) - 1:
    subfiles = sys.argv[arg:-1]
else:
    subfiles = [os.path.expanduser('~/Downloads/submissions.zip')]

origfile = sys.argv[-1]

print(f'Using quiz IDs {quizids}, submission zips {subfiles}, original file {origfile}', file=sys.stderr)

Info = namedtuple('Info', ('filename', 'creation', 'creator', 'modified', 'modder')
origcells = thecells(origfile)
cellfiles = {}
info = []

for subfile in subfiles:
    with ZipFile(subfile, 'r') as subs:
        for filename in sorted(subs.namelist()):
            if not filename.endswith('.xlsx'):
                print('Not a xlsx file: ' + filename, file=sys.stderr)
                continue
            fdata = io.BytesIO(subs.read(filename))
            codename = filename[:filename.find('_')]
            wb = load_workbook(fdata, read_only=True)
            info.append(Info(filename,
                             wb.properties.created,
                             wb.properties.creator,
                             wb.properties.modified,
                             wb.properties.last_modified_by or ''))
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

c = get_config()
c.InteractiveShellEmbed.colors = "Linux"
IPython.embed(config=c)
