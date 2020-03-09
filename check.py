#!/usr/bin/python3

import io
import mmap
import subprocess
import dataclasses as dc
from hashlib import blake2b
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from datetime import datetime, timedelta
from contextlib import closing
from collections import Counter, defaultdict

import simhash
import IPython
from colorama import Fore
from openpyxl import load_workbook

from canvas import *
from xlsx2csv import process_cells, RowVisitor, SHEETSEP
from allgrades import fetch_grades
from wherelink import haslink, links_desc
from uniquecells import cleanval, CellCollector, filerpts, pairs_few, most_shared
from modderupdate import checkadd, Status, studict, fileinfo, writeout

USAGE = 'Arguments: [quizid(s)] <submission zip file(s)> <original Module file>'

sys.excepthook = IPython.core.ultratb.FormattedTB(mode='Verbose', color_scheme='Linux')

@dc.dataclass
class Info:
    filename: str
    creation: datetime
    creator: str
    modified: datetime
    modder: str
    xlhash: str
    csvhash: str
    simhash: int

    asdict = dc.asdict
    replace = dc.replace

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

def get_mime(filename):
    result = subprocess.run(['file', '-b', '--mime-type', filename], capture_output=True)
    return result.stdout.decode().rstrip()

def xls2xlsx(zipp, filename):
    if os.path.exists(filename + 'x'):
        print(f'{filename}x found', file=sys.stderr)
    else:
        print(f'Converting {filename} to xlsx', file=sys.stderr)
        zipp.extract(filename)
        if get_mime(filename) == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            print("Appears to be misnamed .xlsx file", file=sys.stderr)
            os.rename(filename, filename + 'x')
        else:
            subprocess.run(['libreoffice', '--headless', '--convert-to', 'xlsx', filename],
                    stdout=subprocess.DEVNULL)
    return open(filename + 'x', 'rb')

def filesize_mem(fdata):
    return fdata.getbuffer().nbytes

def filesize_fid(fid):
    return os.fstat(fid.fileno()).st_size

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
    cells, csvhash, simhash = process_cells(workbook, [CellCollector(), BlakeHasher(), SimHasher()])
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
        stuid = fileinfo(filename).stuid
    except ValueError: #filename not in Canvas name_sid_sub_etc format
        return # no known student to report
    reports[stuid].append(f'Non-xlsx file: {filename}')

def checktemp(filename, fdata, size):
    stuid = fileinfo(filename).stuid
    badname = '~' in filename
    small = size < 500
    if small and badname:
        reports[stuid].append('Temp file')
    elif badname:
        reports[stuid].append(f'Big temp file? {filename}')
    elif small:
        reports[stuid].append(f'Temp file? {filename}')
    else:
        reports[stuid].append(f'Not an Excel file? {filename}')

def pop_print_report(stu):
    secname = stu['section']
    stuid = stu['id']
    score = grades[stuid]
    namegrad = f"{stu['name']} ({grade})"
    print(f'{secname:4} {namegrad:26} ' + ', '.join(reports.pop(stuid)))

def dumb_lastname(tch):
    return tch['name'].split()[1]

def sorted_teachers():
    return sorted(teachers, key=dumb_lastname)

def print_reports():
    for tch in sorted_teacher():
        print(tch['name'])
        for sec in sorted([sec[1] for sec in tch['sections']]):
            for stuid in reports:
                stu = studict[stuid]
                if stu['section'] == sec:
                    pop_print_report(stu)
            print()
    if reports:
        print('Leftovers?!')
        for stuid in reports:
            pop_print_report(studict[stuid])

def inbasedir():
    basedir = Path(__file__).parent.resolve()
    curdir = os.path.abspath(os.path.curdir)
    return curdir == basedir

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

teachers = load_file('teachers.json', json.load)
origcells, originfo = process_file(origfile)

cellfiles = defaultdict(list) # map cell_content : files
infos = []
grades = fetch_grades(quizids) # map student_id : score
stuids = Counter()
xlhashes = {}
csvhashes = Counter()
reports = defaultdict(list) # map stuid : strings

now = datetime.now()

warnings.filterwarnings('ignore', '.*invalid specification.*', UserWarning, 'openpyxl')
warnings.filterwarnings('ignore', 'Unknown extension is not supported.*', UserWarning, 'openpyxl')

