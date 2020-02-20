#!/usr/bin/python3 -i

import io
import os
import sys
from zipfile import ZipFile
from collections import namedtuple
from openpyxl import load_workbook
from uniquecells import thecells, cleanval

if len(sys.argv <= 1):
    sys.exit('Arguments: <submission zip file(s)> <original Module file>')
if len(sys.argv) > 2:
    subfiles = sys.argv[1:-1]
else:
    subfiles = [os.path.expanduser('~/Downloads/submissions.zip')]
    print(f'Using file {subfiles[0]}', file=sys.stderr)
origfile = sys.argv[-1]

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



