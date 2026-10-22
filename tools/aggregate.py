"""Aggregate the ao_log collection into the guide's sample statistics.

Usage: python3 tools/aggregate.py <ao_log dir> <guide html or json> <window start KST> <window end KST> <out.json>
       window bounds as 'YYYY-MM-DDTHH:MM' in KST; the end is exclusive. The guide file is the latest
       guide HTML (its <script id="guideData"> block is read) or that block saved as JSON.

Rules (same as the 10/08 sample):
  * a record counts when it is a KILL with exactly one participant and one recorded group member,
    the participant list is the killer and the group list is empty or the killer;
  * both sides are counted (winner + victim), repeat appearances count each time;
  * tier, enchant and quality are merged into the guide item;
  * weapons and armour: share = item count / (2 x records); items outside the guide stay in the
    denominator; empty slots are reported as missing;
  * offhand, cape, bag, potion, food, mount: share = item count / identified (non-empty) slot count.
"""
import collections, datetime as dt, glob, json, os, re, sys

LOG, GUIDE, W0, W1, OUT = sys.argv[1:6]
KST = dt.timezone(dt.timedelta(hours=9))
w0 = dt.datetime.strptime(W0, '%Y-%m-%dT%H:%M').replace(tzinfo=KST).astimezone(dt.timezone.utc)
w1 = dt.datetime.strptime(W1, '%Y-%m-%dT%H:%M').replace(tzinfo=KST).astimezone(dt.timezone.utc)
S0, S1 = w0.strftime('%Y-%m-%dT%H:%M:%SZ'), w1.strftime('%Y-%m-%dT%H:%M:%SZ')
SLOTS = ('MainHand', 'OffHand', 'Head', 'Armor', 'Shoes', 'Bag', 'Cape', 'Mount', 'Potion', 'Food')
EXTRA_SLOT = {'offhand': 'OffHand', 'cape': 'Cape', 'bag': 'Bag', 'potion': 'Potion', 'food': 'Food', 'mount': 'Mount'}
ARMOR_SLOT = {'HEAD': 'Head', 'ARMOR': 'Armor', 'SHOES': 'Shoes'}

def load_guide(path):
    text = open(path, encoding='utf-8').read()
    if path.endswith('.html'):
        # '</' inside the block is written as '<\/', so the first '</script>' closes it
        text = re.search(r'<script id="guideData" type="application/json">(.*?)</script>', text, re.S).group(1)
    return json.loads(text)


guide = load_guide(GUIDE)
items = guide['items']
main_ids = {i['id']: i for i in items if i['kind'] in ('weapon', 'armor')}
uid = {}
for i in items:
    if i['kind'] in EXTRA_SLOT:
        for v in i['variants']:
            uid[v['uid']] = i['id']
extra_ids = {i['id']: i for i in items if i['kind'] in EXTRA_SLOT}


def plain(t):
    return re.sub(r'@\d+$', '', t)


def map_main(t):
    base = re.sub(r'^T\d+_', '', plain(t))
    return base if base in main_ids else None


fallback = collections.Counter()


def map_extra(t):
    u = plain(t)
    if u in uid:
        return uid[u]
    base = re.sub(r'^T\d+_', '', u)
    if base in extra_ids:
        fallback[u] += 1
        return base
    return None


# ------------------------------------------------------------------ load and de-duplicate
rows, lines = {}, 0
for f in glob.glob(os.path.join(LOG, 'data', '*', '*.jsonl')):
    with open(f, encoding='utf-8') as fh:
        for line in fh:
            r = json.loads(line)
            lines += 1
            rows[r['i']] = r
inwin = [r for r in rows.values() if S0 <= r['t'] < S1]
excluded = collections.Counter()
solo = []
for r in inwin:
    if r.get('n') != 1:
        excluded['not_single_participant'] += 1
    elif r.get('g') != 1:
        excluded['not_single_group_member'] += 1
    elif r.get('ty') != 'KILL':
        excluded['not_kill_event'] += 1
    elif not (r.get('pk') and r.get('gk')):
        excluded['roster_not_matching_killer'] += 1
    else:
        solo.append(r)
solo.sort(key=lambda r: (r['t'], r['i']))

