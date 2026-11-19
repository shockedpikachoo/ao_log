"""Turn a raw AODP snapshot (fetch_market.py) into the guide's price cells and the figures quoted in the page.

Usage: python3 -I build_market.py <raw dir> <idmap.json> <guide html or guideData.json> <since YYYY-MM-DD> <until YYYY-MM-DD> <out.json>

idmap: guide item id -> {"t": {"4.0": item id | null, ...}, "ref": [[label, item id], ...]}
Cell rules (unchanged since the 10/25 price version):
  * daily history records with quality 1-3, positive price and count, UTC day within [since, until];
  * outliers: records priced outside [median/3, median*3] of the cell's volume-weighted (lower) median are dropped,
    the 7 cities pooled together, the Black Market separately;
  * p = volume-weighted average of the kept city records (rounded), n = units, d = trading days, l = last day,
    c = per-city [city, avg, units, last day] sorted by price; b = Black Market [avg, units, last day];
  * o = cheapest current city sell order (quality 1-3) seen within 24 h before the order fetch.
"""
import bisect, collections, datetime as dt, gzip, itertools, json, os, re, statistics, sys

RAW, IDMAP, GUIDE, SINCE, UNTIL, OUT = sys.argv[1:7]
CITIES = ['Bridgewatch', 'Fort Sterling', 'Lymhurst', 'Martlock', 'Thetford', 'Caerleon', 'Brecilien']
BM = 'Black Market'
TIERS = ['4.0', '4.1', '5.0', '4.2', '5.1', '6.0', '7.0', '8.0']
LOWN = 10

man_h = json.load(open(os.path.join(RAW, 'manifest_hist.json'), encoding='utf-8'))
man_o = json.load(open(os.path.join(RAW, 'manifest_orders.json'), encoding='utf-8'))
assert man_h['finished'][:10] == UNTIL, 'the window must end on the UTC day of the fetch'
idmap = json.load(open(IDMAP, encoding='utf-8'))
text = open(GUIDE, encoding='utf-8').read()
if GUIDE.endswith('.html'):
    text = re.search(r'<script id="guideData" type="application/json">(.*?)</script>', text, re.S).group(1)
guide = json.loads(text)
kind_of = {i['id']: i['kind'] for i in guide['items']}
assert set(idmap) == set(kind_of)

# ------------------------------------------------------------------ raw data
hist = collections.defaultdict(list)          # item -> [(location, quality, day, price, count)]
for f in man_h['files']:
    blob = json.load(gzip.open(os.path.join(RAW, f['file']), 'rt', encoding='utf-8'))
    for s in blob['rows']:
        for x in s['data']:
            hist[s['item_id']].append((s['location'], s['quality'], x['timestamp'][:10], x['avg_price'], x['item_count']))
orders = collections.defaultdict(list)
for f in man_o['files']:
    blob = json.load(gzip.open(os.path.join(RAW, f['file']), 'rt', encoding='utf-8'))
    for r in blob['rows']:
        orders[r['item_id']].append(r)
