#!/usr/bin/python3

import io
import mmap
import subprocess
from hashlib import blake2b
from datetime import datetime
from zipfile import ZipFile, BadZipFile
from collections import Counter, defaultdict
from dataclasses import dataclass

import simhash
import IPython
from openpyxl import load_workbook

from canvas import *
from uniquecells import cleanval
from allgrades import fetch_grades
from modderupdate import checkmodder, Status, modders, studict

USAGE = 'Arguments: [quizid(s)] <submission zip file(s)> <original Module file>'
SHEETSEP = '----------'

sys.excepthook = IPython.core.ultratb.FormattedTB(mode='Verbose', color_scheme='Linux', call_pdb=1)

@dataclass
class Info:
    filename: str
    creation: datetime
    creator: str
    modified: datetime
    modder: str
    xlhash: str
    csvhash: str
    simhash: int

def get_args(argv=sys.argv):
    if len(argv) <= 2:
        sys.exit(USAGE)
    quizids = []
    arg = 1
    while arg < len(argv) and argv[arg].isnumeric():
        quizids.append(int(argv[arg]))
        arg += 1
    if not quizids:
        quizids = todays_ids('quiz_id')
    if not quizids:
        sys.exit('Could not find any quiz IDs. ' + USAGE)
    subfiles = []
    if arg < len(argv) - 1:
        subfiles = argv[arg:-1]
    else:
        subfiles = [os.path.expanduser('~/Downloads/submissions.zip')]
    origfile = argv[-1]
    print(f'Using quiz IDs {quizids}, submission zips {subfiles}, original file {origfile}', file=sys.stderr)
    return quizids, subfiles, origfile

def make_info(filename, workbook, xlhash=None, csvhash=None, simhash=None):
    return Info(filename,
                workbook.properties.created,
                workbook.properties.creator,
                workbook.properties.modified,
                workbook.properties.last_modified_by or '\u2205',
                xlhash,
                csvhash,
                simhash)

def blakesum(buf):
    bsum = blake2b(buf, digest_size=24)
    return bsum.hexdigest()

def bsum_fid(fid):
    return blakesum(mmap.mmap(fid.fileno(), 0, access=mmap.ACCESS_READ))

def bsum_mem(bytio):
    return blakesum(bytio.getbuffer())

def gethash(shingles):
    hashvector = [simhash.unsigned_hash(s.encode()) for s in shingles]
    return simhash.compute(hashvector)

def sumprint(line, bsum, out):
    if out:
        print(line, file=out)
    bsum.update((line + '\n').encode())

def process_cells(workbook, csvout=None):
    """Visit all cells of the workbook, printing to csvout if given,
    and return the set of (ref-erased) cells and blake and sim hashes."""
    bsum = blake2b(digest_size=24)
    shingles = []
    mycells = set()
    for ws in workbook.worksheets:
        ws.reset_dimensions()
        for row in ws.values:
            rowstr = ','.join(str(c) if c is not None else '' for c in row).rstrip(',')
            sumprint(rowstr, bsum, csvout)
            rowcells = [cleanval(c) for c in row if c is not None]
            mycells.update(rowcells)
            if len(rowcells) >= 3:
                shingles += [' '.join(cells) for cells in simhash.shingle(rowcells, 3)]
            else:
                shingles += [' '.join(rowcells)]
        sumprint(SHEETSEP, bsum, csvout)
    return mycells, bsum.hexdigest(), gethash(shingles)

def get_file_info(filename):
    with open(filename, 'rb') as fid:
        xlhash = bsum_fid(fid)
        wb = load_workbook(fid, read_only=True)
        cells, csvhash, thesimhash = process_cells(wb)
        theinfo = make_info(filename, wb, xlhash, csvhash, thesimhash)
        wb.close()
    return cells, theinfo

