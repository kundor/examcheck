#!/usr/bin/python3

import os
import csv
import sys
from openpyxl import load_workbook

wb = load_workbook(filename=sys.argv[1], read_only=True)

if len(sys.argv) == 3:
    outfile = sys.argv[2]
elif len(sys.argv) > 3:
    sys.exit('Max two arguments, infile outfile')
else:
    root, ext = os.path.splitext(sys.argv[1])
    outfile = root + '.csv'

csv.register_dialect('newline', lineterminator='\n')

with open(outfile, 'w', newline='') as fid:
    writer = csv.writer(fid, 'newline')
    for ws in wb.worksheets:
        ws.reset_dimensions()
        maxrow = max(n for n,r in enumerate(ws.rows) if any(c.value for c in r))
        for row in ws.iter_rows(max_row=maxrow+1):
            maxcol = max((n for n,c in enumerate(row) if c.value is not None), default=-1)
            writer.writerow(c.value for c in row[:maxcol+1])
        fid.write('----------\n')

