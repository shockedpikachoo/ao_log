"""Apply Dragonfire Patch 5 (2026-11-26) to the guide data of the 2026-11-19 page.

Usage: python3 -I apply_patch5.py <guideData_1119.json> <out guideData_p5.json>

Source of every number: ao-bin-dumps d277a5c (Patch 5) spells.xml / items.xml, compared with 0483dd9 (Patch 4),
and the official changelog (Steam announcement 1850460852984814). Only fields that the patch changes are touched;
every old value that is replaced is asserted first, so a template mismatch stops the script.
"""
import copy, json, sys

SRC, OUT = sys.argv[1:3]
d = json.load(open(SRC, encoding='utf-8'))
SP, M = d['spells'], d['meta']
ITEMS = {i['id']: i for i in d['items']}
BEFORE = copy.deepcopy(d)

TAG, TITLE, FIX_TITLE = '11.26', '11월 26일 패치 5 변경', '11월 26일 패치 5 오류 수정'
CHANGELOG = 'https://steamcommunity.com/games/761890/announcements/detail/1850460852984814'
PERIODIC_NOTE = ('반복 구조는 해당 지속 효과가 한 번 부여된 경우의 수치입니다. 중첩·갱신·재부여는 별도이며, '
                 '중간 이탈·정화·면역·집중 중단 시 전부 적용되지 않을 수 있습니다.')
CC_NOTE = '제어 시간에 표시한 기본값은 IP·제어 지속 보너스·상대 제어 저항·점감 적용 전입니다. 아래 IP 입력으로 제어 시간은 환산하지 않습니다.'


def V(base, unit='', scale='fixed', derived=False):
    v = {'base': float(base), 'unit': unit, 'scale': scale}
    if derived:
        v['derived'] = True
    return v


def row(label, text):
    return {'label': label, 'text': text}


def expect(s, field, old):
    assert s[field] == old, (s['id'], field, s[field])


def setv(s, n, old, new):
    v = s['details']['values'][n]
    assert v['base'] == old, (s['id'], n, v)
    v['base'] = float(new)


def patch(s, text, title=TITLE):
    s['patch'], s['patchTag'], s['patchTitle'] = text, TAG, title


def counters(s, skills):
    assert [c['skill'] for c in s['counters']] == skills, (s['id'], [c['skill'] for c in s['counters']])


def standard_counter(skill, label):
    """first counter of that skill and label anywhere in the guide (the texts are shared)"""
    for x in SP.values():
        for c in x.get('counters', []):
            if c['skill'] == skill and c['label'] == label:
                return copy.deepcopy(c)
    raise KeyError(skill)


# ====================================================================== Arcane: Dark Sphere (Evensong)
s = SP['ARCANE_METEOR']
expect(s, 'cooldown', 38.0)
counters(s, ['SELF_CLEANSE', 'AVALON_BEAM', 'BLOCK'])
s['one'] = '구체로 큰 마법 피해를 주고, 적 1명에게 주변을 지속 공격·둔화하는 오라를 붙임'
s['tags'] = ['공격', '방해']
s['effect'] = ['0.4초 후에 떨어지는 어둠의 구를 불러옵니다.',
               '5m 범위 안의 모든 적에게 일정량의 마법 피해를 줍니다.',
               '맞은 적 1명에게 어둠의 오라를 부여합니다.',
               '어둠의 오라는 5초 동안 오라가 붙은 적 주변 5m 범위에 펼쳐집니다.',
               '0.9초마다 오라 범위 안의 적에게 일정량의 마법 피해를 줍니다 (반사할 수 없음).',
               '오라 범위 안의 적은 25%만큼 느려집니다.']
s['when'] = '적이 모인 곳에 구체를 떨어뜨리세요. 오라가 붙은 적 주변 5m에 남은 적은 5초 동안 0.9초마다 추가 피해를 받고 25% 느려집니다.'
s['watch'] = ('패치 5부터 받는 회복량·주는 피해 감소는 없고, 오라는 맞은 적 1명에게만 붙습니다. 오라 범위를 벗어나면 추가 피해와 둔화를 받지 않습니다. '
              '쿨타임은 아이템 파워와 관계없이 25초입니다.')
s['cooldown'], s['cooldownLabel'] = 25.0, '25초'
s['details'] = {
    'lines': ['⟦0⟧ 후에 떨어지는 어둠의 구를 불러옵니다.',
              '⟦1⟧ 범위 안의 모든 적에게 ⟦2⟧의 마법 피해를 줍니다.',
              '맞은 적 ⟦3⟧명에게 어둠의 오라를 부여합니다.',
              '어둠의 오라는 ⟦4⟧ 동안 오라가 붙은 적 주변 ⟦5⟧ 범위에 펼쳐집니다.',
              '⟦7⟧마다 오라 범위 안의 적에게 ⟦6⟧의 마법 피해를 줍니다 (반사할 수 없음).',
              '오라 범위 안의 적은 ⟦8⟧만큼 느려집니다.'],
    'values': [V(0.4, '초'), V(5, 'm'), V(179, '', 'health'), V(1), V(5, '초'), V(5, 'm'), V(31, '', 'health'), V(0.9, '초'), V(25, '%'),
               V(25, '초'), V(0.4, '초'), V(16, '% 최대 에너지'), V(15, 'm'), V(0.4, '초'),
               V(31, '', 'health'), V(0.9, '초'), V(0.9, '초'), V(155, '', 'health', True)],
    'stages': [{'label': '기본 사용', 'rows': [row('기본 쿨타임', '⟦9⟧'), row('시전 시간', '⟦10⟧'), row('에너지 소모', '⟦11⟧'),
                                            row('시전 거리', '⟦12⟧'), row('발동 지연', '⟦13⟧')]}],
    'periodic': [row('체력 피해의 반복 구조', '회당 ⟦14⟧ · ⟦15⟧ 간격 · 5회 · 효과 부여 후 첫 발동 ⟦16⟧ · 전부 적용 시 ⟦17⟧')],
    'notes': [PERIODIC_NOTE, '0.9초마다 들어오는 피해는 오라가 붙은 적을 중심으로 반경 5m 안의 적 모두에게 들어갑니다(오라가 붙은 적 포함).'],
    'unresolved': []}
