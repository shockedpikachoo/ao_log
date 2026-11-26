"""Independent check of the Patch 5 numbers in the patched guide data against the Patch 5 game data.

Usage: python3 -I verify_patch5.py <guideData_1119.json> <guideData_p5.json> <p4 spells.xml> <p5 spells.xml> <p5 items.xml>

Reads every number straight from the XML (no code shared with apply_patch5.py) and compares it with the value
the guide shows at that placeholder index; also lists every field that differs from the 11/19 data.
"""
import json, re, sys
import xml.etree.ElementTree as ET

OLD, NEW, X4, X5, I5 = sys.argv[1:6]
old, new = json.load(open(OLD, encoding='utf-8')), json.load(open(NEW, encoding='utf-8'))
SP = new['spells']


def spells(path):
    return {e.attrib['uniquename']: e for e in ET.parse(path).getroot() if 'uniquename' in e.attrib}


S5, S4 = spells(X5), spells(X4)
bad = []


def check(sid, idx, expected, what):
    got = SP[sid]['details']['values'][idx]['base']
    if abs(got - expected) > 1e-9:
        bad.append(f'{sid}[{idx}] {what}: guide {got} != data {expected}')


def a(sid, path, attr):
    el = S5[sid] if path is None else S5[sid].find(path)
    assert el is not None, (sid, path)
    return float(el.attrib[attr])


def all_of(sid, tag):
    return [e for e in S5[sid].iter(tag)]


# ---------------------------------------------------------------- Dark Sphere
s = 'ARCANE_METEOR'
check(s, 0, a(s, None, 'hitdelay'), 'hit delay')
check(s, 1, a(s, 'applyspell', 'effectarearadius'), 'impact radius')
check(s, 2, -a(s, 'directattributechange', 'change'), 'impact damage')
check(s, 3, a(s, 'applyspell', 'maxeffectareatargets'), 'aura targets')
check(s, 5, a('ARCANE_METEOR_EFFECT', 'aura', 'auraradius'), 'aura radius')
check(s, 4, a('ARCANE_METEOR_EFFECT', 'aura', 'time'), 'aura time')
check(s, 6, -a('ARCANE_METEOR_PULSE', 'directattributechange', 'change'), 'pulse damage')
check(s, 7, a('ARCANE_METEOR_EFFECT', 'pulsingspell', 'interval'), 'pulse interval')
check(s, 8, -100 * a('ARCANE_METEOR_AURA', 'buffovertime', 'value'), 'slow')
check(s, 9, a(s, None, 'recastdelay'), 'cooldown')
check(s, 10, a(s, None, 'castingtime'), 'cast')
check(s, 11, 100 * a(s, None, 'energyusage'), 'energy %')
check(s, 12, a(s, None, 'castrange'), 'range')
check(s, 13, a(s, None, 'hitdelay'), 'delay row')
check(s, 14, -a('ARCANE_METEOR_PULSE', 'directattributechange', 'change'), 'periodic per tick')
check(s, 15, a('ARCANE_METEOR_EFFECT', 'pulsingspell', 'interval'), 'periodic interval')
check(s, 16, a('ARCANE_METEOR_EFFECT', 'pulsingspell', 'initialinterval'), 'periodic first')
check(s, 17, -a('ARCANE_METEOR_PULSE', 'directattributechange', 'change') * a('ARCANE_METEOR_EFFECT', 'pulsingspell', 'count'), 'periodic total')
assert 'itempowerrecastdelaymodifier' not in S5[s].attrib and S4[s].attrib['itempowerrecastdelaymodifier'] == '-1'
assert a('ARCANE_METEOR_EFFECT', 'pulsingspell', 'count') == 5 and a('ARCANE_METEOR_AURA', None, 'maxcharges') == 1
assert len(all_of('ARCANE_METEOR_AURA', 'buffovertime')) == 1, 'only the slow is left'
assert S5['ARCANE_METEOR_EFFECT'].attrib['category'] == 'damage' and S4['ARCANE_METEOR_EFFECT'].attrib['category'] == 'debuff'
assert a('ARCANE_METEOR_PULSE', 'directattributechange', 'effectarearadius') == 5
assert S5['ARCANE_METEOR_PULSE'].find('directattributechange').attrib['reflectdamage'] == 'never'

