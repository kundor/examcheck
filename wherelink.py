#!/usr/bin/python3

import sys
from openpyxl import load_workbook

wb = load_workbook(filename=sys.argv[1], read_only=True)
print(" and ".join(link.file_link.Target.replace("file:///", "").replace("%20", " ")
                   for link in wb._external_links))

