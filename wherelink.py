#!/usr/bin/python3

import sys
from zipfile import ZipFile
from openpyxl import load_workbook

def haslink(workbook):
    return bool(workbook._external_links)

def file_haslink(fid):
    """Given open .xlsx file object, or path to one, return if it contains links"""
    zf = ZipFile(fid, 'r')
    try:
        zf.getinfo('xl/externalLinks/externalLink1.xml')
        return True
    except KeyError:
        return False

def enquote(strings):
    return [f'"{s}"' for s in strings]

def makenice(link):
    return link.file_link.Target.replace("file:///", "").replace("%20", " ")

def linklist(workbook):
    return [makenice(link) for link in wb._external_links)]

def links_desc(workbook):
    links = [enquote(l) for l in wherelink(wb)]
    return " and ".join(links)

if __name__ == '__main__':
    wb = load_workbook(filename=sys.argv[1], read_only=True)
    print(links_desc(wb))
    wb.close()