# ---------------------------------------------------------------- Battle Rush
s = 'AXE_CHARGE'
check(s, 0, a('AXE_CHARGE_CONDITION', 'applyspell', 'effectarearadius'), 'landing radius')
check(s, 1, 100 * a('AXE_CHARGE_EFFECT', 'healonhit', 'percentage'), 'lifesteal %')
check(s, 2, a('AXE_CHARGE_EFFECT', 'healonhit', 'time'), 'lifesteal time')
check(s, 3, a(s, None, 'recastdelay'), 'cooldown')
check(s, 4, a(s, None, 'castingtime'), 'cast')
check(s, 5, a(s, None, 'energyusage'), 'energy')
check(s, 6, a(s, None, 'castrange'), 'range')
assert 'AXE_CHARGE_EFFECT2' not in S5 and not all_of('AXE_CHARGE_EFFECT', 'buffovertime')
assert S5['AXE_CHARGE_EFFECT'].find('healonhit').attrib['usehealingmodifiers'] == 'false'

# ---------------------------------------------------------------- Whirlwind
s = 'AXEWHIRLWIND2'
ic = [e.attrib['who'] for e in S5[s].iter('IfCharge')]
assert ic and set(ic) == {'Caster'}, ic
assert any(e.attrib.get('spell') == 'AXEWHIRLWIND_STACK' and e.attrib.get('maxeffectareatargets') == '1' for e in S5[s].iter('applyspell'))
assert S5['AXEWHIRLWIND_STACK'].find('dummy').attrib['target'] == 'self'
assert [v['base'] for v in SP[s]['details']['values']] == [v['base'] for v in old['spells'][s]['details']['values']]

# ---------------------------------------------------------------- Lucent Hawk
check('HAWK_SHOT_MULTI1', 0, -a('HAWK_SHOT_EFFECT', 'directattributechange', 'change'), 'damage')

# ---------------------------------------------------------------- Divine Engine
s = 'CROSSBOW_DIVINE_SHOT'
pulse = S5['CROSSBOW_DIVINE_SHOT_EFFECT_PULSE'].find('directattributechange')
ticks = [-float(pulse.attrib['change'])] + [-float(c.attrib['value']) for c in pulse.iter('change') if int(c.attrib['mincharges']) < 99]
eff = S5['CROSSBOW_DIVINE_SHOT_EFFECT'].find('pulsingspell')
tracker = S5[s].find('pulsingspell')
n = int(eff.attrib['count'])
assert n == 9 and int(tracker.attrib['count']) == 9 and len(ticks) == 9
assert all(round(ticks[k + 1] - ticks[k], 9) == 8 for k in range(8)), ticks
# tick k lands at 0.1 + 0.3k; the caster has gained one tracker charge at 0.2, 0.5, ... -> charges before tick k = k
for k in range(9):
    t = float(eff.attrib['initialinterval']) + k * float(eff.attrib['interval'])
    charges = sum(1 for j in range(9) if float(tracker.attrib['initialinterval']) + j * float(tracker.attrib['interval']) < t)
    assert charges == k, (k, t, charges)
