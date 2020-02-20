#!/usr/bin/python3 -i

import io
import os
import sys
#import glob
import datetime
import xml.etree.ElementTree as ET
from zipfile import ZipFile, BadZipFile
from openpyxl import load_workbook
from uniquecells import thecells, refpat, colpat, rowpat

if len(sys.argv <= 1):
    sys.exit('Arguments: <submission zip file(s)> <original Module file>')
if len(sys.argv) > 2:
    subfiles = sys.argv[1:-1]
else:
    subfiles = [os.path.expanduser('~/Downloads/submissions.zip')]
    print(f'Using file {subfiles[0]}', file=sys.stderr)
origfile = sys.argv[-1]

def alltags(xmlroot):
    tags = {}
    for child in xmlroot:
        if child.tag[0] == '{':
            namespace, sep, tag = child.tag[1:].partition('}')
        else:
            tag = child.tag
        tags[tag] = child.text
    return tags

def dtime(timetag):
    return datetime.datetime.strptime(timetag + '+0000', '%Y-%m-%dT%H:%M:%SZ%z') # to force UTC

def tagval(tags, key, default='\u2205'):
    return tags.get(key, default) or ''

def timeforms(tags, key):
    """Return given key (a datetime) as timestamp, string tuple"""
    thetime = tagval(tags, key)
    if len(thetime) > 5:
        thetime = dtime(thetime)
        return round(thetime.timestamp()), thetime.strftime('%m/%d/%Y %I:%M:%S %p')
    return thetime, thetime

origcells = thecells(origfile)
cellfiles = {}

with open('info', 'xt') as out:
    for subfile in subfiles:
        with ZipFile(subfile, 'r') as subs:
            for filename in sorted(subs.namelist()):
                if not filename.endswith('.xlsx'):
                    print('Not a xlsx file: ' + filename, file=sys.stderr)
                    continue
                fdata = io.BytesIO(subs.read(filename))
                try:
                    xlsx = ZipFile(fdata, 'r')
                except BadZipFile as e:
                    print(filename, 'is not a zip file?', e, file=sys.stderr)
                    continue
                try:
                    prop = xlsx.open('docProps/core.xml', 'r')
                except KeyError:
                    print('Metadata not found (file docProps/core.xml missing) in file ' + filename, file=sys.stderr)
                    continue
                tree = ET.parse(prop)
                tags = alltags(tree.getroot()) 
                mstamp, mtime = timeforms(tags, 'modified')
                cstamp, ctime = timeforms(tags, 'created')
                print(filename,
                      ctime,
                      cstamp,
                      tagval(tags, 'creator'),
                      mtime,
                      mstamp,
                      tagval(tags, 'lastModifiedBy'),
                      sep='\t', file=out)
                prop.close()
                xlsx.close()

                codename = filename[:filename.find('_')]
                wb = load_workbook(fdata, read_only=True)
                contents = set()
                with open(codename + '.csv', 'wt') as csv:
                    for ws in wb.worksheets:
                        ws.reset_dimensions()
                        for row in ws.rows:
                            print(','.join(str(c.value) if c.value is not None else '' for c in row).rstrip(','), file=csv)
                            for c in row:
                                if c.value is not None:
                                    cval = refpat.sub('REF', str(c.value))
                                    cval = colpat.sub('COL', cval)
                                    cval = rowpat.sub('ROW', cval)
                                    contents.add(cval)
                        print('----------', file=csv)
                wb.close()
                fdata.close()


# might be worth it if we're already opening them (to convert to csv)
#        wb = openpyxl.load_workbook(filename, read_only=True)
#        print(filename, 
#              wb.properties.created.strftime('%m/%d/%Y %I:%M:%S %p'),
#              round(wb.properties.created.replace(tzinfo=datetime.timezone.utc).timestamp()),
#              wb.properties.creator,
#              wb.properties.modified.strftime('%m/%d/%Y %I:%M:%S %p'),
#              round(wb.properties.modified.replace(tzinfo=datetime.timezone.utc).timestamp()),
#              wb.properties.last_modified_by or '',
#              sep='\t', file=out)
#        wb.close()