es = standard_counter('EMERGENCY_SHIELD', '지속 피해 제거')
es['effect'] = '어둠의 오라가 붙은 대상(자신 또는 5m 안의 아군)에게 긴급 보호막을 걸어 오라를 지우고 보호막을 얻습니다.'
es['condition'] = '패치 5부터 어둠의 오라는 지속 피해 제거 말고는 정화로 지울 수 없습니다. 이미 맞은 구체 피해는 되돌리지 않습니다.'
s['counters'] = [es] + s['counters'][1:]
assert s['counterNotes'] == []
s['counterNotes'] = ['패치 5부터 어둠의 오라는 지속 피해 제거 효과로만 지울 수 있습니다. 가죽 머리의 정화 같은 일반 정화로는 지워지지 않습니다.']
patch(s, '광역 약화 위주에서 확실한 피해 위주로 바뀌었습니다. 구체 피해 112 → 179, 오라를 받는 적 3명 → 1명이 되었고, 오라 주변 5m의 적에게 '
         '0.9초마다 마법 피해 31(5회, 합계 155)이 새로 들어갑니다. 주는 피해·받는 회복량 감소와 중첩은 없어지고 둔화는 15% → 25%가 되었습니다. '
         '아이템 파워에 따라 줄던 쿨타임(기본 38초)은 고정 25초가 되었고, 지속 피해 제거 말고는 정화로 지울 수 없습니다.')

# ====================================================================== Axes: Battle Rush (all axes)
s = SP['AXE_CHARGE']
counters(s, ['SELF_CLEANSE'])
expect(s, 'cooldown', 18.0)
s['one'] = '돌진해 적 근처에 착지하면 4초 동안 가한 피해의 15%를 체력으로 회복'
s['tags'] = ['기동', '생존']
s['effect'] = ['목표 위치로 돌진해 전투에 뛰어듭니다.',
               '착지 지점 반경 5m 안에 적이 한 명 이상 있으면 4초 동안 가한 피해의 15%만큼 체력을 회복합니다.']
s['when'] = '적 무리 가까이 돌진해 착지한 뒤 4초 안에 피해를 몰아 넣어 체력을 회복하세요. 착지 지점 5m 안에 적이 없으면 회복 효과가 붙지 않습니다.'
s['watch'] = '피해를 주지 않는 이동기입니다. 회복은 착지 뒤 4초 동안 직접 가한 피해에 비례하므로, 그동안 공격하지 못하면 회복도 없습니다.'
s['details'] = {
    'lines': ['목표 위치로 돌진해 전투에 뛰어듭니다.',
              '착지 지점 반경 ⟦0⟧ 안에 적이 한 명 이상 있으면 ⟦2⟧ 동안 가한 피해의 ⟦1⟧만큼 체력을 회복합니다.'],
    'values': [V(5, 'm'), V(15, '%'), V(4, '초'), V(18, '초'), V(0, '초'), V(11), V(12, 'm')],
    'stages': [{'label': '기본 사용', 'rows': [row('기본 쿨타임', '⟦3⟧'), row('시전 시간', '⟦4⟧'), row('에너지 소모', '⟦5⟧'), row('시전 거리', '⟦6⟧')]}],
    'periodic': [], 'notes': [], 'unresolved': []}
s['counters'] = []          # the healing-received debuff it cleansed no longer exists; the new lifesteal ignores healing modifiers in the data
patch(s, '도착 지점 적의 받는 회복량 감소(20%·3초)와 아군의 받는 회복량 증가(20%·4초)가 없어졌습니다. '
         '대신 착지 지점 5m 안에 적이 있으면 4초 동안 가한 피해의 15%를 체력으로 회복합니다.')

# ====================================================================== Axes: Whirlwind (Greataxe)
s = SP['AXEWHIRLWIND2']
assert s['details']['lines'][2] == '같은 적을 연속으로 맞힐 때마다 그 적에게 주는 피해가 ⟦6⟧씩 증가합니다.'
s['one'] = '이동하며 회전하고 적을 이어 맞힐수록 강해짐'
s['effect'][2] = '적을 연속으로 맞힐 때마다 피해가 일정량씩 증가합니다 (맞히는 적이 바뀌어도 이어집니다).'
s['details']['lines'][2] = '적을 연속으로 맞힐 때마다 피해가 ⟦6⟧씩 증가합니다 (맞히는 적이 바뀌어도 이어집니다).'
expect(s, 'when', '상대에게 붙은 뒤 반경 5m 안에 두고 따라다니며 도세요. 같은 적을 연속으로 맞힐수록 피해가 커져, 6번을 모두 맞히면 마지막 타격은 88.5입니다.')
s['when'] = '상대에게 붙은 뒤 반경 5m 안에 두고 따라다니며 도세요. 매 타격에 적을 한 명이라도 맞히면 피해가 계속 커져, 6번을 모두 이어 맞히면 마지막 타격은 88.5입니다.'
patch(s, '피해 증가가 같은 적을 이어 맞힐 때만 쌓이던 방식에서, 매 타격에 아무 적이라도 맞히면 계속 쌓이는 방식으로 바뀌었습니다. '
         '한 명이 빠져나가도 다른 적을 맞히는 동안 피해가 계속 커집니다. 기본 피해(56)와 증가량(6.5)은 그대로입니다.')

# ====================================================================== Bows: Lucent Hawk (Mistpiercer)
s = SP['HAWK_SHOT_MULTI1']
setv(s, 0, 178, 169)
patch(s, '한 발당 피해가 178에서 169로 줄었습니다. 천 몸통에 회복력 관통 15%가 붙는 변경을 함께 고려한 조정입니다.')

