#!/usr/bin/python3

import os
import csv
import sys
from openpyxl import load_workbook

SHEETSEP = '----------\n'
csv.register_dialect('newline', lineterminator='\n')

def process_cells(workbook, rowvisitors):
    """Visit all rows of the workbook, passing to given RowVisitors,
    and return their values."""
    for ws in workbook.worksheets:
        ws.reset_dimensions()
        maxrow = max(n for n,row in enumerate(ws.values) if any(row))
        for row in ws.iter_rows(max_row=maxrow+1, values_only=True):
            for visit in rowvisitors:
                visit(row)
        for visit in rowvisitors:
            visit.newsheet()
    return [rv.value() for rv in rowvisitors]

class RowVisitor:
    def newsheet(self):
        pass

class CSVPrinter(RowVisitor):
    def __init__(self, filename):
        self.fid = open(filename, 'w', newline='')
        self.writer = csv.writer(self.fid, 'newline')
    def __call__(self, row):
        maxcol = max((n for n,c in enumerate(row) if c is not None), default=-1)
        self.writer.writerow(row[:maxcol+1])
    def newsheet(self):
        self.fid.write(SHEETSEP)
    def value(self):
        self.fid.close()

if __name__ = '__main__':
    wb = load_workbook(filename=sys.argv[1], read_only=True)

    if len(sys.argv) == 3:
        outfile = sys.argv[2]
    elif len(sys.argv) > 3:
        sys.exit('Max two arguments, infile outfile')
    else:
        root, ext = os.path.splitext(sys.argv[1])
        outfile = root + '.csv'

    process_cells(wb, [CSVPrinter(outfile)])

