#!/usr/bin/python3

import sys
from openpyxl import load_workbook

wb = load_workbook(filename=sys.argv[1], read_only=True)

for ws in wb.worksheets:
#    ws.max_row = ws.max_column = None
    ws.reset_dimensions()
    for row in ws.rows:
        print(','.join(str(c.value) if c.value is not None else '' for c in row))
    print('----------')