# ====================================================================== Crossbows: Divine Engine (Energy Shaper)
s = SP['CROSSBOW_DIVINE_SHOT']
dd = s['details']
assert [v['base'] for v in dd['values']] == [2.6, 26, 0.3, 106, 70, 35, 0.7, 29, 26, 2.6, 2.6, 106, 0.3, 0.1, 954, 70, 0.3, 0.1, 630]
s['one'] = '방향을 천천히 돌리며 오래 유지할수록 강해지는 긴 에너지 광선'
s['effect'] = ['최대 2.6초 동안 집중을 유지하여 모든 적을 관통하는 26m 길이의 아발론 에너지 광선을 방출합니다 (방해 불가).',
               '0.3초마다 일정량의 마법 피해를 입힙니다.',
               '플레이어에게 주는 피해는 0.3초마다 일정량씩 증가합니다.',
               '광선은 커서 위치를 천천히 따라갑니다.']
s['when'] = '피하기 좁은 곳이나 상대의 이동기가 빠진 순간에 광선을 겹쳐 두세요. 플레이어 대상 피해는 뒤로 갈수록 커지므로 제어기로 묶어 둔 상대에게 끝까지 맞히는 것이 중요합니다.'
expect(s, 'watch', '집중 중단이 불가능한 기술입니다. 중단기를 믿기보다 광선에서 벗어나거나 피해 면역 시간을 맞추세요.')
s['watch'] = '집중 중단이 불가능한 기술입니다. 중단기를 믿기보다 광선에서 벗어나거나 피해 면역 시간을 맞추세요. 피해가 뒤로 갈수록 커지므로 일찍 빠져나올수록 받는 피해가 크게 줄어듭니다.'
dd['lines'] = ['최대 ⟦0⟧ 동안 채널링하여 모든 적을 관통하는 ⟦1⟧ 길이의 아발론 에너지 광선을 방출합니다 (방해 불가).',
               '⟦2⟧마다 ⟦3⟧의 마법 피해 (플레이어 대상) / ⟦4⟧의 마법 피해 (몬스터 대상)를 입힙니다.',
               '플레이어에 대한 피해는 ⟦2⟧마다 ⟦19⟧씩 증가합니다.',
               '광선은 커서 위치를 천천히 따라갑니다.']
setv(s, 3, 106, 74)
setv(s, 11, 106, 74)
dd['values'] += [V(8, '', 'health'), V(138, '', 'health', True)]
dd['periodic'] = [row('플레이어 대상 피해의 반복 구조', '첫 회 ⟦11⟧ → 마지막 회 ⟦20⟧(회마다 ⟦19⟧ 증가) · ⟦12⟧ 간격 · 9회 · 효과 부여 후 첫 발동 ⟦13⟧ · 전부 적용 시 ⟦14⟧'),
                  row('몬스터 대상 피해의 반복 구조', '회당 ⟦15⟧ · ⟦16⟧ 간격 · 9회 · 효과 부여 후 첫 발동 ⟦17⟧ · 전부 적용 시 ⟦18⟧')]
dd['notes'] = dd['notes'] + ['플레이어 대상 피해 증가는 광선을 유지한 시간을 따릅니다. 광선에 늦게 들어온 대상은 그 시점의 커진 피해부터 받고, 맞는 횟수는 줄어듭니다.']
patch(s, '플레이어에게 주는 피해가 매번 106이던 것에서, 첫 회 74로 시작해 0.3초마다 8씩 늘어 마지막 회 138이 되도록 바뀌었습니다. '
         '9회를 모두 맞히면 합계 954로 같지만, 짧게 스친 대상은 덜 아프고 끝까지 맞을수록 커집니다. 몬스터 대상 피해(회당 70)는 그대로입니다.')

# ====================================================================== Crossbows: Sweeping Bolt (Heavy Crossbow)
s = SP['CROSSBOW_ARMORPIERCER']
patch(s, '화살 판정이 남아 있는 시간이 0.7초에서 0.3초로 줄었습니다. 화살이 지나간 뒤 범위에 들어온 적이 보이지 않는 판정에 맞는 일이 줄어듭니다. '
         '피해(225)와 사거리(24m)는 그대로입니다.')

# ====================================================================== Daggers: Slit Throat (Dagger Pair)
s = SP['EXECUTEDAGGER']
counters(s, ['EMERGENCY_SHIELD', 'BLOCK'])
assert [v['base'] for v in s['details']['values'][3:7]] == [92, 145, 218, 309]
assert [v['base'] for v in s['details']['values'][11:15]] == [15, 0.4, 11, 3]
s['one'] = '중첩을 소모해 큰 타격을 주고 두 번째 슬롯 스킬을 초기화'
s['tags'] = ['공격']
s['effect'] = ['대상 적에게 파괴적인 타격을 입히며, 자신에게 부여된 암살자의 영혼 중첩 또는 적에게 부여된 갑옷 찢기 중첩 수에 따라 물리 피해를 입힙니다 (방해 불가).',
               '무기의 두 번째 슬롯 스킬의 재사용 대기 시간을 초기화합니다.',
               '자신에게 부여된 암살자의 영혼 중첩과 대상에게 부여된 갑옷 찢기 중첩을 모두 소모합니다.']
expect(s, 'when', '필요한 중첩을 모으고 상대의 피해 면역이 끝난 직후 큰 공격을 넣으세요.')
s['when'] = ('필요한 중첩을 모으고 상대의 피해 면역이 끝난 직후 큰 공격을 넣으세요. 두 번째 슬롯 스킬이 바로 초기화되므로 돌진기로 빠지거나 '
             '피해 스킬로 마무리할 수 있습니다.')
