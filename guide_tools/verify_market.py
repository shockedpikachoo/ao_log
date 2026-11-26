"""Independent re-computation of every price cell of a built guide from the stored API responses.

Usage: python3 -I verify_market.py <raw dir> <built guide html> <idmap.json> <items.txt of the game data> [report.json]

Does not import build_market.py. It re-reads the raw history and order responses, rebuilds every cell with its own
code (exact integer arithmetic, a different outlier implementation) and compares the result with the data embedded
in the page: prices, units, days, last day, per-city rows and their order, Black Market values, the cheapest sell
order, the reference tiers and every counter of meta.market.
"""
import gzip, json, os, re, sys
from fractions import Fraction

RAW, PAGE, IDMAP, ITEMS_TXT = sys.argv[1:5]
REPORT = sys.argv[5] if len(sys.argv) > 5 else None

html = open(PAGE, encoding='utf-8').read()
m = re.search(r'<script id="guideData" type="application/json">(.*?)</script>', html, re.S)
data = json.loads(m.group(1))
MK = data['meta']['market']
SINCE, UNTIL, FRESH, LOWN = MK['since'], MK['until'], MK['fresh'], MK['lowN']
CUT = MK.get('ordersBefore')            # pre-patch snapshot: orders seen in the 24 h before CUT
CITY = MK['cities']
LABELS = MK['tiers']
problems = []


def bad(msg):
    problems.append(msg)


# ---------------------------------------------------------------- raw responses
man_h = json.load(open(os.path.join(RAW, 'manifest_hist.json'), encoding='utf-8'))
man_o = json.load(open(os.path.join(RAW, 'manifest_orders.json'), encoding='utf-8'))
series = {}                      # (item, location, quality) -> {day: (price, count)}
asked_h, asked_o = [], []
for ent in man_h['files']:
    blob = json.load(gzip.open(os.path.join(RAW, ent['file']), 'rt', encoding='utf-8'))
    asked_h += blob['ids']
    if len(blob['rows']) != ent['rows']:
        bad(f"{ent['file']}: rows {len(blob['rows'])} vs manifest {ent['rows']}")
    for s in blob['rows']:
        key = (s['item_id'], s['location'], s['quality'])
        if key in series:
            bad(f'duplicate series {key}')
        if s['item_id'] not in blob['ids']:
            bad(f"{ent['file']}: series for an item that was not asked: {s['item_id']}")
        days = series.setdefault(key, {})
        for x in s['data']:
            dday = x['timestamp'][:10]
            if x['timestamp'][10:] != 'T00:00:00':
                bad(f'not a daily point: {key} {x["timestamp"]}')
            if dday in days:
                bad(f'duplicate day {key} {dday}')
            days[dday] = (x['avg_price'], x['item_count'])
orders = {}
for ent in man_o['files']:
    blob = json.load(gzip.open(os.path.join(RAW, ent['file']), 'rt', encoding='utf-8'))
    asked_o += blob['ids']
    for r in blob['rows']:
        orders.setdefault(r['item_id'], []).append(r)
if MK['histFetched'] != [man_h['started'], man_h['finished']]:
    bad('histFetched differs from the manifest')
if MK['ordersFetched'] != [man_o['started'], man_o['finished']]:
    bad('ordersFetched differs from the manifest')
if CUT is None and man_h['finished'][:10] != UNTIL:
    bad('window does not end on the UTC day of the fetch')
if CUT is not None and not (man_h['started'] >= CUT + 'Z' and man_o['started'] >= CUT + 'Z'):
    bad('the snapshot was not taken after the cut-off')
if man_h['query']['time-scale'] != '24' or 'east.albion-online-data.com' not in man_h['host']:
    bad('unexpected query')
q0 = [int(x) for x in man_h['query']['date'].split('-')]            # M-D-YYYY
if f'{q0[2]:04d}-{q0[0]:02d}-{q0[1]:02d}' > SINCE:
    bad('the query starts after the window start')
for name in CITY + ['Black Market']:
    if name not in man_h['query']['locations'].split(','):
        bad(f'location not queried: {name}')

# ---------------------------------------------------------------- the IDs: page vs id map vs game data
idmap = json.load(open(IDMAP, encoding='utf-8'))
game_ids = set()
for line in open(ITEMS_TXT, encoding='utf-8'):
    parts = line.split(':')
    if len(parts) >= 2:
        game_ids.add(parts[1].strip())
page_ids = []
for it in data['items']:
    mk = it['market']
    want = idmap[it['id']]
    if list(mk['t']) != LABELS:
        bad(f"{it['id']}: labels {list(mk['t'])}")
    for lab in LABELS:
        c = mk['t'][lab]
        if (c['id'] if c else None) != want['t'][lab]:
            bad(f"{it['id']} {lab}: id {(c or {}).get('id')} vs map {want['t'][lab]}")
        if c:
            page_ids.append(c['id'])
    refs = [(r['label'], r['id']) for r in mk.get('ref', [])]
    if refs != [tuple(x) for x in want['ref']]:
        bad(f"{it['id']}: ref {refs} vs map {want['ref']}")
    page_ids += [r['id'] for r in mk.get('ref', [])]