check(s, 3, ticks[0], 'first player tick')
check(s, 11, ticks[0], 'periodic first player tick')
check(s, 19, ticks[1] - ticks[0], 'increment')
check(s, 20, ticks[-1], 'last player tick')
check(s, 14, sum(ticks), 'player total')
check(s, 2, float(eff.attrib['interval']), 'interval')
check(s, 12, float(eff.attrib['interval']), 'periodic interval')
check(s, 13, float(eff.attrib['initialinterval']), 'periodic first')
mob = S5['CROSSBOW_DIVINE_SHOT_EFFECT'].find('attributechangeovertime')
check(s, 4, -float(mob.attrib['change']), 'mob tick')
check(s, 15, -float(mob.attrib['change']), 'periodic mob tick')
check(s, 18, -float(mob.attrib['change']) * int(mob.attrib['count']), 'mob total')

# ---------------------------------------------------------------- Sweeping Bolt / Trident / Purifying Combination (hitbox only)
assert [e.attrib['time'] for e in S5['CROSSBOW_ARMORPIERCER'].iter('spelleffectarea') if e.attrib['effect'] == 'CROSSBOW_ARMORPIERCER_EFFECT'] == ['0.3']
assert [e.attrib['time'] for e in S4['CROSSBOW_ARMORPIERCER'].iter('spelleffectarea') if e.attrib['effect'] == 'CROSSBOW_ARMORPIERCER_EFFECT'] == ['0.7']
assert [e.attrib['time'] for e in S5['TRIDENTTHROW_AREA'].iter('spelleffectarea') if e.attrib['effect'] == 'TRIDENTTHROW_EFFECT'] == ['0.2']
assert [e.attrib['time'] for e in S4['TRIDENTTHROW_AREA'].iter('spelleffectarea') if e.attrib['effect'] == 'TRIDENTTHROW_EFFECT'] == ['0.5']
assert [e.attrib['time'] for e in S5['TRIPLECOMBO_POWERPUNCH'].iter('spelleffectarea') if e.attrib['effect'] == 'TRIPLECOMBO_POWERPUNCH_AREA_EFFECT'] == ['0.2']
assert [e.attrib['time'] for e in S4['TRIPLECOMBO_POWERPUNCH'].iter('spelleffectarea') if e.attrib['effect'] == 'TRIPLECOMBO_POWERPUNCH_AREA_EFFECT'] == ['0.5']
for s in ('CROSSBOW_ARMORPIERCER', 'TRIDENTTHROW', 'TRIPLECOMBO_DIVEKICK', 'REJUVENATION'):
    assert SP[s]['details'] == old['spells'][s]['details'], s

# ---------------------------------------------------------------- Slit Throat
s = 'EXECUTEDAGGER'
for k in range(4):
    check(s, k, -a(f'EXECUTEDAGGER_EFFECT{k}', 'directattributechange', 'change'), f'hit {k}')
    assert not all_of(f'EXECUTEDAGGER_EFFECT{k}', 'attributechangeovertime')
rc = S5[s].find('resetcooldowns')
assert rc.attrib == {'amount': '1', 'relative': 'true', 'slot': 'mainhand2', 'target': 'self'}, rc.attrib
assert not [e for e in S5[s].iter('buffovertime') if e.attrib.get('type') == 'healmodifier']
check(s, 4, a(s, None, 'recastdelay'), 'cooldown')
check(s, 5, a(s, None, 'castingtime'), 'cast')
check(s, 6, a(s, None, 'energyusage'), 'energy')
check(s, 7, a(s, None, 'castrange'), 'range')

# ---------------------------------------------------------------- range / radius changes
check('FIREPHOENIX', 9, a('FIREPHOENIX', None, 'castrange'), 'range')
assert SP['FIREPHOENIX']['range'] == '12m' and SP['HOLYFLASH']['range'] == '11m'
check('HOLYFLASH', 6, a('HOLYFLASH', None, 'castrange'), 'range')
ch = S5['FROSTBEAM'].find('channelingspell')
check('FROSTBEAM', 2, float(ch.find('directattributechange').attrib['effectarearadius']), 'damage radius')
assert ch.find('applyspell').attrib['effectarearadius'] == '5'
assert '주변 5m' in SP['FROSTBEAM']['effect'][0]

