#!/usr/bin/python3

import time
import requests
from bs4 import BeautifulSoup

theyear, themonth, *_ = time.gmtime()
if themonth <= 5:
    thesem = 'spring'
elif themonth >= 8:
    thesem = 'fall'
else:
    thesem = 'summer'

courses = requests.get(f'https://www.colorado.edu/math/{thesem}-{theyear}')
soup = BeautifulSoup(courses.text)
tbody = soup.table.tbody
rows = [[td.text.strip() for td in row.find_all('td')] for row in tbody.find_all('tr')]
sectns = [r for r in rows if r and '1112' in r[0]]
sectns = [[s[2], s[3], s[5], s[6]] for s in sectns]
print(sectns)
