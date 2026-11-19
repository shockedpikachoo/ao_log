"""Independent recount of the ranking sample, written separately from ao_log/tools/aggregate.py.

Usage: python3 -I recount.py <ao_log dir> <guide html (item list)> <start KST> <end KST> <target> [out.json]
  target = an aggregate.py output (.json)  -> compares counts, winner/victim, shares, ranks, co-usage, totals
         = a built guide page (.html)      -> compares the same figures as stored in the page (items[] and co)
Rules: KILL records with one participant and one group member whose participant/group lists are the killer;
both sides counted; tier/enchant/quality merged; weapon/armour share = count / (2 x records); extras share =
count / non-empty slots of that kind; competition ranking (unseen = no rank); co-usage = top 3 guide items per
other slot of the same loadout, ties broken by item id.
"""
import collections, datetime as dt, glob, json, os, re, sys

LOG, GUIDE, A, B, TARGET = sys.argv[1:6]
OUT = sys.argv[6] if len(sys.argv) > 6 else None
KST = dt.timezone(dt.timedelta(hours=9))
utc = lambda s: dt.datetime.strptime(s, '%Y-%m-%dT%H:%M').replace(tzinfo=KST).astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
LO, HI = utc(A), utc(B)


def page_data(path):
    txt = open(path, encoding='utf-8').read()
    return json.loads(txt[txt.index('<script id="guideData" type="application/json">') + 47:].split('</script>', 1)[0])


g = page_data(GUIDE)
ITEM = {i['id']: i for i in g['items']}
ORDER = ['MainHand', 'OffHand', 'Head', 'Armor', 'Shoes', 'Bag', 'Cape', 'Mount', 'Potion', 'Food']
KIND_SLOT = {'offhand': 1, 'bag': 5, 'cape': 6, 'mount': 7, 'potion': 8, 'food': 9}
ARMOR_POS = {'HEAD': 2, 'ARMOR': 3, 'SHOES': 4}
by_variant = {}
for i in g['items']:
    for v in i.get('variants') or []:
        if i['kind'] in KIND_SLOT:
            by_variant.setdefault(v['uid'], i['id'])
rx = re.compile(r'^T(\d+)_(.+?)(?:@(\d+))?$')


def main_item(t, kind, slot=None):
    m = rx.match(t)
    if not m:
        return None
    it = ITEM.get(m.group(2))
    if not it or it['kind'] != kind or (slot and it.get('slot') != slot):
        return None
    return it['id']


def extra_item(t, kind):
    u = t.split('@')[0]
    gid = by_variant.get(u)
    if gid is None:
        m = rx.match(t)
        gid = m.group(2) if m and m.group(2) in ITEM and ITEM[m.group(2)]['kind'] in KIND_SLOT else None
    return gid if gid and ITEM[gid]['kind'] == kind else None


seen = {}
for f in sorted(glob.glob(os.path.join(LOG, 'data', '*', '*.jsonl'))):
    for line in open(f, encoding='utf-8'):
        r = json.loads(line)
        if LO <= r['t'] < HI:
            seen[r['i']] = r
recs = [r for r in seen.values() if r.get('n') == 1 and r.get('g') == 1 and r.get('ty') == 'KILL' and r.get('pk') and r.get('gk')]
E = len(recs)
count = collections.Counter()
side = {'winner': collections.Counter(), 'victim': collections.Counter()}
equipped = collections.Counter()
co = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
for r in recs:
    for who, gear in (('winner', r['ke']), ('victim', r['ve'])):
        lo = {}
        if gear[0]:
            k = main_item(gear[0], 'weapon')
            if k:
                lo['WEAPON'] = k
        for s, pos in ARMOR_POS.items():
            if gear[pos]:
                k = main_item(gear[pos], 'armor', s)
                if k:
                    lo[s] = k
        for kind, pos in KIND_SLOT.items():
            if gear[pos]:
                equipped[kind] += 1
                k = extra_item(gear[pos], kind)
                if k:
                    lo[kind] = k
        for k in lo.values():
            count[k] += 1
            side[who][k] += 1
        for a in ('WEAPON', 'HEAD', 'ARMOR', 'SHOES'):
            if a in lo:
                for s, k in lo.items():
                    if s != a:
                        co[lo[a]][s][k] += 1


def group_of(i):
    return ('armor', i['slot']) if i['kind'] == 'armor' else (i['kind'],)


groups = collections.defaultdict(list)
for i in g['items']:
    groups[group_of(i)].append(i['id'])
want = {}
for grp, ids in groups.items():
    vals = sorted((count[k] for k in ids), reverse=True)
    for k in ids:
        c = count[k]
        rank = (vals.index(c) + 1) if c else None
        den = 2 * E if grp[0] in ('weapon', 'armor') else equipped[grp[0]]
        want[k] = {'count': c, 'winner': side['winner'][k], 'victim': side['victim'][k], 'share': c / den if den else 0, 'rank': rank}
want_co = {a: {s: [[k, n] for k, n in sorted(c.items(), key=lambda x: (-x[1], x[0]))[:3]] for s, c in sl.items()} for a, sl in co.items()}

problems = []
if TARGET.endswith('.json'):
    t = json.load(open(TARGET, encoding='utf-8'))
    if t['events'] != E or t['observations'] != 2 * E or t['uniqueInWindow'] != len(seen):
        problems.append(f"totals {t['events']}/{t['uniqueInWindow']} vs {E}/{len(seen)}")
    for k, w in want.items():
        got = t['items'][k]
        for f in ('count', 'winner', 'victim', 'rank'):
            if got[f] != w[f]:
                problems.append(f'{k} {f}: {got[f]} vs {w[f]}')
        if abs(got['share'] - w['share']) > 1e-12:
            problems.append(f"{k} share {got['share']} vs {w['share']}")
    tco = {a: {s: [list(x) for x in v] for s, v in sl.items()} for a, sl in t['co'].items()}
    if tco != want_co:
        problems.append('co-usage differs: ' + str(sorted(set(tco) ^ set(want_co)))[:200])
        for a in sorted(set(tco) & set(want_co)):
            if tco[a] != want_co[a]:
                problems.append(f'  co {a}: {tco[a]} vs {want_co[a]}')
                break
    for kind in KIND_SLOT:
        if t['extras'][kind]['equipped'] != equipped[kind]:
            problems.append(f'equipped {kind}')
else:
    p = page_data(TARGET)
    for i in p['items']:
        w = want[i['id']]
        for f in ('count', 'winner', 'victim', 'rank'):
            if i.get(f) != w[f]:
                problems.append(f"{i['id']} {f}: page {i.get(f)} vs {w[f]}")
        if abs((i.get('share') or 0) - w['share']) > 1e-9:
            problems.append(f"{i['id']} share: page {i.get('share')} vs {w['share']}")
        if i['kind'] in ('weapon', 'armor'):
            exp = {s: v for s, v in want_co.get(i['id'], {}).items() if s != 'bag'}
            got = i.get('co') or {}
            if got != exp:
                problems.append(f"{i['id']} co: page {json.dumps(got)[:200]} vs {json.dumps(exp)[:200]}")
summary = {'records': E, 'observations': 2 * E, 'uniqueInWindow': len(seen), 'items': len(want), 'seenItems': sum(1 for w in want.values() if w['count']),
           'coAnchors': len(want_co), 'equipped': dict(equipped), 'problems': len(problems)}
print(json.dumps(summary, ensure_ascii=False))
for x in problems[:40]:
    print('  !!', x)
if OUT:
    json.dump({'summary': summary, 'items': want, 'co': want_co}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
sys.exit(1 if problems else 0)
