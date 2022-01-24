#!/usr/bin/python3

import sys
import time
import requests
from bs4 import BeautifulSoup

if len(sys.argv) == 1:
    classnum = '1112'
elif len(sys.argv) == 2:
    classnum = sys.argv[1]
else:
    sys.exit('Unknown arguments -- I accept one argument: class number to look for')

theyear, themonth, *_ = time.gmtime()
if themonth <= 5:
    thesem = 'spring'
elif themonth >= 8:
    thesem = 'fall'
else:
    thesem = 'summer'

courses = requests.get(f'https://www.colorado.edu/math/{thesem}-{theyear}')
soup = BeautifulSoup(courses.text)
if soup.table.tbody:
    tbody = soup.table.tbody
else:
    tbody = soup.table
rows = [[td.text.strip() for td in row.find_all('td')] for row in tbody.find_all('tr')]
sectns = [r for r in rows if r and classnum in r[0]]
sectns = [[s[2], s[3], s[5], s[6]] for s in sectns]
for s in sectns:
    print(s)
