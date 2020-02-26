#!/usr/bin/python3

import io
import mmap
import subprocess
from zipfile import ZipFile, BadZipFile
from canvas import *
from collections import namedtuple
from hashlib import blake2b
from openpyxl import load_workbook
from uniquecells import thecells, cleanval
from allgrades import allgrades
from modderupdate import checkmodder, Status, modders, studict
import IPython
from traitlets.config import get_config

if len(sys.argv) <= 2:
    sys.exit('Arguments: [quizid(s)] <submission zip file(s)> <original Module file>')

quizids = []
arg = 1
while arg < len(sys.argv) and sys.argv[arg].isnumeric():
    quizids.append(int(sys.argv[arg]))
    arg += 1
if not quizids:
    quizids = todays_ids('quiz_id')
if not quizids:
    sys.exit(f'Could not find any quiz IDs. Usage: {sys.argv[0]} <quizid(s)> <submission zip file(s)> <original Module file>')

subfiles = []
if arg < len(sys.argv) - 1:
    subfiles = sys.argv[arg:-1]
else:
    subfiles = [os.path.expanduser('~/Downloads/submissions.zip')]

origfile = sys.argv[-1]

print(f'Using quiz IDs {quizids}, submission zips {subfiles}, original file {origfile}', file=sys.stderr)

SHEETSEP = '----------'

# TODO: download the submissions here
# Note: assignment json has a submissions_download_url which is purported to let you download the zip of all submissions
# However, it only gives an HTML page with authentication error :(
# https://community.canvaslms.com/thread/10824

# Future plan: make working directory /tmp/examcheck; remove any files
# download each submission as it comes in, a la secdownload
# process the file in memory. instead of writing csv, feed cells as tokens to simhash and save the simhash, xlhash, csvhash
# if there's any problem to report, write out the .xlsx and .csv files. I guess near-dups are found at the end, so re-download cluster members after comparing simhashes?
# also re-download uniquecell cluster members.

sys.excepthook = IPython.core.ultratb.FormattedTB(mode='Verbose', color_scheme='Linux', call_pdb=1)

Info = namedtuple('Info', ('filename', 'creation', 'creator', 'modified', 'modder', 'xlhash', 'csvhash'), defaults=(None, None))

def getinfo(workbook, xlhash=None, csvhash=None):
    return Info(filename,
                workbook.properties.created,
                workbook.properties.creator,
                workbook.properties.modified,
                workbook.properties.last_modified_by or '',
                xlhash,
                csvhash)

origwb = load_workbook(origfile, read_only=True)
origcells = thecells(origwb)
originfo = getinfo(origwb)
origwb.close()

cellfiles = {}
infos = []
grades = allgrades(quizids)

for subfile in subfiles:
    with ZipFile(subfile, 'r') as subs:
        for filename in sorted(subs.namelist()):
            if filename.endswith('.xlsx'):
                fdata = io.BytesIO(subs.read(filename))
                buf = fdata.getbuffer()
            elif filename.endswith('.xls'):
                print(f'Converting {filename} to xlsx', file=sys.stderr)
                subs.extract(filename)
                subprocess.run(['libreoffice', '--headless', '--convert-to', 'xlsx', filename])
                fdata = open(filename + 'x', 'rb')
                buf = mmap.mmap(fdata.fileno(), 0, access=mmap.ACCESS_READ)
            else:
                print('Not a xlsx file: ' + filename, file=sys.stderr)
                continue
            codename = filename[:filename.find('_')]
            bsum = blake2b(buf, digest_size=24)
            xlhash = bsum.hexdigest()
            del buf, bsum
            try:
                wb = load_workbook(fdata, read_only=True)
            except BadZipFile as e:
                print(filename, 'is not a zip file?', e, file=sys.stderr)
                continue
            bsum = blake2b(digest_size=24)
            with open(codename + '.csv', 'wt') as csv:
                for ws in wb.worksheets:
                    ws.reset_dimensions()
                    for row in ws.rows:
                        rowstr = ','.join(str(c.value) if c.value is not None else '' for c in row).rstrip(',')
                        print(rowstr, file=csv)
                        bsum.update((rowstr + '\n').encode())
                        for c in row:
                            if c.value is not None:
                                cval = cleanval(c.value)
                                if cval not in origcells:
                                    if cval not in cellfiles:
                                        cellfiles[cval] = [filename]
                                    else:
                                        cellfiles[cval].append(filename)
                    print(SHEETSEP, file=csv)
                    bsum.update((SHEETSEP + '\n').encode())
            csvhash = bsum.hexdigest()
            infos.append(getinfo(wb, xlhash, csvhash))
            wb.close()
            fdata.close()

for info in infos:
    # Update all modder names afterward, so the long conversion process isn't held up by prompts
    codename = info.filename[:info.filename.find('_')]
    stat = checkmodder(codename, info.modder)
    # Status.Found, Status.Boo, Status.DNE, Status.Approved, Status.Unknown
    if stat is Status.DNE:
        continue
    stu = studict[codename]
    if stat is Status.Unknown:
        addit = input(f"User {stu['name']}: modder '{info.modder}'. Add? ")
        if addit.lower() in {'y', 'yes'}:
            modders[codename].append(info.modder)
    # if multiple files, and some are identical, remove the later ones;
    # if (still multiple and) some are unmodified, remove those




c = get_config()
c.InteractiveShellEmbed.colors = "Linux"
IPython.embed(config=c)