for subfile in subfiles:
    with ZipFile(subfile, 'r') as subs:
        for filename in sorted(subs.namelist()):
            if filename.endswith('.xlsx'):
                fdata = io.BytesIO(subs.read(filename))
                xlhash = bsum_mem(fdata)
                size = filesize_mem(fdata)
            elif filename.endswith('.xls'):
                fdata = xls2xlsx(subs, filename)
                xlhash = bsum_fid(fdata)
                size = filesize_fid(fdata)
            else:
                report_nonxlsx(filename)
                continue
            codename, stuid, subid = fileinfo(filename)
            stuids[stuid] += 1
            if stuids[stuid] > 1:
                print(f'{codename} seen {stuids[stuid]} times')
                if xlhash == originfo.xlhash:
                    print('This one is unmodified, ignoring')
                    fdata.close()
                    continue
                prev = [inf for inf in infos if fileinfo(inf.filename).stuid == stuid]
                if prev[0].xlhash == originfo.xlhash: # Only the first added could be unmodified
                    infos.remove(prev[0])
                    print(f'Removing unmodified file {prev[0].filename}')
                elif any(p.xlhash == xlhash for p in prev):
                    print('This one is identical to a previously seen file for this student; ignoring.')
                    fdata.close()
                    continue
            if xlhash in xlhashes:
                prev = xlhashes[xlhash]
                print(f'File {filename} identical to previously seen file {prev.filename}')
                infos.append(prev.replace(filename=filename))
                fdata.close()
                continue
            if size < 6000:
                reports[stuid].append(f'Small file, {size} bytes')
            try:
                wb = load_workbook(fdata, read_only=True)
            except BadZipFile as e:
                print(filename, 'is not a zip file?', e, file=sys.stderr)
                checktemp(filename, fdata, size)
                continue
            thecells, theinfo = process_workbook(xlhash, filename, wb)
            for cval in thecells - origcells:
                cellfiles[cval].append(filename)
            csvhashes[theinfo.csvhash] += 1
            infos.append(theinfo)
            xlhashes[xlhash] = theinfo
            if haslink(wb):
                reports[stuid].append('Links to ' + links_desc(wb))
            wb.close()
            fdata.close()

for info in infos:
    # Update modder names afterward, so the long conversion process isn't held up by prompts
    codename, stuid, subid = fileinfo(info.filename)
    docreatmsg = False
    creatmsg = 'Created'
    if info.creator != originfo.creator:
        docreatmsg = True
        creatmsg += ' by ' + Fore.RED + info.creator + Fore.RESET
    if info.creation != originfo.creation:
        docreatmsg = True
        if abs(info.creation - originfo.creation) < timedelta(days=1):
            creatmsg += ' on ' + Fore.RED + f'{info.creation:%x %X}' + Fore.RESET
        else:
            creatmsg += ' on ' + Fore.RED + f'{info.creation:%x}' + Fore.RESET
    if docreatmsg:
        reports[stuid].append(creatmsg)

    domodmsg = False
    modmsg = 'Last modified'
    stat = checkadd(stuid, info.modder)
    # Status.Found, Status.Boo, Status.DNE, Status.Approved, Status.Unknown
    if stat is Status.DNE:
        continue
    stu = studict[stuid]
    if stat is Status.Unknown:
        domodmsg = True
        modmsg += ' by ' + Fore.RED + info.modder + Fore.RESET
    elif stat is Status.Boo and info.xlhash == originfo.xlhash:
        reports[stuid].append('Unmodified')
    elif stat is Status.Boo and info.modified == originfo.modified:
        reports[stuid].append('Metadata says unmodified')
    elif stat is Status.Boo:
        reports[stuid].append(f'Unmodified wrong spreadsheet? Last modified by {info.modder} on {info.modified:%x %X}')
    if info.modified > now or info.modified < now - timedelta(days=9) and stat is not Status.Boo:
        if not domodmsg:
            modmsg += ' by ' + info.modder
        modmsg += ' on ' + Fore.RED + f'{info.modified:%x}' + Fore.RESET
        domodmsg = True
    if domodmsg:
        reports[stuid].append(modmsg)


writeout()
pairs = simhash.find_all([i.simhash for i in infos], 6, 4) # blocks >= maxdist + 1; maxdist 1 to 64
print_reports()

for chash, count in csvhashes.most_common():
    if count <= 1:
        break
    print('Identical CSV: ' + ', '.join(i.filename for i in infos if i.csvhash == chash))

rpts = filerpts(cellfiles)
most_shared(rpts, cellfiles)
pairs_few(rpts, cellfiles)

IPython.start_ipython(['--quick', '--no-banner'], user_ns=globals())

# Make command interpreter (import cmd)
# <stu> is codename with tab-completion, or stuid
# report <stu> [message]
# get <stu> -- downloads and converts to CSV
# open <stu> -- gets if necessary, opens in libreoffice
# diff <stu1> <stu2> -- opens icdiff of CSVs in a pager
