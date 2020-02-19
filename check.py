#!/usr/bin/python3

import io
import os
import sys
#import glob
import datetime
import xml.etree.ElementTree as ET
from zipfile import ZipFile, BadZipFile

# timing samples (S19 Mod3; Mod2):
#  exiftool:                        12.180 s;  9.288 s
#  openpyxl method:                 19.176 s; 11.632 s
#  zipfile/xml method:               0.610 s;  0.397 s
#  directly out of submissions.zip:            1.925 s  (saves 2.440 s unzipping)
#    

# xlns = {'cp': "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
#         'dc': "http://purl.org/dc/elements/1.1/",
#         'dcterms': "http://purl.org/dc/terms/"}

# xlfiles = sorted(glob.glob('*.xlsx'))

if len(sys.argv) > 1:
    subfiles = sys.argv[1:]
else:
    subfiles = [os.path.expanduser('~/Downloads/submissions.zip')]
    print(f'Using file {subfiles[0]}', file=sys.stderr)

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

with open('info', 'xt') as out:
    for subfile in subfiles:
        with ZipFile(subfile, 'r') as subs:
            for f in sorted(subs.namelist()):
                if not f.endswith('.xlsx'):
                    print('Not a xlsx file: ' + f, file=sys.stderr)
                    continue
                fdata = io.BytesIO(subs.read(f))
                try:
                    xlsx = ZipFile(fdata, 'r')
                except BadZipFile as e:
                    print(f, 'is not a zip file?', e, file=sys.stderr)
                    continue
                try:
                    prop = xlsx.open('docProps/core.xml', 'r')
                except KeyError:
                    print('Metadata not found (file docProps/core.xml missing) in file ' + f, file=sys.stderr)
                    continue
                tree = ET.parse(prop)
                tags = alltags(tree.getroot()) 
                mstamp, mtime = timeforms(tags, 'modified')
                cstamp, ctime = timeforms(tags, 'created')
                print(f,
                      ctime,
                      cstamp,
                      tagval(tags, 'creator'),
                      mtime,
                      mstamp,
                      tagval(tags, 'lastModifiedBy'),
                      sep='\t', file=out)
                prop.close()
                xlsx.close()
                fdata.close()
        
        
# slow way to get info from openpyxl
# might be worth it if we're already opening them (to convert to csv)
#        wb = openpyxl.load_workbook(f, read_only=True)
#        print(f, 
#              wb.properties.created.strftime('%m/%d/%Y %I:%M:%S %p'),
#              round(wb.properties.created.replace(tzinfo=datetime.timezone.utc).timestamp()),
#              wb.properties.creator,
#              wb.properties.modified.strftime('%m/%d/%Y %I:%M:%S %p'),
#              round(wb.properties.modified.replace(tzinfo=datetime.timezone.utc).timestamp()),
#              wb.properties.last_modified_by or '',
#              sep='\t', file=out)
#        wb.close()
        
