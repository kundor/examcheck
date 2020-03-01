#!/usr/bin/python3

import io
import mmap
import subprocess
from hashlib import blake2b
from zipfile import ZipFile, BadZipFile
from datetime import datetime
from contextlib import closing
from collections import Counter, defaultdict, namedtuple
from dataclasses import dataclass

import simhash
import IPython
from openpyxl import load_workbook

from canvas import *
from xlsx2csv import process_cells, RowVisitor, SHEETSEP
from uniquecells import cleanval, CellCollector
from allgrades import fetch_grades
from modderupdate import checkmodder, Status, modders, studict

USAGE = 'Arguments: [quizid(s)] <submission zip file(s)> <original Module file>'

sys.excepthook = IPython.core.ultratb.FormattedTB(mode='Verbose', color_scheme='Linux', call_pdb=1)

NameInfo = namedtuple('NameInfo', ('codename', 'stuid', 'subid'))

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

def blakesum(buf):
    bsum = blake2b(buf, digest_size=24)
    return bsum.hexdigest()

def bsum_fid(fid):
    return blakesum(mmap.mmap(fid.fileno(), 0, access=mmap.ACCESS_READ))

def bsum_mem(bytio):
    return blakesum(bytio.getbuffer())

def xls2xlsx(zipp, filename):
    print(f'Converting {filename} to xlsx', file=sys.stderr)
    zipp.extract(filename)
    subprocess.run(['libreoffice', '--headless', '--convert-to', 'xlsx', filename],
            stdout=subprocess.DEVNULL)
    return open(filename + 'x', 'rb')

def filesize(fdata):
    try:
        size = fdata.getbuffer().nbytes
    except AttributeError:
        size = os.fstat(fdata.fileno()).st_size
    return size

def nameinfo(filename):
    codename, stuid, subid, *fn = filename.split('_')
    return NameInfo(codename, int(stuid), int(subid))

class BlakeHasher(RowVisitor):
    def __init__(self):
        self.bsum = blake2b(digest_size=24)
    def __call__(self, row):
        rowstr = ','.join(str(c) if c is not None else '' for c in row).rstrip(',') + '\n'
        self.bsum.update(rowstr.encode())
    def newsheet(self):
        self.bsum.update(SHEETSEP.encode())
    def value(self):
        return self.bsum.hexdigest()

class SimHasher(RowVisitor):
    def __init__(self):
        self.hashvector = []
    @staticmethod
    def hashval(shingle):
        return simhash.unsigned_hash(shingle.encode())
    def __call__(self, row):
        rowcells = [cleanval(c) for c in row if c is not None]
        if len(rowcells) >= 3:
            shingles = [' '.join(cells) for cells in simhash.shingle(rowcells, 3)]
        else:
            shingles = [' '.join(rowcells)]
        self.hashvector += [self.hashval(s) for s in shingles]
    def value(self):
        return simhash.compute(self.hashvector)

def process_workbook(xlhash, filename, workbook):
    cells, csvhash, simhash = process_cells(workbook, [CellCollector(), BlakeHasher(), SimHasher()]
    return cells, Info(filename,
                workbook.properties.created,
                workbook.properties.creator,
                workbook.properties.modified,
                workbook.properties.last_modified_by or '\u2205',
                xlhash,
                csvhash,
                simhash)

def process_file(filename):
    with open(filename, 'rb') as fid:
        xlhash = bsum_fid(fid)
        with closing(load_workbook(fid, read_only=True)) as workbook:
            return process_workbook(xlhash, filename, workbook)

def report_nonxlsx(filename):
    print('Not a xlsx file: ' + filename, file=sys.stderr)
    try:
        codename, stuid, subid = nameinfo(filename)
    except ValueError: #filename not in Canvas name_sid_sub_etc format
        return # no known student to report
    reports[stuid].append(f'Non-xlsx file: {filename}')

def checktemp(filename, fdata):
    stuid = nameinfo(filename).stuid
    badname = '~' in filename
    small = filesize(fdata) < 500
    if small and badname:
        reports[stuid].append('Temp file')
    elif badname:
        reports[stuid].append(f'Big temp file? {filename}')
    elif small:
        reports[stuid].append(f'Temp file? {filename}')
    else:
        reports[stuid].append(f'Not an Excel file? {filename}')

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

origcells, originfo = process_file(origfile)

cellfiles = defaultdict(list) # map cell_content : files
infos = []
grades = fetch_grades(quizids) # map student_id : score
stuids = Counter()
xlhashes = Counter()
csvhashes = Counter()
reports = defaultdict(list) # map stuid : strings

warnings.filterwarnings('ignore', '.*invalid specification.*', UserWarning, 'openpyxl')
warnings.filterwarnings('ignore', 'Unknown extension is not supported.*', UserWarning, 'openpyxl')

for subfile in subfiles:
    with ZipFile(subfile, 'r') as subs:
        for filename in sorted(subs.namelist()):
            if filename.endswith('.xlsx'):
                fdata = io.BytesIO(subs.read(filename))
                xlhash = bsum_mem(fdata)
            elif filename.endswith('.xls'):
                fdata = xls2xlsx(subs, filename)
                xlhash = bsum_fid(fdata)
            else:
                report_nonxlsx(filename)
                continue
            codename, stuid, subid = nameinfo(filename)
            stuids[stuid] += 1
            if stuids[stuid] > 1:
                print(f'{codename} seen {stuids[stuid]} times')
                if xlhash == originfo.xlhash:
                    print('This one is unmodified, ignoring')
                    fdata.close()
                    continue
                prev = [inf for inf in infos if nameinfo(inf.filename)[1] == stuid]
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
                checktemp(filename, fdata)
                continue
            thecells, theinfo = process_workbook(xlhash, filename, wb)
            for cval in thecells - origcells:
                cellfiles[cval].append(filename)
            csvhashes[csvhash] += 1
            infos.append(theinfo)
            wb.close()
            fdata.close()

for info in infos:
    # Update modder names afterward, so the long conversion process isn't held up by prompts
    codename, stuid, subid = nameinfo(filename)
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