if len(page_ids) != len(set(page_ids)):
    bad('an item ID is used by two cells')
if set(page_ids) != set(asked_h) or set(page_ids) != set(asked_o):
    bad(f'IDs asked {len(set(asked_h))}/{len(set(asked_o))} vs IDs in the page {len(set(page_ids))}')
if len(asked_h) != len(set(asked_h)) or len(asked_o) != len(set(asked_o)):
    bad('an ID was asked twice')
for i in page_ids:
    if i not in game_ids:
        bad(f'ID not in the game data: {i}')


# ---------------------------------------------------------------- own calculation
def half_even(num, den):
    """round(num/den) to the nearest integer, ties to even, in exact integer arithmetic"""
    q, r = divmod(num, den)
    if 2 * r > den or (2 * r == den and q % 2 == 1):
        q += 1
    return q


def trim(recs):
    """drop records whose price is outside [median/3, median*3]; median = volume-weighted (lower) median"""
    if not recs:
        return [], []
    total = sum(r[3] for r in recs)
    acc, med = 0, None
    for price, count in sorted((r[2], r[3]) for r in recs):
        acc += count
        if 2 * acc >= total:
            med = price
            break
    keep, drop = [], []
    for r in recs:
        # exact comparison: price*3 >= med  and  price <= med*3
        (keep if (3 * r[2] >= med and r[2] <= 3 * med) else drop).append(r)
    return keep, drop


def avg(recs):
    n = sum(r[3] for r in recs)
    return half_even(sum(r[2] * r[3] for r in recs), n), n


by_item = {}
for (iid, loc, q), days in series.items():
    by_item.setdefault(iid, []).append((loc, q, days))


def pool_fast(item, where):
    out = []
    for loc, q, days in by_item.get(item, []):
        if loc in where and q in (1, 2, 3):
            for dday, (price, count) in days.items():
                if SINCE <= dday <= UNTIL and price > 0 and count > 0:
                    out.append((loc, dday, price, count))
    return out


t_orders = (CUT + 'Z') if CUT else man_o['started']          # 'YYYY-MM-DDTHH:MM:SSZ'
y, mo, dd = int(t_orders[:4]), int(t_orders[5:7]), int(t_orders[8:10])
dd -= 1
if dd == 0:
    mo -= 1
    if mo == 0:
        mo, y = 12, y - 1
    dd = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1]
NOT_BEFORE = f'{y:04d}-{mo:02d}-{dd:02d}{t_orders[10:19]}'
NOT_FROM = CUT or '9999'
if CUT is not None:
    cy, cm, cd = int(CUT[:4]), int(CUT[5:7]), int(CUT[8:10])
    uy, um, ud = int(UNTIL[:4]), int(UNTIL[5:7]), int(UNTIL[8:10])
    if not ((cy, cm) == (uy, um) and cd - ud == 1):
        bad('the window does not end the UTC day before the cut-off')

float_ties = 0
dropped = {'city': 0, 'bm': 0}
dropped_units = {'city': 0, 'bm': 0}


def expect_cell(item):
    global float_ties
    city_keep, city_drop = trim(pool_fast(item, CITY))
    bm_keep, bm_drop = trim(pool_fast(item, ['Black Market']))
    dropped['city'] += len(city_drop)
    dropped['bm'] += len(bm_drop)
    dropped_units['city'] += sum(r[3] for r in city_drop)
    dropped_units['bm'] += sum(r[3] for r in bm_drop)
    out = {'id': item, 'p': None}
    if city_keep:
        p, n = avg(city_keep)
        tot = sum(r[2] * r[3] for r in city_keep)
        if Fraction(tot, n).denominator == 2:
            float_ties += 1
        rows = []
        for c in CITY:
            rs = [r for r in city_keep if r[0] == c]
            if rs:
                cp, cn = avg(rs)
                rows.append([c, cp, cn, max(r[1] for r in rs)])
        rows.sort(key=lambda r: (r[1], r[0]))
        out.update({'p': p, 'n': n, 'd': len({r[1] for r in city_keep}), 'l': max(r[1] for r in city_keep), 'c': rows})
    if bm_keep:
        p, n = avg(bm_keep)
        out['b'] = [p, n, max(r[1] for r in bm_keep)]
    best = None
    for r in orders.get(item, []):
        if r['city'] in CITY and r['quality'] in (1, 2, 3) and r['sell_price_min'] > 0 and NOT_BEFORE <= r['sell_price_min_date'] < NOT_FROM:
            cand = (r['sell_price_min'], CITY.index(r['city']), r['quality'], r['sell_price_min_date'])
            if best is None or cand < best:
                best = cand
    if best:
        out['o'] = [best[0], CITY[best[1]], best[2], best[3][:16]]
    return out