# ------------------------------------------------------------------ count
cnt = collections.defaultdict(lambda: {'count': 0, 'winner': 0, 'victim': 0})
armor = {s: {'mapped': 0, 'gathering': 0, 'missing': 0, 'outside': collections.Counter()} for s in ARMOR_SLOT}
weap = {'mapped': 0, 'missing': 0, 'outside': collections.Counter()}
extra = {k: {'equipped': 0, 'empty': 0, 'mapped': 0, 'outside': collections.Counter()} for k in EXTRA_SLOT}
daily = collections.Counter()
for r in solo:
    day = (dt.datetime.strptime(r['t'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc).astimezone(KST)).strftime('%m/%d')
    daily[day] += 1
    for side, gear in (('winner', r['ke']), ('victim', r['ve'])):
        g = dict(zip(SLOTS, gear))
        # main hand
        t = g['MainHand']
        if not t:
            weap['missing'] += 1
        else:
            k = map_main(t)
            if k and main_ids[k]['kind'] == 'weapon':
                weap['mapped'] += 1
                cnt[k]['count'] += 1
                cnt[k][side] += 1
            else:
                weap['outside'][plain(t)] += 1
        for s, slot in ARMOR_SLOT.items():
            t = g[slot]
            if not t:
                armor[s]['missing'] += 1
                continue
            k = map_main(t)
            if k and main_ids[k]['kind'] == 'armor' and main_ids[k]['slot'] == s:
                armor[s]['mapped'] += 1
                cnt[k]['count'] += 1
                cnt[k][side] += 1
            else:
                armor[s]['gathering'] += 1
                armor[s]['outside'][plain(t)] += 1
        for kind, slot in EXTRA_SLOT.items():
            t = g[slot]
            if not t:
                extra[kind]['empty'] += 1
                continue
            extra[kind]['equipped'] += 1
            k = map_extra(t)
            if k and extra_ids[k]['kind'] == kind:
                extra[kind]['mapped'] += 1
                cnt[k]['count'] += 1
                cnt[k][side] += 1
            else:
                extra[kind]['outside'][plain(t)] += 1


def ranks(ids):
    """competition ranking by count; 0 = not observed (None)"""
    order = sorted(ids, key=lambda k: -cnt[k]['count'])
    out, prev, rank = {}, None, 0
    for n, k in enumerate(order, 1):
        c = cnt[k]['count']
        if c != prev:
            rank, prev = n, c
        out[k] = rank if c > 0 else None
    return out


obs = 2 * len(solo)
res = {'window': [S0, S1], 'windowKst': [W0, W1], 'events': len(solo), 'observations': obs,
       'firstEvent': solo[0]['t'], 'lastEvent': solo[-1]['t'], 'excluded': dict(excluded),
       'uniqueInWindow': len(inwin), 'uniqueAll': len(rows), 'storedLines': lines,
       'daily': dict(sorted(daily.items())), 'items': {}, 'armor': {}, 'weapons': {}, 'extras': {},
       'fallbackMapped': dict(fallback)}
for s in ARMOR_SLOT:
    ids = [k for k, i in main_ids.items() if i['kind'] == 'armor' and i['slot'] == s]
    rk = ranks(ids)
    for k in ids:
        res['items'][k] = {**cnt[k], 'share': cnt[k]['count'] / obs, 'rank': rk[k]}
    a = armor[s]
    assert a['mapped'] + a['gathering'] + a['missing'] == obs, s
    res['armor'][s] = {'mapped': a['mapped'], 'gathering': a['gathering'], 'missing': a['missing'],
                       'outsideTop': a['outside'].most_common(8)}
wids = [k for k, i in main_ids.items() if i['kind'] == 'weapon']
rk = ranks(wids)
for k in wids:
    res['items'][k] = {**cnt[k], 'share': cnt[k]['count'] / obs, 'rank': rk[k]}
assert weap['mapped'] + weap['missing'] + sum(weap['outside'].values()) == obs
res['weapons'] = {'mapped': weap['mapped'], 'missing': weap['missing'], 'outside': dict(weap['outside'])}
for kind in EXTRA_SLOT:
    ids = [k for k, i in extra_ids.items() if i['kind'] == kind]
    rk = ranks(ids)
    e = extra[kind]
    assert e['equipped'] + e['empty'] == obs and e['mapped'] + sum(e['outside'].values()) == e['equipped'], kind
    for k in ids:
        res['items'][k] = {**cnt[k], 'share': (cnt[k]['count'] / e['equipped']) if e['equipped'] else 0, 'rank': rk[k]}
    res['extras'][kind] = {'slot': EXTRA_SLOT[kind], 'equipped': e['equipped'], 'empty': e['empty'], 'mapped': e['mapped'],
                           'outside': dict(e['outside']), 'outsideCount': sum(e['outside'].values()), 'families': len(ids)}

# ------------------------------------------------------------------ collection health in the window
polls = failed = gaps = warns = 0
runs = set()
for f in glob.glob(os.path.join(LOG, 'logs', '*', '*.jsonl')):
    for line in open(f, encoding='utf-8'):
        x = json.loads(line)
        if not (S0 <= x.get('at', '') < S1):
            continue
        runs.add(os.path.basename(f)[:-6])
        if 'pages' in x:
            polls += 1
            failed += bool(x.get('failed'))
        if 'warn' in x:
            warns += 1
ts = sorted(r['t'] for r in inwin)
p = lambda s: dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')
quiet = [(a, b, (p(b) - p(a)).total_seconds()) for a, b in zip(ts, ts[1:]) if (p(b) - p(a)).total_seconds() > 240]
res['health'] = {'runs': len(runs), 'polls': polls, 'failedPolls': failed, 'fetchWarnings': warns,
                 'quietStretches': [{'fromKst': (p(a) + dt.timedelta(hours=9)).strftime('%m/%d %H:%M:%S'),
                                     'toKst': (p(b) + dt.timedelta(hours=9)).strftime('%m/%d %H:%M:%S'),
                                     'minutes': round(s / 60, 1)} for a, b, s in quiet]}
json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: res[k] for k in ('events', 'observations', 'firstEvent', 'lastEvent', 'excluded', 'uniqueInWindow',
                                      'daily', 'fallbackMapped', 'health')}, ensure_ascii=False, indent=1))
print('armor', {s: (v['mapped'], v['gathering'], v['missing']) for s, v in res['armor'].items()})
print('weapons', res['weapons']['mapped'], res['weapons']['missing'], sum(res['weapons']['outside'].values()))
print('extras', {k: (v['equipped'], v['empty'], v['mapped'], v['outsideCount']) for k, v in res['extras'].items()})