s['watch'] = '중단 불가능과 피해 면역 관통은 다릅니다. 패치 5부터 출혈과 받는 회복량 감소는 붙지 않습니다.'
s['details'] = {
    'lines': ['대상 적에게 파괴적인 타격을 입히며, 자신에게 부여된 암살자의 영혼 중첩 또는 적에게 부여된 갑옷 찢기 중첩 수에 따라 물리 피해를 입힙니다 (방해 불가).',
              '중첩: 0 | 1 | 2 | 3',
              '타격 피해: ⟦0⟧ | ⟦1⟧ | ⟦2⟧ | ⟦3⟧',
              '무기의 두 번째 슬롯 스킬의 재사용 대기 시간을 초기화합니다.',
              '자신에게 부여된 암살자의 영혼 중첩과 대상에게 부여된 갑옷 찢기 중첩을 모두 소모합니다.'],
    'values': [V(92, '', 'health'), V(145, '', 'health'), V(218, '', 'health'), V(309, '', 'health'),
               V(15, '초'), V(0.4, '초'), V(11), V(3, 'm')],
    'stages': [{'label': '기본 사용', 'rows': [row('기본 쿨타임', '⟦4⟧'), row('시전 시간', '⟦5⟧'), row('에너지 소모', '⟦6⟧'), row('시전 거리', '⟦7⟧')]}],
    'periodic': [], 'notes': [], 'unresolved': []}
s['counters'] = s['counters'][1:]      # no bleed left to remove
patch(s, '출혈 피해와 받는 회복량 감소(20%·4초)가 없어졌습니다. 대신 쓰는 즉시 무기 두 번째 슬롯 스킬의 재사용 대기 시간이 초기화되어, '
         '돌진기로 빠지거나 피해 스킬로 마무리할 수 있습니다. 중첩별 타격 피해(92·145·218·309)는 그대로입니다.')

# ====================================================================== Fire: Flaming Phoenix (Dawnsong)
s = SP['FIREPHOENIX']
expect(s, 'range', '15m')
s['range'] = '12m'
setv(s, 9, 15, 12)
patch(s, '시전 거리가 15m에서 12m로 줄었습니다. 피해, 화염 지대, 받는 회복량 감소는 그대로입니다.')

# ====================================================================== Frost: Frost Beam (all frost staffs)
s = SP['FROSTBEAM']
setv(s, 2, 4, 5)
old = '대상 적에게 얼어붙는 광선을 발사해 최대 2.7초 동안 집중을 유지하며, 0.3초마다 대상 적 주변 4m 범위 내의 모든 적에게 일정량의 마법 피해를 입힙니다.'
assert s['effect'][0] == old
s['effect'][0] = old.replace('주변 4m 범위', '주변 5m 범위')
patch(s, '피해가 들어가는 범위가 대상 주변 4m에서 5m로 넓어져, 원래 5m였던 둔화 범위와 같아졌습니다. 피해량과 둔화 수치는 그대로입니다.')

# ====================================================================== Frost: Glacial Obelisk (all frost staffs)
s = SP['ICE_SCULPTURE']
counters(s, ['PURGE_HELMET', 'PURIFYING_SMOKE', 'SELF_CLEANSE', 'AVALON_BEAM', 'BLOCK'])
assert [v['base'] for v in s['details']['values']] == [6, 20, 10, 6, 77, 40, 4, 16, 0.4, 8, 12, 16, 0, 0, 0, 5.9]
s['one'] = '아군을 강화하는 오벨리스크를 세우고, 다시 시전해 터뜨리면 아군 보호막과 적 둔화'
s['tags'] = ['방해', '지원', '생존']
s['effect'] = ['목표 위치에 6초 동안 지속되는 빙하 오벨리스크를 생성합니다.',
               '오벨리스크로부터 반경 6m 내에 있는 아군 최대 10명의 가하는 모든 피해와 재사용 대기 시간 감소 속도가 20%만큼 증가합니다.',
               '스킬을 다시 시전하면 오벨리스크를 미리 폭발시켜, 반경 6m 안의 아군에게 3초 동안 일정량의 피해(저항력 계산 전)를 흡수하는 보호막을 부여합니다.',
               '폭발에 맞은 모든 적을 4초 동안 40%만큼 둔화시킵니다.',
               '오벨리스크는 6초 후에 자동으로 폭발합니다. 자동 폭발은 적을 둔화시키기만 하고 보호막은 주지 않습니다.']
s['when'] = ('아군이 모여 싸우는 자리에 세워 6m 안 아군 최대 10명의 피해와 재사용 대기 시간 감소 속도를 20% 높이세요. '
             '큰 피해가 들어오기 직전에 다시 시전해 터뜨리면 6m 안의 아군이 3초 보호막을 얻고, 다가온 적은 4초 동안 40% 느려집니다.')
s['watch'] = ('오벨리스크는 설치한 자리에 고정되며, 반경 6m 밖으로 나가면 강화를 받지 못합니다. 다시 시전해 터뜨리면 강화도 바로 끝나고, '
              '패치 5부터 폭발은 피해를 주지 않습니다.')
s['details']['lines'] = [
    '목표 위치에 ⟦0⟧ 동안 지속되는 빙하 오벨리스크를 생성합니다.',
    '오벨리스크로부터 반경 ⟦3⟧ 내에 있는 아군 최대 ⟦2⟧명의 가하는 모든 피해와 재사용 대기 시간 감소 속도가 ⟦1⟧만큼 증가합니다.',
    '스킬을 다시 시전하면 오벨리스크를 미리 폭발시켜, 반경 ⟦3⟧ 안의 아군에게 ⟦5⟧ 동안 최대 ⟦4⟧의 피해(저항력 계산 전)를 흡수하는 보호막을 부여합니다.',
    '폭발에 맞은 모든 적을 ⟦7⟧ 동안 ⟦6⟧만큼 둔화시킵니다.',
    '오벨리스크는 ⟦0⟧ 후에 자동으로 폭발합니다. 자동 폭발은 적을 둔화시키기만 하고 보호막은 주지 않습니다.']
s['details']['values'] = [V(6, '초'), V(20, '%'), V(10), V(6, 'm'), V(200, '', 'health'), V(3, '초'), V(40, '%'), V(4, '초', 'ccBase'),
                          V(16, '초'), V(0.4, '초'), V(8), V(12, 'm'), V(16, '초'), V(0, '초'), V(0), V(0, 'm'), V(5.9, '초')]
