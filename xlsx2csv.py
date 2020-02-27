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
        maxrow = max(n for n,row in enumerate(ws.values) if any(row))
        for row in ws.iter_rows(max_row=maxrow+1, values_only=True):
            maxcol = max((n for n,c in enumerate(row) if c is not None), default=-1)
            writer.writerow(row[:maxcol+1])
        fid.write('----------\n')

