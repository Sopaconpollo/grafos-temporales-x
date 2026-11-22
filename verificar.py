import csv, json, sys
from collections import Counter
from pathlib import Path
import numpy as np

r = Path(sys.argv[1])
def read(name):
    with (r / (name + '.csv')).open(encoding='utf-8', newline='') as file:
        return list(csv.DictReader(file))

events = read('events')
assert len(events) == len({tuple(row[k] for k in ('post_id','type','source','target')) for row in events})
summary = json.loads((r / 'summary.json').read_text())
assert sum(int(row['posts']) for row in read('daily')) == summary['included']
assert len(read('provenance')) == summary['rows']
counts = Counter()
for row in events:
    assert all(row[k].isdigit() for k in ('post_id','source','target'))
    if row['source'] != row['target']:
        for kind in (row['type'], 'all'):
            counts[row['month'],kind,row['source'],row['target']] += 1
edges = read('edges')
assert len(edges) == sum(k[1] != 'all' for k in counts)
for row in edges:
    assert int(row['weight']) == counts[tuple(row[k] for k in ('month','type','source','target'))]

for row in read('spectral'):
    m, kind = row['month'], row['type']
    prefix = f'matrices/{m}_{kind}'
    nodes = {int(n['index']): n['user_id'] for n in read(prefix + '_nodes')}
    comp = {int(n['index']): n['user_id'] for n in read(prefix + '_lcc_nodes')}
    lines = (r / (prefix + '_A.mtx')).read_text().splitlines()
    n, size, nnz = map(int, lines[1].split())
    assert n == size == len(nodes) == int(row['nodes'])
    assert nnz == len(lines) - 2 == int(row['arcs'])
    actual = Counter()
    sym = Counter()
    comp_ids = set(comp.values())
    for line in lines[2:]:
        i, j, w = map(int, line.split())
        s, t = nodes[i], nodes[j]
        actual[m,kind,s,t] = w
        if s in comp_ids and t in comp_ids:
            sym[s,t] += w
            sym[t,s] += w
    assert actual == Counter({k:v for k,v in counts.items() if k[:2] == (m,kind)})
    degrees = Counter()
    for (s,t), w in sym.items():
        degrees[s] += w
    lines = (r / (prefix + '_Lnorm_lcc.mtx')).read_text().splitlines()
    g, size, nnz = map(int, lines[1].split())
    assert g == size == len(comp) == int(row['lcc_nodes'])
    assert nnz == len(lines) - 2 == g + len(sym)
    for line in lines[2:]:
        i, j, w = line.split()
        s, t = comp[int(i)], comp[int(j)]
        expect = 1 if s == t else -sym[s,t] / np.sqrt(degrees[s] * degrees[t])
        assert abs(float(w) - expect) < 1e-12
print(f'OK: {len(events)} events, {len(edges)} typed edges, 30 adjacency and 30 Laplacian matrices')