# ---------------------------------------------------------------- Glacial Obelisk
s = 'ICE_SCULPTURE'
sh = S5['ICE_SCULPTURE_EXPLODE_EFFECT_SHIELD'].find('damageshield')
sl = S5['ICE_SCULPTURE_EXPLODE_EFFECT_SLOW'].find('buffovertime')
check(s, 4, float(sh.attrib['damageabsorbed']), 'shield')
check(s, 5, float(sh.attrib['time']), 'shield time')
check(s, 6, -100 * float(sl.attrib['value']), 'slow')
check(s, 7, float(sl.attrib['time']), 'slow time')
buff_area = S5[s].find('spelleffectarea')
check(s, 0, float(buff_area.attrib['time']), 'obelisk time')
check(s, 2, float(buff_area.attrib['maxeffectareatargets']), 'ally cap')
check(s, 3, float(buff_area.find('area/shape/circle').attrib['radius']), 'radius')
check(s, 1, 100 * float(S5['ICE_SCULPTURE_BUFF'].find('buffovertime').attrib['value']), 'buff')
check(s, 8, a(s, None, 'recastdelay'), 'cooldown')
check(s, 9, a(s, None, 'castingtime'), 'cast')
check(s, 10, a(s, None, 'energyusage'), 'energy')
check(s, 11, a(s, None, 'castrange'), 'range')
check(s, 16, float(S5[s].find('multispell').attrib['timewindow']), 'recast window')
assert not all_of('ICE_SCULPTURE_EXPLODE_EFFECT', 'directattributechange'), 'no damage left'
ex = S5['ICE_SCULPTURE_EXPLODE'].find('spelleffectarea')
assert ex.attrib['target'] == 'all' and ex.find('area/shape/circle').attrib['radius'].startswith('A 0:6;')
auto = [e for e in S5[s].findall('spelleffectarea') if e.attrib['effect'] == 'ICE_SCULPTURE_EXPLODE_EFFECT']
assert len(auto) == 1 and auto[0].attrib['target'] == 'enemy', 'the automatic blast only reaches enemies, so allies get no shield from it'
assert [x.attrib['target'] for x in S5['ICE_SCULPTURE_EXPLODE_EFFECT'].iter('applyspell')] == ['enemy', 'friendall']

# ---------------------------------------------------------------- Well of Life
s = 'WELLOFLIFE2'
inst = S5[s].find('directattributechange')
check(s, 13, float(inst.attrib['change']), 'instant heal')
assert inst.attrib['effectarearadius'] == '7' and inst.attrib['target'] == 'friendall'
hot = S5['WELLOFLIFE2_EFFECT'].find('attributechangeovertime')
total = float(hot.attrib['change']) * int(hot.attrib['count'])
check(s, 12, total, 'periodic total')
check(s, 14, total + float(inst.attrib['change']), 'total with instant')
assert total == 276 and total + 69 == 345

# ---------------------------------------------------------------- Rejuvenation (fix)
assert S5['REJUVENATION'].attrib.get('keepmovingaftercast') == 'true' and 'keepmovingaftercast' not in S4['REJUVENATION'].attrib

# ---------------------------------------------------------------- Devastating Combo
s = 'KNUCKLECOMBO'
st = S5['KNUCKLECOMBO_STUN']
assert st.find('stun') is None and st.find('root') is not None
check(s, 2, float(st.find('root').attrib['time']), 'root time')
check(s, 5, a(s, None, 'recastdelay'), 'cooldown')
assert SP[s]['cooldown'] == 12.0

# ---------------------------------------------------------------- Earth Crusher
s = 'GROWING_PUNCH'
kb = lambda sid: round(float(S5[sid].find('knockback').attrib['distance']) / float(S5[sid].find('knockback').attrib['movespeed']), 9)
check(s, 16, kb('GROWING_PUNCH_KNOCKBACK_SHORT'), 'short knock-up')
check(s, 10, kb('GROWING_PUNCH_KNOCKBACK_LONG'), 'long knock-up')
radii = sorted({float(e.attrib['effectarearadius']) for e in S5['GROWING_PUNCH_HIT'].iter('applyspell') if 'KNOCKBACK' in e.attrib['spell']})
assert radii == [5, 7, 8, 9], radii

