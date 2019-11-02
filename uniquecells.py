#!/usr/bin/python3

import sys
import glob
import re
from openpyxl import load_workbook

refpat = re.compile(r"\$?[A-Z]{1,3}\$?[0-9]{1,5}")
colpat = re.compile(r"(\$?[A-Z]{1,3}):\1")
rowpat = re.compile(r"(\$?[0-9]{1,5}):\1")

def thecells(filename):
    contents = set()
    wb = load_workbook(filename=filename, read_only=True)
    for ws in wb.worksheets:
        #ws.reset_dimensions()
        for row in ws.rows:
            for c in row:
                if c.value is not None:
                    cval = refpat.sub('REF', str(c.value))
                    cval = colpat.sub('COL', cval)
                    cval = rowpat.sub('ROW', cval)
                    contents.add(cval)
    wb.close()
    return contents


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('One argument required: original module file')
    xlfiles = glob.glob('*.xlsx')
    if not xlfiles:
        sys.exit('Should be in a directory containing .xlsx files')
    origcells = thecells(sys.argv[1])
    cellfiles = {}
    for xlfile in xlfiles:
        for cell in thecells(xlfile) - origcells:
            if cell not in cellfiles:
                cellfiles[cell] = [xlfile]
            else:
                cellfiles[cell].append(xlfile)