weak = lambda n, last: n < LOWN or last < FRESH
cnt = {k: 0 for k in ('exists', 'city', 'bm', 'cityWeak', 'bmOnly', 'none', 'noneWithOrder', 'noTier')}
by_kind = {}
cells = diffs = 0
field_diffs = {}
priced_units = 0
for it in data['items']:
    k = by_kind.setdefault(it['kind'], {'items': 0, 'exists': 0, 'city': 0, 'bmOnly': 0, 'none': 0, 'noTier': 0})
    k['items'] += 1
    for lab in LABELS:
        c = it['market']['t'][lab]
        if c is None:
            cnt['noTier'] += 1
            k['noTier'] += 1
            continue
        want = expect_cell(c['id'])
        cells += 1
        cnt['exists'] += 1
        k['exists'] += 1
        if want['p'] is not None:
            cnt['city'] += 1
            k['city'] += 1
            cnt['cityWeak'] += weak(want['n'], want['l'])
            priced_units += want['n']
        if 'b' in want:
            cnt['bm'] += 1
        if want['p'] is None and 'b' in want:
            cnt['bmOnly'] += 1
            k['bmOnly'] += 1
        if want['p'] is None and 'b' not in want:
            cnt['none'] += 1
            k['none'] += 1
            cnt['noneWithOrder'] += 'o' in want
        if c != want:
            diffs += 1
            for f in sorted(set(c) | set(want)):
                if c.get(f) != want.get(f):
                    field_diffs[f] = field_diffs.get(f, 0) + 1
            if len(problems) < 60:
                bad(f"{it['id']} {lab} ({c['id']}): page {json.dumps(c, ensure_ascii=False)[:300]} vs recomputed {json.dumps(want, ensure_ascii=False)[:300]}")
    for r in it['market'].get('ref', []):
        want = {**expect_cell(r['id']), 'label': r['label']}
        cells += 1
        if r != want:
            diffs += 1
            bad(f"{it['id']} ref {r['label']}: page {json.dumps(r, ensure_ascii=False)[:300]} vs recomputed {json.dumps(want, ensure_ascii=False)[:300]}")
if cnt != MK['counts']:
    bad(f"counts: page {MK['counts']} vs recount {cnt}")
if dropped != MK['dropped']:
    bad(f"dropped: page {MK['dropped']} vs recount {dropped}")
if cnt['exists'] + cnt['noTier'] != 342 * 8 or cnt['city'] + cnt['bmOnly'] + cnt['none'] != cnt['exists']:
    bad('cell totals do not add up')
dday = lambda s: (int(s[:4]), int(s[5:7]), int(s[8:10]))
ys, ms, ds = dday(SINCE)
yu, mu, du = dday(UNTIL)
if (ys, ms) != (yu, mu) or du - ds + 1 != MK['days']:
    bad('days does not match since/until')
yf, mf, df = dday(FRESH)
if (yf, mf, df) != (yu, mu, du - 7):
    bad('fresh is not until - 7 days')

# the figures quoted in the page text
ratios = []
for it in data['items']:
    for c in it['market']['t'].values():
        if c and c['p'] is not None and 'b' in c:
            ratios.append(Fraction(c['b'][0], c['p']))
ratios.sort()
nr = len(ratios)
bm_med = float(ratios[nr // 2] if nr % 2 else (ratios[nr // 2 - 1] + ratios[nr // 2]) / 2)
cell_ids = {c['id'] for it in data['items'] for c in it['market']['t'].values() if c}
prem = {2: [], 3: [], 4: [], 5: []}
for iid in cell_ids:
    same = {}
    for loc, q, days in by_item.get(iid, []):
        if loc in CITY:
            for d2, (price, count) in days.items():
                if SINCE <= d2 <= UNTIL and price > 0 and count > 0:
                    same.setdefault((loc, d2), {})[q] = price
    for qs in same.values():
        if 1 in qs:
            for q in prem:
                if q in qs:
                    prem[q].append(Fraction(qs[q], qs[1]))


def med(v):
    v = sorted(v)
    n = len(v)
    return float(v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2)


summary = {
    'cellsChecked': cells, 'idsChecked': len(page_ids), 'diffs': diffs, 'fieldDiffs': field_diffs, 'counts': cnt, 'dropped': dropped,
    'droppedUnits': dropped_units, 'cityUnits': priced_units,
    'droppedCityUnitShare': dropped_units['city'] / (priced_units + dropped_units['city']),
    'byKind': by_kind, 'bmOverCityMedian': bm_med, 'bmPairs': nr,
    'qualityPremiumMedian': {q: med(v) for q, v in prem.items()}, 'qualityPremiumPairs': {q: len(v) for q, v in prem.items()},
    'exactHalfTies': float_ties, 'ordersNotBefore': NOT_BEFORE,
    'ordersKept': sum(1 for it in data['items'] for c in it['market']['t'].values() if c and 'o' in c),
    'seriesInRaw': len(series), 'idsWithHistory': len({k[0] for k in series}), 'problems': len(problems),
}
print(json.dumps(summary, ensure_ascii=False, indent=1))
for x in problems[:60]:
    print('  !!', x)
if REPORT:
    json.dump(summary, open(REPORT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
sys.exit(1 if problems else 0)
