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

# follow up with something like
    files = [0]*12
    rpts = [0]*12
    for n in range(2,12):
        files[n] = set(tuple(f) for f in cellfiles.values() if len(f) == n) # all the n-tuples of files with cells appearing in only those n files
        rpts[n] = {ff: 0 for ff in files[n]} # the number of cells unique to this n-tuple of files
        for fs in cellfiles.values():
            if len(fs) == n:
                rpts[n][tuple(fs)] += 1

# then, looking at big = max(rpts2.values),
# then big = max(v for v in rpts2.values() if v < big), etc.
# suspsets = [ff for ff in rpts2 if rpts2[ff] == big]
# for susp in suspsets:
#    susp = list(susp)
#    thecels = [c for c in cellfiles if cellfiles[c] == susp]
# # Check it out; are they suspicious or what? Numbers usually turn out not to be

# Also consider:

    for ff,v in rpts[2].items():
        if 2 < v < 6: # these guys share 2-6 cells
            print(ff, end=": ")
            for c,fs in cellfiles.items():
                if tuple(fs) == ff:
                    print(c, end=', ')
            print()
