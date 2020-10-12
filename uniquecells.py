#!/usr/bin/python3

import re
import sys
import glob
from contextlib import closing
from collections import Counter, defaultdict

import IPython
from openpyxl import load_workbook
from traitlets.config import get_config
from xlsx2csv import process_cells, RowVisitor

refpat = re.compile(r"\$?\b[A-Z]{1,2}\$?[1-9][0-9]{0,4}\b")
colpat = re.compile(r"(?<![:$])(\$?\b[A-Z]{1,2}):\1\b")
rowpat = re.compile(r"(?<![:$])\b(\$?[1-9][0-9]{0,4}):\1\b(?!:)")
numpat = re.compile(r'-?[0-9]+\.?[0-9]+')
datepat = re.compile(r"(19|20)[0-9]{2}-(0[0-9]|1[0-2])-([012][0-9]|3[01]) ([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]")

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
        return process_cells(workbook, [CellCollector()])[0]

def filerpts(cellfiles):
    # tuple of filenames : # of cells appearing only in these files
    return Counter(tuple(ff) for ff in cellfiles.values() if 2 <= len(ff) <= 20)

def most_shared(rpts, cellfiles):
    """Report the files with the most shared cells unique to them"""
    for ff, numshared in rpts.most_common():
        if numshared <= 6:
            break
        susp = list(ff)
        thecels = [c for c in cellfiles if cellfiles[c] == susp]
        notnums = [c for c in thecels if not (numpat.fullmatch(c) or datepat.fullmatch(c))]
        if any(notnums):
            print(f'{susp}: {numshared} matches')
            print(notnums)
            print()
# Check it out; are they suspicious or what? (Numbers usually turn out not to be)

def pairs_few(rpts, cellfiles):
    """Report pairs of files which share 2-6 unique cells"""
    # Why?
    for ff, v in rpts.items():
        if len(ff) == 2 and 2 <= v <= 6: # these guys share 2-6 cells
            print(ff, end=": ")
            for c, fs in cellfiles.items():
                if tuple(fs) == ff:
                    print(c, end=', ')
            print()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('One argument required: original module file')
    xlfiles = glob.glob('*.xlsx')
    if not xlfiles:
        sys.exit('Should be in a directory containing .xlsx files')
    origcells = thecells(sys.argv[1])
    cellfiles = defaultdict(list)
    for xlfile in xlfiles:
        for cell in thecells(xlfile) - origcells:
            cellfiles[cell].append(xlfile)

# follow up with something like
    rpts = filerpts(cellfiles)
    most_shared(rpts, cellfiles)
# Also consider:
    pairs_few(rpts, cellfiles)

    c = get_config()
    c.InteractiveShellEmbed.colors = "Linux"
    IPython.embed(config=c)
