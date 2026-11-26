"""List every spell (monsters and PvE excluded) that differs between two spells.xml files, ignoring effects/sound/animation attributes.

Usage: python3 -I allspelldiff.py <old spells.xml> <new spells.xml>
"""
import sys, re
import xml.etree.ElementTree as ET
def load(p):
    root = ET.parse(p).getroot()
    out = {}
    for el in root:
        u = el.attrib.get('uniquename')
        if not u: continue
        out[u] = el
    return out
SKIP_ATTR = re.compile(r'(prefab|fx|sound|audio|anim|uisprite|icon|locatag)', re.I)
def canon(el):
    parts = []
    def rec(e, d):
        if e.tag in ('spelleffectfx','AudioInfo') or 'fx' in e.tag.lower(): return
        a = ' '.join(f'{k}={v}' for k, v in sorted(e.attrib.items()) if not SKIP_ATTR.search(k))
        parts.append('  '*d + e.tag + ' ' + a)
        for c in e: rec(c, d+1)
    rec(el, 0)
    return parts
a = load(sys.argv[1]); b = load(sys.argv[2])
changed = []
for u in sorted(set(a) | set(b)):
    if u.startswith('MOB_') or u.startswith('PVE_') : continue
    if u not in a: changed.append((u, 'added')); continue
    if u not in b: changed.append((u, 'removed')); continue
    if canon(a[u]) != canon(b[u]): changed.append((u, 'changed'))
for u, s in changed: print(s, u)
print(len(changed))