s['details']['stages'] = [
    {'label': '기본 사용', 'rows': [row('기본 쿨타임', '⟦8⟧'), row('시전 시간', '⟦9⟧'), row('에너지 소모', '⟦10⟧'), row('시전 거리', '⟦11⟧')]},
    {'label': '추가 사용 1', 'rows': [row('재사용 가능한 시간', '⟦16⟧'), row('기본 쿨타임', '⟦12⟧'), row('시전 시간', '⟦13⟧'), row('에너지 소모', '⟦14⟧'),
                                    row('시전 거리', '⟦15⟧')]}]
assert s['details']['notes'] == [CC_NOTE] and s['details']['periodic'] == []
s['counters'] = s['counters'][:4]      # the detonation no longer deals damage, so "block the hit" no longer applies
patch(s, '다시 시전해 터뜨릴 때의 마법 피해(77)가 없어지고, 대신 반경 6m 안의 아군에게 3초 동안 200의 피해를 흡수하는 보호막을 줍니다. '
         '4초 40% 둔화는 그대로이며, 6초가 지나 저절로 터질 때는 둔화만 주고 피해도 보호막도 없습니다.')

# ====================================================================== Holy: Holy Flash (all holy staffs)
s = SP['HOLYFLASH']
expect(s, 'range', '13m')
assert s['patchTag'] == '9.23'
s['range'] = '11m'
setv(s, 6, 13, 11)
patch(s, '시전 거리가 13m에서 11m로 줄었습니다. 강한 범위 회복을 쓰려면 위험한 앞쪽까지 다가가야 합니다. 회복량(106)과 쿨타임(3.5초)은 그대로입니다.')

# ====================================================================== Nature: Well of Life (Wild Staff), Rejuvenation (fix)
s = SP['WELLOFLIFE2']
assert [v['base'] for v in s['details']['values']] == [4, 7, 20, 1, 69, 20, 0.7, 18, 15, 69, 1, 0.5, 276]
s['one'] = '만드는 즉시 회복하고, 정해진 지역에 서 있는 아군을 반복 회복'
s['effect'] = ['목표 위치에 4초 동안 지속되는 7m 범위의 생명의 샘을 만듭니다.',
               '만드는 즉시 범위 안의 아군 체력을 일정량 회복시킵니다.',
               '샘 안의 아군 최대 20명의 체력을 1초마다 일정량 회복시킵니다.']
s['when'] = '자신이 머물며 싸울 수 있는 위치에 샘을 놓으세요. 만드는 순간에도 한 번 회복이 들어갑니다.'
s['watch'] = '즉시 회복은 만들 때 한 번뿐이고, 나머지 회복은 샘 안에 머물러야 받습니다. 샘 밖으로 밀려나거나 이동해야 하면 반복 회복을 받기 어렵습니다.'
s['details']['lines'] = ['목표 위치에 ⟦0⟧ 동안 지속되는 ⟦1⟧ 범위의 생명의 샘을 만듭니다.',
                         '만드는 즉시 범위 안의 아군 체력을 ⟦13⟧ 회복시킵니다.',
                         '샘 안의 아군 최대 ⟦2⟧명의 체력을 ⟦3⟧마다 ⟦4⟧ 회복시킵니다.']
s['details']['values'] += [V(69, '', 'health'), V(345, '', 'health', True)]
assert s['details']['periodic'] == [row('체력 회복의 반복 구조', '회당 ⟦9⟧ · ⟦10⟧ 간격 · 4회 · 효과 부여 후 첫 발동 ⟦11⟧ · 전부 적용 시 ⟦12⟧')]
s['details']['periodic'][0]['text'] += ' (만들 때의 즉시 회복을 더하면 ⟦14⟧)'
patch(s, '샘을 만드는 즉시 반경 7m 안의 아군을 69 회복하는 효과가 추가되었습니다. 샘에 끝까지 머문 아군의 회복 합계는 276에서 345로 늘었습니다. '
         '1초마다 69씩 4회 회복하는 반복 회복은 그대로입니다.')

s = SP['REJUVENATION']
patch(s, '시전할 때 이동이 끊기던 문제가 고쳐져, 움직이면서 쓸 수 있습니다. 수치 변화는 없습니다.', FIX_TITLE)

# ====================================================================== Spears: Spectral Trident (Trinity Spear)
s = SP['TRIDENTTHROW']
assert s['patchTag'] == '9.23'
patch(s, '착지 피해와 속박의 판정이 남아 있는 시간이 0.5초에서 0.2초로 줄었습니다. 착지 뒤 범위에 걸어 들어온 적이 보이지 않는 판정에 맞는 일이 줄어듭니다. '
         '피해(220)와 속박(2.65초) 등 수치는 그대로입니다.')

# ====================================================================== War gloves
s = SP['KNUCKLECOMBO']
expect(s, 'cooldown', 15.0)
setv(s, 5, 15, 12)
s['cooldown'], s['cooldownLabel'] = 12.0, '12초'
s['one'] = '속박으로 묶고 두 번째 펀치로 밀쳐내는 근접 2연타'
assert s['effect'][2] == '1.1초 동안 기절시킵니다.' and s['details']['lines'][2] == '⟦2⟧ 동안 기절시킵니다.'
s['effect'][2] = '1.1초 동안 속박시킵니다.'
s['details']['lines'][2] = '⟦2⟧ 동안 속박시킵니다.'
s['when'] = '대상에게 2m 안으로 붙었을 때 써서, 속박이 걸린 동안 두 번째 펀치까지 확실히 맞히세요.'
s['watch'] = ('속박 1.1초와 밀쳐내기 3m는 상대의 군중 제어 저항·점감과 관계없이 고정입니다(게임 데이터 기준). 속박은 기절과 달리 상대가 스킬을 쓸 수 있어 '
              '순간이동이나 방어 스킬로 대응할 수 있습니다. 밀쳐낸 뒤에는 거리가 벌어지니 다음 근접 기술의 거리를 생각하세요.')
patch(s, '첫 번째 펀치의 기절(1.1초)이 같은 시간의 속박으로 바뀌었습니다. 맞은 상대도 순간이동이나 방어 스킬로 대응할 수 있게 된 대신 '
         '쿨타임이 15초에서 12초로 줄었습니다. 피해와 밀쳐내기는 그대로입니다.')

