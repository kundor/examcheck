from check import *
import zipfile

def is_stamp(frm):
    return isinstance(frm, str) and frm.startswith('IF(1,1,"WMDAT:') and 'WATERMARK' not in frm

def alldvs(fid):
    wb = load_workbook(fid)
    dvs = []
    for ws in wb.worksheets:
        dvs += ws.data_validations.dataValidation
    wb.close()
    return dvs

def wmdat(fid):
    dvs = alldvs(fid)
    stamps = [dv.formula1[14:-2] for dv in dvs if is_stamp(dv.formula1)]
    if not stamps:
        return 0
    if len(set(stamps)) > 1:
        print(f'{fid.name} multiple stamps {stamps}')
    return int(stamps[0])

subfiles = list(Path('~/Downloads').expanduser().glob('submissions*.zip'))
wm0 = wmdat('orig.xlsx') - 9*60 # Assuming it's for section 009
gen = filesinzips(subfiles) # so we can resume where we left off

for file in gen:
    codename, stuid = fileinfo(file.name)
    stu = studict[stuid]
    try:
        wm = wmdat(file)
        dif = (wm - wm0) / 60
        dif = (dif // 60)*100 + (dif % 60)
        sec = int(stu['section'].rstrip('R'))
        if dif != sec:
            print(f"File {file.name} stamped {wm}, difference {dif} doesn't match {sec}")
    except zipfile.BadZipFile:
        print(f"File {file.name} not a zip file")
