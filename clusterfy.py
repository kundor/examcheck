#!/usr/bin/python3

import sys
import re
import igraph
import os # *

if len(sys.argv) > 3:
    print('Too many arguments')
    sys.exit(2)

if len(sys.argv) <= 1 or sys.argv[1] == "-":
    fil = sys.stdin
else:
    fil = open(sys.argv[1])

#minwt = .88
minwt = .92
if len(sys.argv) == 3:
    minwt = float(sys.argv[2])

lines = fil.readlines()
fil.close()

pad = lines[0].index('1') - 1
nv = len(lines) - 1
wts = [[float(w) if w != '?' else 0 for w in l[pad:].rstrip().split()] for l in lines[1:]]
lowertriadj = [w + [0]*(nv - len(w)) for w in wts]

G = igraph.Graph.Weighted_Adjacency(lowertriadj, mode="LOWER", loops=False)
#G.vs["name"] = [re.sub(r'[\. _].*$', '', l[:pad-1]) for l in lines[1:]] # *
G.vs["name"] = [re.sub(r'[ _].*$', '', l[:pad-1]) for l in lines[1:]] # *

G.delete_edges(weight_lt=minwt)
clusters = [c for c in G.components() if len(c) > 1]
print(f'{len(clusters)} clusters above {minwt}')
for i, c in enumerate(clusters):
    if len(set(re.sub(r'\..*','',os.path.basename(n)) for n in G.vs[c]['name'])) == 1: # *
        continue # *
    if all('..' in n for n in G.vs[c]['name']): # *
        continue
    print(f'Cluster {i} ({len(c)} members):')
    print('    ' + '\n    '.join(G.vs[c]['name']))



#for minwt in [.4, .5, .6, .7, .8, .9]:
#    K = G.copy()
#    K.delete_edges(weight_lt=minwt)
#    if sum(len(c) == 1 for c in K.components()) > nv/2:
#        clusters = [c for c in K.components() if len(c) > 1]
#        print(f'{len(clusters)} clusters above {minwt}:')
#        for i, c in enumerate(clusters):
#            print(f'Cluster {i} ({len(c)} members):')
#            print(G.vs[c]['name'])
#        print()