s = SP['TRIPLECOMBO_DIVEKICK']
patch(s, '두 번째 정화의 주먹 판정이 남아 있는 시간이 0.5초에서 0.2초로 줄었습니다. 펀치가 끝난 뒤 범위에 들어온 적이 보이지 않는 판정에 맞는 일이 줄어듭니다. '
         '피해와 버프 제거 효과는 그대로입니다.')

s = SP['GROWING_PUNCH']
assert len(s['details']['values']) == 16 and s['details']['values'][10]['base'] == 1.4000000000000001
assert s['effect'][3] == '끝까지(2초) 집중을 유지하면 맞은 모든 적을 1.4초 동안 공중에 띄웁니다.'
s['effect'][3] = '집중을 일찍 끝내면 맞은 모든 적을 0.7초 동안, 끝까지(2초) 유지하면 1.4초 동안 공중에 띄웁니다.'
assert s['details']['lines'][6] == '끝까지(⟦0⟧) 채널링하면 맞은 모든 적을 ⟦10⟧ 동안 공중에 띄웁니다.'
s['details']['lines'][6] = '채널링을 일찍 끝내면 맞은 모든 적을 ⟦16⟧ 동안, 끝까지(⟦0⟧) 채널링하면 ⟦10⟧ 동안 공중에 띄웁니다.'
s['details']['values'].append(V(0.7, '초', 'fixed', True))
s['when'] = '상대가 쉽게 빠져나갈 수 없는 근접전에서 끝까지 모아 반경 9m 띄우기를 노리고, 상대가 벗어나려 하면 일찍 끝내 피해와 0.7초 띄우기라도 넣으세요.'
s['watch'] = '모으는 동안 이동 속도가 25% 줄어듭니다. 1초 전에 끝내면 반경 5m의 가장 약한 단계가 나가고, 1.4초 띄우기는 2초를 끝까지 채웠을 때만 붙습니다.'
patch(s, '이제 끝까지 모으지 않고 일찍 끝내도 맞은 적을 0.7초 동안 공중에 띄웁니다(이전에는 피해만). 끝까지(2초) 모으면 1.4초 띄우기는 그대로이고, '
         '단계별 피해와 범위도 바뀌지 않았습니다.')

# ====================================================================== Helmets / armors
s = SP['DISRUPTIONIMMUNITY']
assert s['patchTag'] == '9.23'
setv(s, 2, 7, 5)
s['one'] = '밀치기·끌어당기기와 둔화에 흔들리지 않게 합니다.'
s['effect'][0] = '주변 5m 안의 자신과 아군 최대 10명에게 5초 동안 강제 이동과 둔화에 대한 면역을 부여합니다.'
s['when'] = '상대의 밀치기·끌어당기기나 둔화를 뚫고 붙거나, 밀려나면 곤란한 위치를 지켜야 할 때 미리 켜세요.'
s['watch'] = '피해 면역도, 모든 군중 제어 면역도 아닙니다. 막는 것은 강제 이동과 둔화뿐이며, 기절·속박·침묵은 그대로 걸립니다.'
assert s['details']['lines'] == ['⟦0⟧ 범위 내 최대 ⟦1⟧명의 아군을 밀리거나 끌려가지 않는 상태로 만들어, ⟦2⟧ 동안 강제 이동 효과에 면역을 부여합니다.']
s['details']['lines'] = ['⟦0⟧ 범위 내 최대 ⟦1⟧명의 아군을 밀리거나 끌려가지 않는 상태로 만들어, ⟦2⟧ 동안 강제 이동 효과와 둔화에 대한 면역을 부여합니다.']
patch(s, '면역 지속 시간이 7초에서 5초로 줄고, 대신 둔화에도 면역이 됩니다. 쿨타임 25초는 그대로라 면역이 유지되는 시간 비율이 28%에서 20%로 내려갔습니다.')

s = SP['IMMUNEAREA']
assert s['patchTag'] == '9.23'
s['tags'] = ['생존', '기동']
s['effect'] = ['0.6초 시전 뒤 날아올라 지정한 위치에 착지합니다. 날아가는 동안에는 군중 제어와 피해를 모두 받지 않는 완전 면역이며, 착지점에 반경 5.5m 영역을 6초 동안 만듭니다.',
               '자신이 영역 안에 있으면 바깥의 적은 자신에게 영향을 줄 수 없습니다. 영역 안에서는 재사용 대기 시간 감소 속도가 15% 증가합니다.']
s['watch'] = ('영역 안까지 들어온 적과는 여전히 싸워야 합니다. 완전 면역은 날아가는 짧은 순간(약 0.5초)뿐이니, 착지 구역 안에서 모든 공격에 안전한 무적 장판으로 '
              '해석하지 마세요.')
s['details']['lines'] = ['한 쌍의 용의 날개를 소환해 공중을 날아다니며, 날아가는 동안 군중 제어 효과와 피해에 면역이 됩니다.',
                         '착지 지점에 반경 ⟦0⟧의 영역을 ⟦1⟧ 동안 생성합니다.',
                         '영역 안에 있는 동안 영역 밖의 적은 자신에게 영향을 줄 수 없으며, 재사용 대기 시간 감소 속도가 ⟦2⟧만큼 증가합니다.']
assert s['details']['notes'] == []
s['details']['notes'] = ['게임 툴팁에는 아직 ‘군중 제어 효과에 면역’만 적혀 있지만, 패치 5 공지와 게임 데이터(날아가는 0.48초 동안 무적 추가)에 따라 완전 면역으로 적었습니다.']
patch(s, '영역 안에서 얻던 피해 15% 증가가 없어지고, 재사용 대기 시간 감소 속도 15% 증가만 남았습니다. '
         '대신 날아가는 동안(약 0.5초)에는 군중 제어뿐 아니라 피해까지 받지 않는 완전 면역이 됩니다.')

