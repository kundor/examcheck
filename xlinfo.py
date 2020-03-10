#!/usr/bin/python3

import io
import os
import sys
import dataclasses as dc
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from datetime import datetime
from contextlib import closing

# timing samples (S19 Mod3; Mod2):
#  exiftool:                        12.180 s;  9.288 s
#  openpyxl method:                 19.176 s; 11.632 s
#  zipfile/xml method:               0.610 s;  0.397 s
#  directly out of submissions.zip:            1.925 s  (saves 2.440 s unzipping)

# xlns = {'cp': "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
#         'dc': "http://purl.org/dc/elements/1.1/",
#         'dcterms': "http://purl.org/dc/terms/"}

@dc.dataclass
class Info:
    filename: str
    creation: datetime
    creator: str
    modified: datetime
    modder: str
    xlhash: str = ''
    csvhash: str = ''
    simhash: int = 0

    asdict = dc.asdict
    replace = dc.replace

def timeforms(dt):
    """Format datetime as m/d/Y H:M:S and timestamp"""
    return dt.strftime('%m/%d/%Y %I:%M:%S %p'), str(round(dt.timestamp()))

def tabline(info):
    """Tab-delimited line of first 5 Info fields, with times as timestamps and m/d/Y H:M:S format"""
    return '\t'.join([info.filename,
            *timeforms(info.creation),
            info.creator,
            *timeforms(info.modified),
            info.modder])

def get_args(argv=sys.argv):
    if len(argv) > 1:
        subfiles = argv[1:]
    else:
        subfiles = [Path('~/Downloads/submissions.zip').expanduser()]
        print(f'Using file {subfiles[0]}', file=sys.stderr)
    return subfiles

def alltags(xmlroot):
    tags = {}
    for child in xmlroot:
        if child.tag[0] == '{':
            namespace, sep, tag = child.tag[1:].partition('}')
        else:
            tag = child.tag
        tags[tag] = child.text
    return tags

def tagval(tags, key, default='\u2205'):
    return tags.get(key, default) or ''

def timeform(tags, key):
    """Return given key as a datetime, or the raw string if it can't be parsed"""
    thetime = tagval(tags, key)
    try:
        return datetime.strptime(thetime + '+0000', '%Y-%m-%dT%H:%M:%SZ%z') # to force UTC
    except ValueError:
        return thetime

def get_name(filething):
    if isinstance(filething, (str, os.PathLike)):
        return str(filething)
    elif hasattr(filething, 'name'):
        return filething.name
    elif hasattr(filething, 'filename'):
        return filething.filename
    else:
        return '<Unknown>'

def xml_props(ooxml, filename=None):
    if filename is None:
        filename = get_name(ooxml)
    try:
        ooxml = ZipFile(ooxml, 'r')
    except BadZipFile as e:
        print(filename, 'is not a zip file?', e, file=sys.stderr)
        return
    try:
        prop = ooxml.open('docProps/core.xml', 'r')
    except KeyError:
        print('Metadata not found (file docProps/core.xml missing) in file ' + filename, file=sys.stderr)
        return
    tree = ET.parse(prop)
    tags = alltags(tree.getroot())
    with closing(prop), closing(ooxml):
        return Info(filename,
                timeform(tags, 'created'),
                tagval(tags, 'creator'),
                timeform(tags, 'modified'),
                tagval(tags, 'lastModifiedBy'))

def workbook_props(wb, filename):
    """Get Info properties from open openpyxl workbook"""
    # slow; worth it if we're already loading them (to convert to csv)
    return Info(filename,
              wb.properties.created,
              wb.properties.creator,
              wb.properties.modified,
              wb.properties.last_modified_by or '\u2205'))

def writeallinfos(files, outfile='info'):
    with open(outfile, 'xt') as out:
        for f in files:
            xp = xml_props(f)
            if xp:
                print(tabline(xp), file=out)

def filesinzip(subfile):
    """Iterator yielding BytesIO for each file in the zip"""
    with ZipFile(subfile, 'r') as subs:
        for name in sorted(subs.namelist()):
            with io.BytesIO(subs.read(name)) as fdata:
                fdata.name = name
                yield fdata

def filesinzips(subfiles):
    for subfile in subfiles:
        yield from filesinzip(subfile)

def filesindir(pdir='.', ext='xlsx'):
    pdir = Path(pdir)
    return sorted(pdir.glob('*.' + ext))

if __name__ == '__main__':
    subfiles = get_args()
    writeallinfos(filesinzips(subfiles))
    # writeallinfos(filesindir())