t_ord = dt.datetime.strptime(man_o['started'], '%Y-%m-%dT%H:%M:%SZ')
ORDER_FROM = (t_ord - dt.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')


def usable(recs, where):
    return [r for r in recs if r[0] in where and r[1] in (1, 2, 3) and SINCE <= r[2] <= UNTIL and r[3] > 0 and r[4] > 0]


def keep_drop(recs):
    """split records by the 1/3..3x rule around the volume-weighted lower median"""
    if not recs:
        return [], []
    srt = sorted(recs, key=lambda r: r[3])
    cum = list(itertools.accumulate(r[4] for r in srt))
    med = srt[bisect.bisect_left(cum, cum[-1] / 2)][3]
    keep = [r for r in recs if med / 3 <= r[3] <= med * 3]
    drop = [r for r in recs if not (med / 3 <= r[3] <= med * 3)]
    return keep, drop


def wavg(recs):
    units = sum(r[4] for r in recs)
    return round(sum(r[3] * r[4] for r in recs) / units), units


drop_n = collections.Counter()
drop_units = collections.Counter()


def cell(iid):
    recs = hist.get(iid, [])
    city, cdrop = keep_drop(usable(recs, CITIES))
    bm, bdrop = keep_drop(usable(recs, [BM]))
    drop_n['city'] += len(cdrop)
    drop_n['bm'] += len(bdrop)
    drop_units['city'] += sum(r[4] for r in cdrop)
    drop_units['bm'] += sum(r[4] for r in bdrop)
    out = {'id': iid, 'p': None}
    if city:
        p, n = wavg(city)
        rows = []
        for c in CITIES:
            mine = [r for r in city if r[0] == c]
            if mine:
                a, u = wavg(mine)
                rows.append([c, a, u, max(r[2] for r in mine)])
        rows.sort(key=lambda r: (r[1], r[0]))
        out.update(p=p, n=n, d=len({r[2] for r in city}), l=max(r[2] for r in city), c=rows)
    if bm:
        a, u = wavg(bm)
        out['b'] = [a, u, max(r[2] for r in bm)]
    cand = [(r['sell_price_min'], CITIES.index(r['city']), r['quality'], r['sell_price_min_date'])
            for r in orders.get(iid, [])
            if r['city'] in CITIES and r['quality'] in (1, 2, 3) and r['sell_price_min'] > 0 and r['sell_price_min_date'] >= ORDER_FROM]
    if cand:
        price, ci, q, seen = min(cand)
        out['o'] = [price, CITIES[ci], q, seen[:16]]
    return out


fresh = (dt.date.fromisoformat(UNTIL) - dt.timedelta(days=7)).isoformat()
weak = lambda c: c['n'] < LOWN or c['l'] < fresh
items, counts = {}, collections.Counter({k: 0 for k in ('exists', 'city', 'bm', 'cityWeak', 'bmOnly', 'none', 'noneWithOrder', 'noTier')})
by_kind = collections.defaultdict(collections.Counter)
for gid in kind_of:
    m = idmap[gid]
    t = {}
    k = by_kind[kind_of[gid]]
    k['items'] += 1
    for lab in TIERS:
        iid = m['t'][lab]
        if iid is None:
            t[lab] = None
            counts['noTier'] += 1
            k['noTier'] += 1
            continue
        c = cell(iid)
        t[lab] = c
        counts['exists'] += 1
        k['exists'] += 1
        if c['p'] is not None:
            counts['city'] += 1
            k['city'] += 1
            counts['cityWeak'] += weak(c)
        if 'b' in c:
            counts['bm'] += 1
        if c['p'] is None and 'b' in c:
            counts['bmOnly'] += 1
            k['bmOnly'] += 1
        if c['p'] is None and 'b' not in c:
            counts['none'] += 1
            k['none'] += 1
            counts['noneWithOrder'] += 'o' in c
    entry = {'t': t}
    if m['ref']:
        entry['ref'] = [{**cell(iid), 'label': lab} for lab, iid in m['ref']]        # same key order as the 11/13 page
    items[gid] = entry

# ------------------------------------------------------------------ figures for the page text
cells = [c for e in items.values() for c in e['t'].values() if c]
pairs = [c['b'][0] / c['p'] for c in cells if c['p'] is not None and 'b' in c]
prem = collections.defaultdict(list)
for c in cells:
    same = collections.defaultdict(dict)
    for loc, q, day, price, cnt in hist.get(c['id'], []):
        if loc in CITIES and SINCE <= day <= UNTIL and price > 0 and cnt > 0:
            same[(loc, day)][q] = price
    for qs in same.values():
        if 1 in qs:
            for q in (2, 3, 4, 5):
                if q in qs:
                    prem[q].append(qs[q] / qs[1])
by_day = {'city': collections.Counter(), 'bm': collections.Counter()}
for c in cells:
    recs = hist.get(c['id'], [])
    for key, where in (('city', CITIES), ('bm', [BM])):
        for r in keep_drop(usable(recs, where))[0]:
            by_day[key][r[2]] += r[4]
city_units = sum(c['n'] for c in cells if c['p'] is not None)
assert sum(by_day['city'].values()) == city_units
kst = lambda s: dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ') + dt.timedelta(hours=9)
t0, t1 = kst(man_h['started']), kst(man_o['finished'])
label = f'{t0:%Y.%m.%d %H:%M}–{t1:%H:%M}(한국 시간)' if t0.date() == t1.date() else f'{t0:%Y.%m.%d %H:%M}–{t1:%m.%d %H:%M}(한국 시간)'
days = (dt.date.fromisoformat(UNTIL) - dt.date.fromisoformat(SINCE)).days + 1
meta = {'source': 'Albion Online Data Project (east.albion-online-data.com)', 'server': 'Asia', 'since': SINCE, 'until': UNTIL,
        'days': days, 'fresh': fresh, 'lowN': LOWN, 'cities': CITIES, 'qualities': [1, 2, 3],
        'histFetched': [man_h['started'], man_h['finished']], 'ordersFetched': [man_o['started'], man_o['finished']],
        'collectedLabel': label, 'counts': dict(counts), 'dropped': {'city': drop_n['city'], 'bm': drop_n['bm']}, 'tiers': TIERS,
        'ipGroups': {'700': ['4.0'], '800': ['4.1', '5.0'], '900': ['4.2', '5.1', '6.0'], '1000': ['7.0'], '1100': ['8.0']}}
stats = {'byKind': {k: dict(v) for k, v in by_kind.items()}, 'bmOverCityMedian': statistics.median(pairs), 'bmOverCityPairs': len(pairs),
         'bmAboveCityPairs': sum(1 for x in pairs if x > 1), 'cityUnits': city_units, 'droppedUnits': dict(drop_units),
         'droppedCityUnitShare': drop_units['city'] / (city_units + drop_units['city']),
         'qualityPremiumMedian': {q: statistics.median(v) for q, v in sorted(prem.items())}, 'qualityPremiumPairs': {q: len(v) for q, v in sorted(prem.items())},
         'cityUnitsByDay': dict(sorted(by_day['city'].items())), 'bmUnitsByDay': dict(sorted(by_day['bm'].items())),
         'idsQueried': man_h['idsTotal'], 'refIds': sum(len(e.get('ref', [])) for e in items.values()),
         'ordersKept': sum(1 for c in cells if 'o' in c), 'priced': sum(1 for c in cells if c['p'] is not None or 'b' in c),
         'orderFrom': ORDER_FROM}
json.dump({'meta': meta, 'items': items, 'stats': stats}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print(json.dumps(meta, ensure_ascii=False))
print(json.dumps({k: v for k, v in stats.items() if k not in ('cityUnitsByDay', 'bmUnitsByDay')}, ensure_ascii=False))
print('cityUnitsByDay', stats['cityUnitsByDay'])