# ====================================================================== Displacement Immunity counters elsewhere (now also slow immunity, 5 s)
OLD_COND = '같은 기술의 피해·기절·속박·둔화까지 모두 막지는 않습니다. 면역 버프 자체를 먼저 제거당하면 보호가 사라집니다.'
NEW_COND = '같은 기술의 피해·기절·속박은 막지 않습니다(둔화는 패치 5부터 함께 막습니다). 면역은 5초뿐이고, 면역 버프 자체를 먼저 제거당하면 보호가 사라집니다.'
n_di = 0
for x in SP.values():
    for c in x.get('counters', []):
        if c['skill'] == 'DISRUPTIONIMMUNITY':
            assert c['condition'].startswith(OLD_COND), (x['id'], c['condition'])
            c['condition'] = NEW_COND + c['condition'][len(OLD_COND):]
            n_di += 1
assert n_di == 49, n_di
s = SP['TORNADO']
expect(s, 'watch', '공중에 띄우는 효과와 주변 둔화는 다릅니다. 강제 이동 면역만으로 둔화까지 자동으로 없애지는 않습니다.')
s['watch'] = '공중에 띄우는 효과와 주변 둔화는 다릅니다. 강제 이동 면역만으로는 둔화를 막지 못하며, 기사 헬멧의 이동 면역은 패치 5부터 둔화 면역도 함께 줍니다.'
s = SP['BLACKHOLE']
expect(s, 'watch', '발동까지 지연이 있습니다. 강제 이동 면역은 당김을 막지만 피해와 둔화까지 모두 막는 효과는 아닙니다.')
s['watch'] = '발동까지 지연이 있습니다. 강제 이동 면역은 당김을 막지만 피해는 막지 못합니다. 둔화는 기사 헬멧의 이동 면역처럼 둔화 면역이 함께 있을 때만(패치 5부터) 막힙니다.'

# ====================================================================== items: signature copies, cloth robes
for it in d['items']:
    sig = it.get('signature')
    if sig and sig in SP:
        it['one'], it['tags'] = SP[sig]['one'], list(SP[sig]['tags'])
CLOTH = ['ARMOR_CLOTH_SET1', 'ARMOR_CLOTH_SET2', 'ARMOR_CLOTH_SET3', 'ARMOR_CLOTH_KEEPER', 'ARMOR_CLOTH_HELL', 'ARMOR_CLOTH_MORGANA',
         'ARMOR_CLOTH_AVALON', 'ARMOR_CLOTH_FEY', 'ARMOR_CLOTH_ROYAL']
assert sorted(CLOTH) == sorted(i['id'] for i in d['items'] if i['id'].startswith('ARMOR_CLOTH'))
CLOTH_NOTE = ('모든 천 몸통에 회복력 관통 15%가 새로 붙었습니다. 여러 명에게 집중 공격을 받는 상대가 얻는 피해 감소(회복력)를 일부 뚫어, '
              '착용자가 주는 모든 피해에 적용됩니다. 대규모 전투에서 천 몸통 딜러의 화력을 높이려는 변경이며, 몸통 스킬과 패시브는 그대로입니다.')
for cid in CLOTH:
    it = ITEMS[cid]
    assert 'patch' not in it
    it['patch'], it['patchTag'], it['patchTitle'] = CLOTH_NOTE, TAG, TITLE

# ====================================================================== DPS (Q·W page)
dps = M['dps']
k = [x['k'] for x in dps['skills']].index('KNUCKLECOMBO')
x = dps['skills'][k]
assert (x['cd'], x['cycle'], x['cast']) == (15.0, 16, 0)
x['cd'], x['cycle'] = 12.0, 13
k = [x['k'] for x in dps['skills']].index('ICE_SCULPTURE')
x = dps['skills'].pop(k)
assert x['dmg'] == 77 and x['note'] == '오벨리스크 폭발 피해만'
assert 'ICE_SCULPTURE' not in [y['k'] for y in dps['nodmg']]
dps['nodmg'].append({'k': 'ICE_SCULPTURE', 'ko': x['ko'], 'en': x['en'], 'slot': x['slot'], 'fams': x['fams'],
                     'why': '피해가 없는 스킬(제어·이동·방어·지원)', 'w': 'MAIN_FROSTSTAFF'})
fb = dps['skills'][[x['k'] for x in dps['skills']].index('FROSTBEAM')]
assert fb['dmg'] == 315 and fb['note'] == '2.7초 채널링 10회(31.5)'        # radius change only: single-target damage unchanged

# ====================================================================== patch panel
def entry(spell, item, where, change):
    assert spell is None or spell in SP
    assert item in ITEMS
    return {'spell': spell, 'item': item, 'where': where, 'change': change}