# ---------------------------------------------------------------- Displacement Immunity
s = 'DISRUPTIONIMMUNITY'
ims = S5[s].findall('cceffectimmunity')
assert sorted(e.attrib['type'] for e in ims) == ['forcedmovement', 'slow'] and {e.attrib['time'] for e in ims} == {'5'}
check(s, 0, float(ims[0].attrib['effectarearadius']), 'radius')
check(s, 1, float(ims[0].attrib['maxeffectareatargets']), 'cap')
check(s, 2, float(ims[0].attrib['time']), 'duration')
check(s, 3, a(s, None, 'recastdelay'), 'cooldown')

# ---------------------------------------------------------------- Wings of Fire
s = 'IMMUNEAREA'
assert S5[s].find('invincibility').attrib['time'] == '0.48' and S4[s].find('invincibility') is None
types = [e.attrib['type'] for e in S5['IMMUNEAREA_SEA_EFFECT_SELF'].findall('buffovertime')]
assert types == ['magiccooldownreduction'], types
check(s, 2, 100 * float(S5['IMMUNEAREA_SEA_EFFECT_SELF'].find('buffovertime').attrib['value']), 'cooldown rate')
check(s, 0, float(S5[s].find('nop').attrib['effectarearadius']), 'radius')

# ---------------------------------------------------------------- cloth robes
def top_items(path):
    return {e.attrib['uniquename']: e.attrib.get('focusfireprotectionpenetration') for e in ET.parse(path).getroot() if 'uniquename' in e.attrib}


pen4, pen5 = top_items(I5.replace('/p5/', '/p4/')), top_items(I5)
changed_pen = sorted(u for u in pen5 if u in pen4 and pen4[u] != pen5[u])
assert all(pen4[u] is None and pen5[u] == '0.15' for u in changed_pen)
assert all(re.fullmatch(r'T[2-8]_ARMOR_CLOTH_[A-Z0-9]+', u) for u in changed_pen), changed_pen
assert {v for u, v in pen5.items() if u not in changed_pen} <= {None, '0'}, 'no other item gained penetration'
fams = sorted({u.split('_', 1)[1] for u in changed_pen})
guide_cloth = sorted(i['id'] for i in new['items'] if i['id'].startswith('ARMOR_CLOTH'))
assert fams == guide_cloth, (fams, guide_cloth)
for i in new['items']:
    if i['id'].startswith('ARMOR_CLOTH'):
        assert i['patchTag'] == '11.26'
pen = changed_pen

# ---------------------------------------------------------------- what else differs from the 11/19 data
diffs = {}
for k in SP:
    for f in set(SP[k]) | set(old['spells'][k]):
        if SP[k].get(f) != old['spells'][k].get(f):
            diffs.setdefault(k, []).append(f)
for i, j in zip(new['items'], old['items']):
    assert i['id'] == j['id']
    for f in set(i) | set(j):
        if i.get(f) != j.get(f):
            diffs.setdefault('item:' + i['id'], []).append(f)
meta_diff = sorted(f for f in set(new['meta']) | set(old['meta']) if new['meta'].get(f) != old['meta'].get(f))
assert new['images'] == old['images']
print('differences from the 11/19 data:')
for k in sorted(diffs):
    print(' ', k, sorted(diffs[k]))
print('meta:', meta_diff)
print('cloth armor variants with penetration 0.15:', len(pen))
if bad:
    print('PROBLEMS:')
    for b in bad:
        print(' ', b)
    sys.exit(1)
print('OK: all Patch 5 numbers match the game data')
