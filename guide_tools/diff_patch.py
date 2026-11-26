"""Which guide spells and items changed between two game data extracts?

Usage: python3 -I diff_patch.py <old dump dir> <new dump dir> <guideData.json> <out.json>
Spells: every guide spell id and every spell it reaches (attribute values that name another spell), compared as
element trees (tag, attributes, children). Items: every uniquename of the guide's items (all tiers/enchantments
found in items.xml for weapons/armor; variant uids for extras). Prints a readable line diff per change.
"""
import difflib, json, re, sys
import xml.etree.ElementTree as ET

OLD, NEW, GUIDE, OUT = sys.argv[1:5]
d = json.load(open(GUIDE, encoding='utf-8'))


def load_spells(path):
    out = {}
    for el in ET.parse(path).getroot():
        u = el.get('uniquename')
        if u:
            out[u] = el
    return out


def load_items(path):
    out = {}
    for el in ET.parse(path).getroot().iter():
        u = el.get('uniquename')
        if u and el.tag not in ('craftspell', 'spell', 'craftresource', 'enchantment') and u not in out:
            out[u] = el
    return out


def canon(el):
    return (el.tag, tuple(sorted(el.attrib.items())), tuple(canon(c) for c in el))


def pretty(el):
    lines = []

    def rec(e, depth):
        attrs = ' '.join(f'{k}="{v}"' for k, v in sorted(e.attrib.items()))
        lines.append('  ' * depth + f'<{e.tag} {attrs}>')
        for c in e:
            rec(c, depth + 1)
    rec(el, 0)
    return lines


def reach(el, spells, seen):
    for x in el.iter():
        for v in x.attrib.values():
            for part in re.split(r'[\s,;|]+', str(v)):
                if part in spells and part not in seen:
                    seen.add(part)
                    reach(spells[part], spells, seen)
    return seen


so, sn = load_spells(f'{OLD}/spells.xml'), load_spells(f'{NEW}/spells.xml')
io, inw = load_items(f'{OLD}/items.xml'), load_items(f'{NEW}/items.xml')
report = {'spells': {}, 'items': {}}
for sid in d['spells']:
    a, b = so.get(sid), sn.get(sid)
    if a is None or b is None:
        report['spells'][sid] = {'missing': 'old' if a is None else 'new'}
        continue
    ra, rb = reach(a, so, {sid}), reach(b, sn, {sid})
    changes = []
    for s in sorted(ra | rb):
        ea, eb = so.get(s), sn.get(s)
        if ea is None or eb is None:
            changes.append({'spell': s, 'status': 'added' if ea is None else 'removed'})
            continue
        if canon(ea) != canon(eb):
            diff = [l for l in difflib.unified_diff(pretty(ea), pretty(eb), lineterm='', n=0) if not l.startswith(('---', '+++', '@@'))]
            changes.append({'spell': s, 'status': 'changed', 'diff': diff})
    if changes:
        report['spells'][sid] = {'ko': d['spells'][sid]['ko'], 'en': d['spells'][sid].get('en'), 'changes': changes}

# items: all tiers / enchantments of the guide items
names = {}
for it in d['items']:
    if it['kind'] in ('weapon', 'armor'):
        rx = re.compile(r'^T\d_' + re.escape(it['id']) + r'(@\d)?$')
        names[it['id']] = sorted(u for u in set(io) | set(inw) if rx.match(u))
    else:
        names[it['id']] = sorted({v['uid'] for v in it.get('variants') or []})
for gid, us in names.items():
    ch = []
    for u in us:
        a, b = io.get(u), inw.get(u)
        if a is None or b is None:
            ch.append({'uid': u, 'status': 'added' if a is None else 'removed'})
        elif canon(a) != canon(b):
            diff = [l for l in difflib.unified_diff(pretty(a), pretty(b), lineterm='', n=0) if not l.startswith(('---', '+++', '@@'))]
            ch.append({'uid': u, 'status': 'changed', 'diff': diff})
    if ch:
        it = next(i for i in d['items'] if i['id'] == gid)
        report['items'][gid] = {'ko': it['ko'], 'kind': it['kind'], 'slot': it.get('slot'), 'variants': len(us), 'changes': ch}
json.dump(report, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('changed guide spells:', len(report['spells']))
for sid, r in report['spells'].items():
    print(f"  {sid} ({r.get('ko')} / {r.get('en')}): " + ', '.join(f"{c['spell']}[{c['status']}]" for c in r.get('changes', [])) if 'changes' in r else f'  {sid}: {r}')
print('changed guide items:', len(report['items']))
for gid, r in report['items'].items():
    print(f"  {gid} ({r['ko']}, {r['kind']} {r['slot'] or ''}): {len(r['changes'])}/{r['variants']} variants changed")