weapons = [
    entry('ARCANE_METEOR', '2H_ARCANE_RINGPAIR_AVALON', '이븐송 · 고유 스킬',
          '구체 피해 112 → 179 · 오라 대상 3명 → 1명 · 오라 지속 피해 31×5회 추가 · 피해·회복 감소 삭제 · 둔화 15% → 25% · 쿨타임 38초(IP 보정) → 25초 · 지속 피해 제거로만 정화'),
    entry('AXE_CHARGE', 'MAIN_AXE', '도끼 8종 공통', '적·아군 받는 회복량 증감 삭제 → 적 근처 착지 시 4초 동안 가한 피해의 15% 회복'),
    entry('AXEWHIRLWIND2', '2H_AXE', '그레이트액스 · 고유 스킬', '피해 증가 중첩이 같은 적이 아니어도 이어짐 (아무 적이나 맞히면 계속 증가)'),
    entry('HAWK_SHOT_MULTI1', '2H_BOW_AVALON', '미스트피어서 · 고유 스킬', '피해 178 → 169'),
    entry('CROSSBOW_DIVINE_SHOT', '2H_CROSSBOW_CANNON_AVALON', '에너지 셰이퍼 · 고유 스킬', '플레이어 대상 회당 106 → 74부터 8씩 증가해 138 (합계 954 그대로)'),
    entry('CROSSBOW_ARMORPIERCER', '2H_CROSSBOWLARGE', '헤비 크로스보우 · 고유 스킬', '판정 유지 시간 0.7초 → 0.3초'),
    entry('EXECUTEDAGGER', '2H_DAGGERPAIR', '대거 페어 · 고유 스킬', '출혈·받는 회복량 감소 삭제 → 두 번째 슬롯 스킬 재사용 대기 시간 초기화'),
    entry('FIREPHOENIX', '2H_FIRE_RINGPAIR_AVALON', '던송 · 고유 스킬', '시전 거리 15m → 12m'),
    entry('FROSTBEAM', 'MAIN_FROSTSTAFF', '서리 지팡이 8종 공통', '피해 반경 4m → 5m'),
    entry('ICE_SCULPTURE', 'MAIN_FROSTSTAFF', '서리 지팡이 8종 공통', '다시 시전 시 폭발 피해(77) 삭제 → 6m 안 아군 보호막 200·3초'),
    entry('HOLYFLASH', 'MAIN_HOLYSTAFF', '신성 지팡이 8종 공통', '시전 거리 13m → 11m'),
    entry('WELLOFLIFE2', '2H_WILDSTAFF', '와일드 스태프 · 고유 스킬', '설치 즉시 회복 69 추가 (합계 276 → 345)'),
    entry('TRIDENTTHROW', '2H_TRIDENT_UNDEAD', '트리니티 스피어 · 고유 스킬', '착지 피해·속박 판정 유지 0.5초 → 0.2초'),
    entry('KNUCKLECOMBO', '2H_KNUCKLES_SET1', '전투 장갑 8종 공통', '기절 → 속박 (1.1초) · 쿨타임 15초 → 12초'),
    entry('TRIPLECOMBO_DIVEKICK', '2H_KNUCKLES_AVALON', '아발론의 철권 · 고유 스킬', '정화의 주먹 판정 유지 0.5초 → 0.2초'),
    entry('GROWING_PUNCH', '2H_KNUCKLES_MORGANA', '까마귀 장갑 · 고유 스킬', '일찍 끝내도 0.7초 띄우기 (끝까지 모으면 1.4초 그대로)'),
    entry('REJUVENATION', 'MAIN_NATURESTAFF', '자연 지팡이 8종 공통', '시전할 때 이동이 끊기던 문제 수정 (오류 수정)'),
]
armors = [
    entry('DISRUPTIONIMMUNITY', 'HEAD_PLATE_SET2', '기사 헬멧 · 고유 스킬', '지속 7초 → 5초 · 둔화 면역 추가'),
    entry('IMMUNEAREA', 'ARMOR_LEATHER_DRAGON', '드래곤슬레이어 재킷 · 고유 스킬', '영역 안 피해 15% 증가 삭제 · 날아가는 동안 군중 제어 면역 → 완전 면역'),
]
robes = [entry(None, cid, f'{ITEMS[cid]["ko"]} · 능력치', '회복력 관통 0% → 15%') for cid in CLOTH]
P5 = {'name': '드래곤파이어 패치 5', 'date': '2026.11.26', 'tag': TAG, 'changelog': CHANGELOG,
      'groups': [{'label': f'무기 스킬 {len(weapons)}개 (밸런스 {len(weapons) - 1} · 오류 수정 1)', 'entries': weapons},
                 {'label': f'방어구 스킬 {len(armors)}개', 'entries': armors},
                 {'label': f'천 몸통 {len(robes)}종', 'entries': robes}]}
assert M['patches'][0]['tag'] == '11.02' and M['patch'] == M['patches'][0]
M['patches'].insert(0, P5)
M['patch'] = P5

# ====================================================================== consistency
changed = sorted(k for k in SP if SP[k] != BEFORE['spells'][k])
EXPECT = sorted(['ARCANE_METEOR', 'AXE_CHARGE', 'AXEWHIRLWIND2', 'HAWK_SHOT_MULTI1', 'CROSSBOW_DIVINE_SHOT', 'CROSSBOW_ARMORPIERCER', 'EXECUTEDAGGER',
                 'FIREPHOENIX', 'FROSTBEAM', 'ICE_SCULPTURE', 'HOLYFLASH', 'WELLOFLIFE2', 'REJUVENATION', 'TRIDENTTHROW', 'KNUCKLECOMBO',
                 'TRIPLECOMBO_DIVEKICK', 'GROWING_PUNCH', 'DISRUPTIONIMMUNITY', 'IMMUNEAREA', 'TORNADO', 'BLACKHOLE']
                + [x['id'] for x in SP.values() if any(c['skill'] == 'DISRUPTIONIMMUNITY' for c in x.get('counters', []))])
assert changed == sorted(set(EXPECT)), sorted(set(changed) ^ set(EXPECT))
patched = sorted(k for k, x in SP.items() if x.get('patchTag') == TAG)
assert len(patched) == 19 and set(patched) == {e['spell'] for g in P5['groups'] for e in g['entries'] if e['spell']}
for x in SP.values():                                   # every placeholder resolves, every value is used
    dd = x['details']
    texts = dd['lines'] + [r['text'] for st in dd['stages'] for r in st['rows']] + [r['text'] for r in dd['periodic']]
    import re
    used = {int(n) for t in texts for n in re.findall(r'⟦(\d+)⟧', t)}
    assert all(n < len(dd['values']) for n in used), x['id']
    if x['id'] in patched:
        assert used == set(range(len(dd['values']))), (x['id'], sorted(set(range(len(dd['values']))) - used))
for it in d['items']:
    if it.get('signature') in SP:
        assert it['one'] == SP[it['signature']]['one'] and it['tags'] == SP[it['signature']]['tags']
json.dump(d, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('spells changed', len(changed), '| patch-tagged', len(patched), '| items with item-level note', sum(1 for i in d['items'] if i.get('patchTag') == TAG),
      '| panel entries', sum(len(g['entries']) for g in P5['groups']), '| DI counters', n_di,
      '| dps skills', len(dps['skills']), 'nodmg', len(dps['nodmg']))
print('items whose one/tags changed:', sorted(i['id'] for i, j in zip(d['items'], BEFORE['items']) if (i['one'], i['tags']) != (j['one'], j['tags'])))
