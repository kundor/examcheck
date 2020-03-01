#!/usr/bin/python3 -i

import re
import sys
import glob
import IPython
from contextlib import closing
from openpyxl import load_workbook
from traitlets.config import get_config
from xlsx2csv import process_cells, RowVisitor

refpat = re.compile(r"\b\$?[A-Z]{1,2}\$?[1-9][0-9]{0,4}\b")
colpat = re.compile(r"\b(\$?[A-Z]{1,2}):\1\b")
rowpat = re.compile(r"(?<!:)\b(\$?[1-9][0-9]{0,4}):\1\b(?!:)")
numpat = re.compile(r'-?[0-9]+\.?[0-9]+')

def cleanval(cellval):
    cval = str(cellval)
    cval = refpat.sub('REF', cval)
    cval = colpat.sub('COL', cval)
    cval = rowpat.sub('ROW', cval)
    return cval

class CellCollector(RowVisitor):
    def __init__(self):
        self.cells = set()
    def __call__(self, row):
        self.cells.update(cleanval(c) for c in row if c is not None)
    def value(self):
        return self.cells

def thecells(filename):
    with closing(load_workbook(filename, read_only=True)) as workbook:
        return process_cells(wb, [CellCollector()])

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

    for n in range(2, 12):
        big = max(rpts[n].values())
        msg = []
        while big > 6:
            suspsets = [ff for ff in rpts[n] if rpts[n][ff] == big]
            for susp in suspsets:
                susp = list(susp)
                thecels = [c for c in cellfiles if cellfiles[c] == susp]
                msg.append([c for c in thecels if not numpat.fullmatch(c)])
            if any(msg):
                print(f'Matches: {big}')
            for susp, cc in zip(suspsets, msg):
                if not cc:
                    continue
                print(susp)
                print(cc)
# # Check it out; are they suspicious or what? Numbers usually turn out not to be
            big = max(v for v in rpts[n].values() if v < big)

# Also consider:

    for ff,v in rpts[2].items():
        if 2 < v < 6: # these guys share 2-6 cells
            print(ff, end=": ")
            for c,fs in cellfiles.items():
                if tuple(fs) == ff:
                    print(c, end=', ')
            print()

    c = get_config()
    c.InteractiveShellEmbed.colors = "Linux"
    IPython.embed(config=c)