# TODO: download the submissions here
# Note: assignment json has a submissions_download_url which is purported to let you download the zip of all submissions
# However, it only gives an HTML page with authentication error :(
# https://community.canvaslms.com/thread/10824

# Future plan: make working directory /tmp/examcheck; remove any files
# download each submission as it comes in, a la secdownload
# process the file in memory. instead of writing csv, save the simhash, xlhash, csvhash
# if there's any problem to report, write out the .xlsx and .csv files.
# I guess near-dups are found at the end, so re-download cluster members after comparing simhashes?
# also re-download uniquecell cluster members.

quizids, subfiles, origfile = get_args()

origcells, originfo = get_file_info(origfile)

cellfiles = defaultdict(list) # map cell_content : files
infos = []
grades = fetch_grades(quizids) # map student_id : score
stuids = Counter()
xlhashes = Counter()
csvhashes = Counter()

warnings.filterwarnings('ignore', '.*invalid specification.*', UserWarning, 'openpyxl')
warnings.filterwarnings('ignore', 'Unknown extension is not supported.*', UserWarning, 'openpyxl')

for subfile in subfiles:
    with ZipFile(subfile, 'r') as subs:
        for filename in sorted(subs.namelist()):
            if filename.endswith('.xlsx'):
                fdata = io.BytesIO(subs.read(filename))
                xlhash = bsum_mem(fdata)
            elif filename.endswith('.xls'):
                print(f'Converting {filename} to xlsx', file=sys.stderr)
                subs.extract(filename)
                subprocess.run(['libreoffice', '--headless', '--convert-to', 'xlsx', filename],
                        stdout=subprocess.DEVNULL)
                fdata = open(filename + 'x', 'rb')
                xlhash = bsum_fid(fdata)
            else:
                print('Not a xlsx file: ' + filename, file=sys.stderr)
                continue
            codename, stuid, subid, *fn = filename.split('_')
            stuid = int(stuid)
            stuids[stuid] += 1
            if stuids[stuid] > 1:
                print(f'{codename} seen {stuids[stuid]} times')
                if xlhash == originfo.xlhash:
                    print('This one is unmodified, ignoring')
                    fdata.close()
                    continue
                prev = [inf for inf in infos if int(inf.filename.split('_')[1]) == stuid]
                if prev[0].xlhash == originfo.xlhash: # Only the first added could be unmodified
                    infos.remove(prev[0])
                    print(f'Removing unmodified file {prev[0].filename}')
                elif any(p.xlhash == xlhash for p in prev):
                    print('This one is identical to a previously seen file; ignoring.')
                    fdata.close()
                    continue
            xlhashes[xlhash] += 1
            try:
                wb = load_workbook(fdata, read_only=True)
            except BadZipFile as e:
                print(filename, 'is not a zip file?', e, file=sys.stderr)
                continue
            with open(f'{codename}_{stuid}.csv', 'wt') as csv:
                thecells, csvhash, thehash = process_cells(wb, csv)
            for cval in thecells - origcells:
                cellfiles[cval].append(filename)
            csvhashes[csvhash] += 1
            infos.append(make_info(filename, wb, xlhash, csvhash, thehash))
            wb.close()
            fdata.close()

for info in infos:
    # Update modder names afterward, so the long conversion process isn't held up by prompts
    codename, stuid, subid, *fn = info.filename.split('_')
    stuid = int(stuid)
    stat = checkmodder(stuid, info.modder)
    # Status.Found, Status.Boo, Status.DNE, Status.Approved, Status.Unknown
    if stat is Status.DNE:
        continue
    stu = studict[stuid]
    if stat is Status.Unknown:
        addit = input(f"User {stu['name']}: modder '{info.modder}'. Add? ")
        if addit.lower() in {'y', 'yes'}:
            modders[codename].append(info.modder)
    # if multiple files, and some are identical, remove the later ones;
    # if (still multiple and) some are unmodified, remove those


IPython.start_ipython(['--quick', '--no-banner'], user_ns=globals())
