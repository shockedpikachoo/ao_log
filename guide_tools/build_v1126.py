"""Build the 2026-11-26 guide (Dragonfire Patch 5) from the 2026-11-19 page.

  * skill and item texts/numbers: Patch 5 data made by apply_patch5.py (checked by verify_patch5.py);
  * ranking sample: 11/19-11/25 KST, the last 7 days before Patch 5 (labelled "패치 5 이전" on screen);
  * prices: the 14 UTC days before the patch day (11/12-11/25), orders seen in the 24 h before the patch;
  * rank history v8, update notes (the 11/19 notes become history), Patch 5 panel, sources/footer texts.

Usage: python3 -I build_v1126.py <11/19 page> <guideData_p5.json> <agg.json> <market.json> <checked UTC> <qa.json or -> <out.html>
"""
import collections, datetime as dt, json, re, sys

SRC, PATCHED, AGG, MARKET, CHECKED, QA, OUT = sys.argv[1:8]
html = open(SRC, encoding='utf-8').read()
TAG = '<script id="guideData" type="application/json">'
a = html.index(TAG) + len(TAG)
b = html.index('</script>', a)
H, d0, J = html[:a], json.loads(html[a:b]), html[b:]
d = json.load(open(PATCHED, encoding='utf-8'))
g = json.load(open(AGG, encoding='utf-8'))
mk = json.load(open(MARKET, encoding='utf-8'))
MM, MS = mk['meta'], mk['stats']
qa = None if QA == '-' else json.load(open(QA, encoding='utf-8'))
m, m0 = d['meta'], d0['meta']
assert m0['versionDate'] == '2026.11.19' and len(m0['rankHistory']) == 7, 'template must be the 11/19 page'
assert d['images'] == d0['images'] and [i['id'] for i in d['items']] == [i['id'] for i in d0['items']] and list(d['spells']) == list(d0['spells'])
assert m['patches'][0]['tag'] == '11.26' and m['patch'] == m['patches'][0], 'patched data expected'
for k in m0:                                                   # the patched data only differs in dps and the patch panel
    if k not in ('dps', 'patch', 'patches'):
        assert m[k] == m0[k], k


def sub(text, old, new, n=1, where=''):
    c = text.count(old)
    assert c == n, (where, c, n, old[:160])
    return text.replace(old, new)


f = lambda n: f'{n:,}'
KST = dt.timedelta(hours=9)
p_utc = lambda s: dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')

# ------------------------------------------------------------------ constants of this version
VERSION_DATE, REVIEW_KO, REVIEW_DAY = '2026.11.26', '2026년 11월 26일', '11월 26일'
PREV = {'label': '11/13–11/18', 'days': 6, 'events': 72806}
QW_CHECK = {'at': '2026-11-26 23:00 KST', 'events': 270, 'equipment': 4429, 'withActiveSpells': 0, 'withPassiveSpells': 0}
P5_URL = 'https://steamcommunity.com/games/761890/announcements/detail/1850460852984814'
P4_URL = 'https://steamcommunity.com/games/761890/announcements/detail/1847920302247585'
P5, P4 = 'd277a5cf8a76535f1dccadbf35b36350ae2665aa', '0483dd97f1581dfaf02eed42f25f5ea2a3cb75e5'
SAMPLE_NOTE = '패치 5 이전'
PATCH_DOWN = {'lastBeforeKst': '2026-11-26 19:00:23', 'firstAfterKst': '2026-11-26 19:34:08'}   # gap in the kill feed
# polls whose read-back did not reach the full 3-minute overlap; the ranges they read still overlapped the previous poll
OVERLAP_SHORT = [
    {'atKst': '11/22 00:04:20', 'oldestRead': '11/21 23:51:30', 'overlapFrom': '11/21 23:51:25', 'previousNewest': '11/21 23:54:25'},
    {'atKst': '11/25 23:58:58', 'oldestRead': '11/25 23:46:11', 'overlapFrom': '11/25 23:45:57', 'previousNewest': '11/25 23:48:57'},
]
assert all(x['overlapFrom'] < x['oldestRead'] <= x['previousNewest'] for x in OVERLAP_SHORT)

# ------------------------------------------------------------------ sample figures
assert g['windowKst'] == ['2026-11-19T00:00', '2026-11-26T00:00']
w0 = dt.datetime.strptime(g['windowKst'][0], '%Y-%m-%dT%H:%M')
w1 = dt.datetime.strptime(g['windowKst'][1], '%Y-%m-%dT%H:%M')
d1 = w1 - dt.timedelta(days=1)
assert w0.month == d1.month == w1.month
NDAYS = (w1 - w0).days
KO = f'{w0.month}월 {w0.day}–{d1.day}일'                        # 11월 19–25일
SLASH = f'{w0.month}/{w0.day}–{d1.day}'                          # 11/19–25
SLASH_FULL = f'{w0.month}/{w0.day}–{d1.month}/{d1.day}'          # 11/19–11/25
DOT = f'{w0:%Y.%m.%d}–{d1:%d}'                                   # 2026.11.19–25
PERIOD = f'{w0:%Y.%m.%d}–{d1:%m.%d}'                             # 2026.11.19–11.25
COLLECT_DOT = f'{w0:%Y.%m.%d}–{w1:%d}'                           # 2026.11.19–26
E, OBS = g['events'], g['observations']
EV, OB = f(E), f(OBS)
assert NDAYS == 7 and OBS == 2 * E and len(g['daily']) == NDAYS and sum(g['daily'].values()) == E
first, last = p_utc(g['firstEvent']) + KST, p_utc(g['lastEvent']) + KST
assert w0 <= first < w0 + dt.timedelta(minutes=5) and w1 - dt.timedelta(minutes=5) < last < w1
EXC = g['excluded']
EXC_SUM = sum(EXC.values())
assert g['uniqueInWindow'] - EXC_SUM == E
h = g['health']
assert h['failedPolls'] == 0 and h['fetchWarnings'] == 2
maint, lulls, other = {}, [], []
pk = lambda s: dt.datetime.strptime('2026/' + s, '%Y/%m/%d %H:%M:%S')
for q in h['quietStretches']:
    day, t = q['fromKst'].split()
    if '07:50:00' <= t <= '08:01:00':
        assert day not in maint, q
        maint[day] = (pk(q['toKst']) - pk(q['fromKst'])).total_seconds() / 60
    elif '08:01:00' < t <= '08:40:00':
        assert day in maint, q
        lulls.append(q)
    else:
        other.append(q)
assert not other, other                                     # no outage in this window
assert sorted(maint) == list(g['daily']), 'one maintenance window per day'
MAINT_LO, MAINT_HI = round(min(maint.values())), round(max(maint.values()))
CHK = p_utc(CHECKED) + KST
VERSION_ID = f'{CHK:%Y%m%d-%H%M%S}'
assert VERSION_ID.startswith('20261126-') and CHK > dt.datetime(2026, 11, 26, 19, 34)

# ------------------------------------------------------------------ market figures
since, until = dt.date.fromisoformat(MM['since']), dt.date.fromisoformat(MM['until'])
fresh = dt.date.fromisoformat(MM['fresh'])
MDAYS = MM['days']
assert (until - since).days + 1 == MDAYS == 14 and since == dt.date(2026, 11, 12) and until == dt.date(2026, 11, 25)
assert MM['ordersBefore'] == '2026-11-26T10:00:00'                                    # 19:00 KST, the patch downtime
M_SLASH = f'{since.month}/{since.day}–{until.month}/{until.day}'                        # 11/12–11/25
M_KO = f'{since.month}월 {since.day}–{until.day}일'                                      # 11월 12–25일
M_DOT = f'{since:%Y.%m.%d}–{until:%m.%d}'                                               # 2026.11.12–11.25
t_fetch = p_utc(MM['histFetched'][0]) + KST
FETCH_HM = f'{t_fetch:%H:%M}'
assert t_fetch.date() == dt.date(2026, 11, 26)
CNT = MM['counts']
PRICED = CNT['city'] + CNT['bmOnly']
assert PRICED == MS['priced'] and CNT['exists'] == 2243 and CNT['noTier'] == 493 and MS['refIds'] == 10
BM_RATIO = f"{MS['bmOverCityMedian']:.1f}"
assert MS['bmAboveCityPairs'] / MS['bmOverCityPairs'] > 0.85                           # "대체로 도시보다 높게"


def prem(q):
    x = (MS['qualityPremiumMedian'][str(q)] - 1) * 100
    return f'+{x:.1f}%' if abs(x) < 1 else f'+{x:.0f}%'


DROP_SHARE = f"{MS['droppedCityUnitShare'] * 100:.2f}%"
ubd = MS['cityUnitsByDay']
assert sum(ubd.values()) == MS['cityUnits'] and min(ubd) == MM['since'] and max(ubd) == MM['until'] and len(ubd) == MDAYS
EARLY_TO, LATE_FROM = since + dt.timedelta(days=6), until - dt.timedelta(days=2)       # first seven days / last three days
EARLY = sum(v for k, v in ubd.items() if k <= EARLY_TO.isoformat()) / MS['cityUnits']
LATE = sum(v for k, v in ubd.items() if k >= LATE_FROM.isoformat()) / MS['cityUnits']
assert 0.5 < EARLY < 0.6 and 0.1 < LATE < 0.2, (EARLY, LATE)                          # "비교적 고르게, 앞쪽이 조금 더"
WEAK_BEFORE = fresh - dt.timedelta(days=1)
COLLECTED = MM['collectedLabel']                                                        # 2026.11.26 22:30–22:53(한국 시간)

# ------------------------------------------------------------------ items
EXTRA = {'offhand', 'cape', 'bag', 'potion', 'food', 'mount'}
moves = []
prev_hist = {k: v for k, v in m['rankHistory'][-1]['ranks'].items()}
for it in d['items']:
    s = g['items'][it['id']]
    for k in ('count', 'winner', 'victim', 'share', 'rank'):
        it[k] = s[k]
    if it['kind'] in EXTRA:
        assert set(it['pvp']) == {'count', 'winner', 'victim', 'rank', 'share'}
        it['pvp'] = {'count': s['count'], 'winner': s['winner'], 'victim': s['victim'], 'rank': s['rank'], 'share': s['share']}
        assert it.get('co') is None
    else:
        it['co'] = {slot: v for slot, v in g['co'].get(it['id'], {}).items() if slot != 'bag'}
    it['market'] = mk['items'][it['id']]
    pr = prev_hist.get(it['id'])
    if pr and s['rank']:
        moves.append((it['id'], it['ko'], it['kind'], it.get('slot'), pr, s['rank'], s['count']))

# ------------------------------------------------------------------ meta
m['events'], m['denominator'], m['period'] = E, OBS, PERIOD
m['daily'] = list(g['daily'].values())
m['dailyLabels'] = list(g['daily'])
m['missing'] = {s: g['armor'][s]['missing'] for s in ('HEAD', 'ARMOR', 'SHOES')}
m['gathering'] = {s: g['armor'][s]['gathering'] for s in ('HEAD', 'ARMOR', 'SHOES')}
m['weapons'].update(events=E, denominator=OBS, missing=g['weapons']['missing'], outside=g['weapons']['outside'], count=g['weapons']['mapped'])
m['periodKstLabel'] = f'{first:%Y.%m.%d %H:%M:%S}–{last:%Y.%m.%d %H:%M:%S} (한국 시간)'
m['shortPeriod'], m['timeLabel'] = SLASH, SLASH_FULL
m['sampleCheckedAt'] = CHECKED
m['sampleNote'] = SAMPLE_NOTE
m['versionId'], m['versionDate'] = VERSION_ID, VERSION_DATE
assert (m['dumpDate'], m['commit'], m['previousCommit']) == ('2026.11.02', P4, '1a469e53de028c5f85cdd80505f10cbd0a2515cf')
m['dumpDate'], m['commit'], m['previousCommit'] = '2026.11.26', P5, P4
m['checkedDate'] = m['numericUpdate'] = m['numericCheckedDate'] = VERSION_DATE
mv = m['movement']
assert mv['dataDate'] == '2026.11.02' and mv['source'].endswith(P4)
mv['dataDate'], mv['source'] = '2026.11.26', mv['source'].replace(P4, P5)     # characters.xml unchanged, no shoe spell/item changed in Patch 5
POLL_SUMMARY = (f"확인 {f(h['polls'])}회는 모두 성공했고, 일시적인 서버 오류 {h['fetchWarnings']}회는 다시 받아 채웠습니다. "
                '11월 22일 0시 4분과 11월 25일 23시 58분에는 기록이 몰려 겹쳐 읽는 여유분(3분)을 각각 5초·14초 덜 읽었지만, '
                '읽은 구간 자체는 직전 확인과 겹쳐 끊기지 않았습니다.')
pv = m['pvpExtras']
prev_pv = {'source': pv['source'], 'method': pv['method'], 'eventsCount': pv['eventsCount'], 'observations': pv['observations'],
           'periodFrom': pv['periodFrom'], 'periodTo': pv['periodTo'], 'windowKst': pv['windowKst']}
assert prev_pv['eventsCount'] == PREV['events']
pv.update(checkedAt=CHECKED, periodFrom=g['firstEvent'], periodTo=g['lastEvent'], windowKst=g['windowKst'], uniqueEvents=g['uniqueInWindow'],
          excluded=EXC, eventsCount=E, observations=OBS, polls=h['polls'], failedPolls=h['failedPolls'], fetchWarnings=h['fetchWarnings'],
          runs=h['runs'], pollSummary=POLL_SUMMARY, outages=[], quietStretches=h['quietStretches'], collectionGaps=[],
          kinds=g['extras'], previous=prev_pv)
pv['overlapShortfalls'] = OVERLAP_SHORT
for k, xk in m['extraKinds'].items():
    xk['hint'] = sub(xk['hint'], '11월 13–18일', f'{KO}({SAMPLE_NOTE})', 1, k)
    e = g['extras'][k]
    new_note = re.sub(r'11/13–18 단독 처치 표본 · 장착 [\d,]+회 · 도감 밖 [\d,]+회',
                      f"{SLASH} 단독 처치 표본({SAMPLE_NOTE}) · 장착 {f(e['equipped'])}회 · 도감 밖 {f(e['outsideCount'])}회", xk['note'])
    assert new_note != xk['note'], k
    xk['note'] = new_note
    if 'notice' in xk and '11월 2일 게임 데이터(드래곤파이어 패치 4)' in xk['notice']:
        xk['notice'] = sub(xk['notice'], '11월 2일 게임 데이터(드래곤파이어 패치 4)', '11월 26일 게임 데이터(드래곤파이어 패치 5)', 1, k)
assert sum('11월 26일 게임 데이터(드래곤파이어 패치 5)' in xk.get('notice', '') for xk in m['extraKinds'].values()) == 3
m['coUsage']['window'] = g['windowKst']
m['coUsage']['anchors'] = len(g['co'])
ranks, counts = {}, {}
for it in d['items']:
    ranks[it['id']], counts[it['id']] = it['rank'], it['count']
sample_label = f'{first:%m/%d %H:%M:%S}–{last:%m/%d %H:%M:%S} KST · {EV}건'
m['rankHistory'].append({'id': VERSION_ID, 'date': VERSION_DATE, 'label': f'{VERSION_DATE} · {SLASH} 공식 API 표본({SAMPLE_NOTE})', 'ranks': ranks, 'counts': counts,
                         'samples': {k: sample_label for k in ranks}, 'source': pv['source'], 'eventsCount': E, 'observations': OBS,
                         'sequence': 8})
old_mk = m['market']
m['market'] = dict(MM)
m['market']['windowNote'] = SAMPLE_NOTE
m['market']['previous'] = {k: old_mk[k] for k in ('since', 'until', 'histFetched', 'ordersFetched', 'counts', 'dropped')}
m['review20261126'] = {
    'date': VERSION_DATE, 'timezone': 'Asia/Seoul', 'sample': f'{SLASH_FULL} KST official API (before Patch 5)', 'windowKst': g['windowKst'],
    'events': E, 'observations': OBS, 'uniqueInWindow': g['uniqueInWindow'], 'excluded': EXC, 'health': h,
    'maintenanceMinutes': {k: round(v, 1) for k, v in sorted(maint.items())}, 'afterMaintenanceLulls': lulls,
    'outages': [], 'collectionGaps': [], 'overlapShortfalls': OVERLAP_SHORT,
    'dataDate': '2026.11.26', 'latestCommit': P5, 'previousCommit': P4,
    'patch5': {'changelog': P5_URL, 'liveKst': '2026-11-26 19:34 (downtime from 19:00)', 'killFeedGap': PATCH_DOWN,
               'skillsChanged': sorted(k for k, s in d['spells'].items() if s.get('patchTag') == '11.26'),
               'itemsChanged': sorted(i['id'] for i in d['items'] if i.get('patchTag') == '11.26'),
               'unchangedButReached': ['MIMIC (mimics Battle Rush / Glacial Obelisk; its own text unchanged)', 'SHAPE_W_TETHERBEAM (VFX only)'],
               'notShown': ['MOUNTSPELL_DRAKE_FIRE_BREATH standtime 3.84 -> 2.88 (not shown in the guide)', 'HELLGATE_DAMAGE_HIT (2v2 Hellgate lava)'],
               'countersEdited': 'Displacement Immunity (49 skills): now 5 s and also slow immunity; removed: Slit Throat DoT removal, Battle Rush cleanse, '
                                 'Glacial Obelisk block; Dark Sphere: cleanse -> Emergency Shield (DoT removal)',
               'dps': 'KNUCKLECOMBO cd 15 -> 12 (cycle 16 -> 13); ICE_SCULPTURE moved to the no-damage list'},
    'patchCheck': 'ao-bin-dumps d277a5c (2026-11-26) vs 0483dd9 (2026-11-02): spells.xml, items.xml, localization.xml changed; '
                  'characters.xml, gamedata.xml, transformations.xml unchanged',
    'qwCheck': QW_CHECK, 'market': {'stats': MS, 'window': [MM['since'], MM['until']], 'ordersBefore': MM['ordersBefore'],
                                    'rule': 'the 14 UTC days before the Patch 5 day; sell orders seen in the 24 h before the patch downtime'},
}
if qa:
    m['review20261126']['qa'] = qa

# ------------------------------------------------------------------ static page text: head, hero, banner, catalog hints
H = sub(H, '<title>알비온 장비 도감 · 342종 · 2026.11.19 업데이트</title>', f'<title>알비온 장비 도감 · 342종 · {VERSION_DATE} 업데이트</title>')
H = sub(H, '<div class="eyebrow">ASIA · 6-DAY OFFICIAL API SAMPLE</div>', f'<div class="eyebrow">ASIA · {NDAYS}-DAY OFFICIAL API SAMPLE</div>')
H = sub(H, '<div><strong>72,806</strong><small>단독 가해자 기록</small></div><div><strong>6일</strong><small>2026.11.13–18</small></div>',
        f'<div><strong>{EV}</strong><small>단독 가해자 기록</small></div><div><strong>{NDAYS}일</strong><small>{DOT}</small></div>')
H = sub(H, '<div class="sample-foot">아시아 서버 · 11월 13–18일 기록 · ', f'<div class="sample-foot">아시아 서버 · {KO} 기록({SAMPLE_NOTE}) · ')
P5_SKILLS = sum(1 for s in d['spells'].values() if s.get('patchTag') == '11.26')
P5_ITEMS = sum(1 for i in d['items'] if i.get('patchTag') == '11.26')
P5_ENTRIES = sum(len(x['entries']) for x in m['patch']['groups'])
assert (P5_SKILLS, P5_ITEMS, P5_ENTRIES) == (19, 9, 28)
H = sub(H, '<span><b>2026.11.19 업데이트</b>장착 순위·비중과 같이 많이 쓰는 장비 TOP 3를 11월 13–18일 새 표본(단독 처치 72,806건)으로 다시 매기고, '
           '시세는 최근 14일(11/6–11/19)의 거래로 새로 받았습니다. 게임 데이터는 바뀌지 않아 설명·수치는 그대로입니다.</span>',
        f'<span><b>{VERSION_DATE} 업데이트 · 드래곤파이어 패치 5 반영</b>11월 26일 패치 5의 장비 변경 {P5_ENTRIES}개(스킬 {P5_SKILLS}개·천 몸통 {P5_ITEMS}종)를 '
        f'설명·수치에 반영했습니다. 장착 순위·비중·TOP 3는 {SAMPLE_NOTE} 기록인 {KO} 표본(단독 처치 {EV}건)이고, 시세도 {SAMPLE_NOTE} {MDAYS}일({M_SLASH})의 거래입니다.</span>')
H = sub(H, '<p id="resultNote">비중은 각 장비 슬롯의 전체 장착 기회 145,612회 기준입니다.</p>',
        f'<p id="resultNote">비중은 {SAMPLE_NOTE} 표본의 각 장비 슬롯 전체 장착 기회 {OB}회 기준입니다.</p>')
H = sub(H, '시세는 아시아 서버의 최근 14일(11/6–11/19) 실제 거래 평균입니다.', f'시세는 아시아 서버의 {SAMPLE_NOTE} {MDAYS}일({M_SLASH}) 실제 거래 평균입니다.')
H = sub(H, '시세는 아시아 서버에서 최근 14일 동안 실제로 거래된 평균 가격(실버)입니다.',
        f'시세는 아시아 서버에서 {MDAYS}일 동안 실제로 거래된 평균 가격(실버)입니다(이번 판은 {SAMPLE_NOTE} {M_KO}).')
H = sub(H, '이번 자료에서는 대체로 도시보다 높게(중앙값 약 1.6배) 사 갔습니다.', f'이번 자료에서는 대체로 도시보다 높게(중앙값 약 {BM_RATIO}배) 사 갔습니다.')
H = sub(H, '원본 2026.11.02(패치 4 이후, 그레이브가드 부츠의 전투 광란 지속 5초 → 6초 반영) / 기능 검토 2026.11.05. '
           f'<a href="https://github.com/ao-data/ao-bin-dumps/tree/{P4}" target="_blank" rel="noopener noreferrer">고정 버전 게임 데이터</a>',
        '원본 2026.11.26(패치 5 적용 후 다시 대조 · 신발 이동에 쓰는 수치는 패치 4와 같음) / 기능 검토 2026.11.05. '
        f'<a href="https://github.com/ao-data/ao-bin-dumps/tree/{P5}" target="_blank" rel="noopener noreferrer">고정 버전 게임 데이터</a>')

# ------------------------------------------------------------------ sources page intro and update notes
H = sub(H, '<p>2026년 11월 19일 기준으로 확인했습니다. 장착 순위는 공식 킬 기록 API로 직접 모은 11/13–11/18 아시아 단독 처치 72,806건을 사용합니다. '
           '수치와 신발 이동거리의 원본은 이날 확인한 최신 공개 추출본인 11월 2일 자료(드래곤파이어 패치 4 적용 후)입니다. 티어별 시세는 11월 19일 17:42쯤(한국 시간)에 따로 수집했습니다.',
        f'<p>{REVIEW_KO} 기준으로 확인했습니다. 장착 순위는 공식 킬 기록 API로 직접 모은 {SLASH_FULL} 아시아 단독 처치 {EV}건({SAMPLE_NOTE})을 사용합니다. '
        f'수치와 신발 이동거리의 원본은 이날 확인한 최신 공개 추출본인 11월 26일 자료(드래곤파이어 패치 5 적용 후)입니다. '
        f'티어별 시세는 {REVIEW_DAY} {FETCH_HM}쯤(한국 시간)에 따로 수집했고 {SAMPLE_NOTE} 거래만 썼습니다.')

SEC = '<section class="reading-panel feature-review" id="featureReview"><h2>2026년 11월 19일 업데이트</h2><ul>\n'
i0 = H.index(SEC)
END19 = ('</ul><p>기준일: 2026.11.19 / 시세: 2026.11.06–11.19 거래(11.19 17:42쯤 수집) / 수치 원본: 2026.11.02 (0483dd9) / '
         '장착 표본: 2026.11.13–18 (공식 API, 한국 시간).</p>\n')
i1 = H.index(END19, i0)
body19 = H[i0 + len(SEC):i1]
assert body19.count('<span id="featureQaText">') == 1 and body19.count('<li>') == 7
history19 = ('<details class="update-history"><summary>이전 기록 · 2026년 11월 19일 업데이트</summary><ul>\n'
             + body19.replace('<span id="featureQaText">', '<span>') + END19 + '</details>\n')
if qa:
    QA_TEXT = (f"실제 브라우저(Chromium)로 8개 분류의 카드·표·시세표와 정렬, 장비 {qa['detailsOpened']}종 상세의 시세·순위 변화·TOP 3 영역과 바로 가기, "
               f"패치 5 변경 스킬·천 몸통 상세, 비교 창, DPS·이동거리·1:1 순위 화면을 열어 스크립트 오류 {qa['scriptErrors']}건을 확인했습니다. "
               f"{qa['widths']}px 화면과 어두운 테마에서 가로 넘침이 없는지도 확인했습니다.")
else:
    QA_TEXT = '(검증 문장은 점검을 마친 뒤 채웁니다.)'
DI = sum(1 for s in d['spells'].values() for c in s.get('counters', []) if c['skill'] == 'DISRUPTIONIMMUNITY')
assert DI == 49
NEW_NOTES = (
    f'<section class="reading-panel feature-review" id="featureReview"><h2>{REVIEW_KO} 업데이트 · 드래곤파이어 패치 5 반영</h2><ul>\n'
    f'<li><b>패치 5 반영</b>: 11월 26일 19시쯤(한국 시간) 적용된 드래곤파이어 패치 5의 장비 변경을 <a href="{P5_URL}" target="_blank" rel="noopener noreferrer">공식 패치 노트</a>와 '
    f'같은 날 공개된 게임 데이터(ao-bin-dumps d277a5c)로 대조해 설명·수치·대응 예시에 반영했습니다. 무기 스킬 17개(오류 수정 1개 포함)·방어구 스킬 2개·'
    f'천 몸통 {P5_ITEMS}종이며, 바뀐 스킬과 장비에는 ‘11.26 변경’ 표시가 붙습니다. 전체 목록은 아래 ‘11월 26일 드래곤파이어 패치 5 반영’에 있습니다.</li>\n'
    '<li><b>크게 바뀐 것</b>: 어둠의 구체(이븐송)는 약화 오라 대신 피해 오라가 되었고(구체 피해 179, 오라는 1명에게, 0.9초마다 31씩 5회), '
    '전투 돌격(도끼 8종)은 받는 회복량 증감 대신 적 근처에 착지하면 4초 동안 가한 피해의 15%만큼 체력을 회복합니다. 목 베기(대거 페어)는 출혈·회복 감소 대신 '
    '두 번째 슬롯 스킬을 초기화하고, 빙하 오벨리스크(서리 지팡이 8종)는 다시 시전할 때 피해 대신 아군에게 보호막 200을 줍니다. 파괴적인 콤보(전투 장갑 8종)는 '
    '기절이 속박으로 바뀌고 쿨타임이 12초가 되었으며, 천 몸통 9종에는 회복력 관통 15%가 붙었습니다.</li>\n'
    '<li><b>대응 예시·피해 비교</b>: 패치로 효과가 없어진 대응 예시를 뺐습니다(목 베기의 지속 피해 제거, 전투 돌격의 정화, 빙하 오벨리스크의 피해 타이밍 방어). '
    '어둠의 오라는 지속 피해 제거로만 지워져 대응을 긴급 보호막으로 바꿨고, '
    f'기사 헬멧의 이동 면역을 대응으로 든 {DI}개 스킬은 문구를 지속 5초·둔화 면역에 맞게 고쳤습니다. '
    'Q·W 피해 비교에서는 빙하 오벨리스크를 피해 없는 스킬로 옮기고 파괴적인 콤보를 쿨타임 12초로 다시 계산했습니다.</li>\n'
    f'<li><b>{SAMPLE_NOTE} 표본</b>: 장착 순위·비중, 기타 장비 6종의 1:1 참고 순위, 같이 많이 쓰는 장비 TOP 3는 {KO}(한국 시간, {NDAYS}일) 아시아 서버의 '
    f'단독 처치 {EV}건(승자·사망자 양측 {OB}회)으로 새로 매겼습니다. 모두 패치 5 적용 전 기록이라 이번 변경의 영향은 아직 들어 있지 않습니다. '
    '패치 당일 11월 26일 0시–19시의 패치 전 기록은 쓰지 않았고, 다음 판부터는 패치 뒤 기록만 씁니다.</li>\n'
    f'<li><b>{SAMPLE_NOTE} 시세</b>: Albion Online Data Project 아시아 서버 공개 API에서 {COLLECTED.replace("(한국 시간)", "")}(한국 시간)에 받았지만, '
    f'{SAMPLE_NOTE} {MDAYS}일({M_KO})의 실제 거래 평균만 썼습니다. 상세의 판매 요청서 최저가도 패치 직전 24시간에 보인 값만 썼습니다. '
    f'게임에 있는 {f(CNT["exists"])}칸 중 {f(PRICED)}칸에 가격이 있고(도시 거래 {f(CNT["city"])}칸, 암시장 거래만 있는 칸 {f(CNT["bmOnly"])}칸), '
    f'수집된 거래가 없는 {f(CNT["none"])}칸은 ‘–’, 게임에 없는 단계 {f(CNT["noTier"])}칸은 빈칸입니다. 계산 기준은 아래 ‘티어별 시세 · 읽는 법과 계산 기준’에 있습니다.</li>\n'
    f'<li><b>빠진 시간</b>: 매일 아침 8시 전후 {MAINT_LO}–{MAINT_HI}분은 서버 점검으로 기록 자체가 없습니다. 그 밖에 수집이 끊긴 구간은 없고 확인 {f(h["polls"])}회는 '
    f'모두 성공했습니다(일시적인 서버 오류 {h["fetchWarnings"]}회는 다시 받아 채움). 11월 22일 0시 4분과 11월 25일 23시 58분에는 기록이 몰려 겹쳐 읽는 여유분(3분)을 '
    '각각 5초·14초 덜 읽었지만, 읽은 구간은 직전 확인과 겹쳐 끊기지 않았습니다.</li>\n'
    f'<li><b>순위 변화</b>: 순위 옆 (▲·▼)와 최근 10개 버전 그래프에 이번 버전(8번째 기록)을 더했습니다. 직전 버전({PREV["label"]}, {PREV["days"]}일, 단독 처치 {f(PREV["events"])}건)과 '
    '수집 방법·집계 기준이 같고 둘 다 패치 4 이후·패치 5 이전 표본입니다. 장착 횟수가 적은 품목은 표본에 따라 순위가 크게 흔들릴 수 있습니다.</li>\n'
    f'<li><b>Q·W 순위</b>: 이번에도 만들 수 없었습니다. 공식 킬 기록의 스킬 칸은 {REVIEW_DAY} 확인 때도 모두 비어 있습니다(최근 기록 {QW_CHECK["events"]}건의 장비 {f(QW_CHECK["equipment"])}개 모두 빈 값).</li>\n'
    f'<li><b>검증</b>: 패치 5로 바뀐 스킬 {P5_SKILLS}개와 천 몸통 {P5_ITEMS}종의 수치는 별도 코드로 게임 데이터(d277a5c)에서 다시 읽어 화면 값과 모두 일치함을 확인했고, '
    '나머지 스킬은 대응 문구 말고는 11월 19일판과 같음을 대조했습니다. 순위·비중과 같이 많이 쓰는 장비 TOP 3는 원본 기록에서 따로 다시 세어 342종 모두 일치했고, '
    f'시세는 아이템 ID {f(MS["idsQueried"])}개 전부를 저장해 둔 API 응답에서 별도 코드로 다시 계산해 차이 0건을 확인했으며, 그 아이템 ID가 모두 지금 게임 데이터(d277a5c)의 아이템 목록에 있는지도 대조했습니다. '
    f'<span id="featureQaText">{QA_TEXT}</span></li>\n'
    f'</ul><p>기준일: {VERSION_DATE} / 시세: {M_DOT} 거래({SAMPLE_NOTE}, {t_fetch:%m.%d} {FETCH_HM}쯤 수집) / 수치 원본: 2026.11.26 (d277a5c) / '
    f'장착 표본: {DOT} ({SAMPLE_NOTE}, 공식 API, 한국 시간).</p>\n'
)
H = H[:i0] + NEW_NOTES + history19 + H[i1 + len(END19):]
H = sub(H, '현재 표본과 이번 변경 사항은 위 11월 19일 업데이트를 기준으로 읽으세요.', f'현재 표본과 이번 변경 사항은 위 {REVIEW_DAY} 업데이트를 기준으로 읽으세요.')

# ------------------------------------------------------------------ market panel
H = sub(H, '<li><b>수집</b>: 2026.11.19 17:42–17:46(한국 시간). 아이템 ID 2,243개(여덟 단계)와 참고 티어 10개를 한 번에 조회했습니다.</li>',
        f'<li><b>수집</b>: {COLLECTED}. 패치 5 적용 뒤에 받았지만 아래 기간의 패치 전 거래만 썼습니다. 아이템 ID {f(CNT["exists"])}개(여덟 단계)와 참고 티어 {MS["refIds"]}개를 한 번에 조회했습니다.</li>')
H = sub(H, '<li><b>기간</b>: 11월 6일–11월 19일, 14일. 최근 14일을 기본으로 하되 그 안에 밸런스 패치가 있으면 패치 날부터 셉니다'
           '(이번 기간에는 패치가 없어 14일을 모두 썼고, 11월 13일판은 패치 4 적용일인 11월 2일부터 11일이었습니다). 날짜는 UTC 일별 묶음이라 한국 시간 오전 9시에 하루가 바뀝니다. '
           '마지막 묶음(19일)은 수집 시점까지입니다.</li>',
        f'<li><b>기간</b>: {since.month}월 {since.day}일–{until.month}월 {until.day}일, {MDAYS}일({SAMPLE_NOTE}). 최근 14일을 기본으로 하되 그 안에 밸런스 패치가 있으면 패치 날부터 셉니다. '
        '이번에는 수집 직전인 11월 26일 19시쯤(한국 시간) 패치 5가 적용되어 패치 뒤 거래가 거의 없으므로, 패치 전날까지의 14일을 썼습니다. '
        f'날짜는 UTC 일별 묶음이라 한국 시간 오전 9시에 하루가 바뀌며, 마지막 묶음({until.day}일)은 한국 시간 11월 26일 오전 9시까지입니다. '
        '패치 5로 바뀐 장비의 시세는 다음 판에서 패치 뒤 거래로 다시 매깁니다.</li>')
H = sub(H, '이번 자료의 도시 거래 개수는 11월 6–12일(앞 7일)이 71%, 11월 17–19일이 3%여서 평균은 기간 앞쪽의 가격을 더 많이 반영합니다. '
           '지금 가격은 상세의 판매 요청서 최저가나 게임 안 시장으로 확인하세요.',
        f'이번에는 기간이 수집 전날에 끝나 날짜별 기록이 비교적 고르게 모였습니다(도시 거래 개수 기준 {since.month}월 {since.day}–{EARLY_TO.day}일(앞 7일) '
        f'{EARLY * 100:.0f}%, {LATE_FROM.month}월 {LATE_FROM.day}–{until.day}일 {LATE * 100:.0f}%). 패치 5 뒤의 가격은 게임 안 시장으로 확인하세요.')
H = sub(H, '두 값이 모두 있는 장비에서 암시장 평균은 도시 평균의 중앙값 약 1.6배였습니다.', f'두 값이 모두 있는 장비에서 암시장 평균은 도시 평균의 중앙값 약 {BM_RATIO}배였습니다.')
H = sub(H, '같은 도시·날짜에서 일반 품질 대비 중앙값이 좋음 +0.3%, 뛰어남 +6%, 우수함 +37%, 걸작 +145%라서 우수함·걸작은 뺐습니다.',
        f'같은 도시·날짜에서 일반 품질 대비 중앙값이 좋음 {prem(2)}, 뛰어남 {prem(3)}, 우수함 {prem(4)}, 걸작 {prem(5)}라서 우수함·걸작은 뺐습니다.')
H = sub(H, '이상 거래로 보고 뺐습니다(도시 612개 · 암시장 9개, 도시 거래 개수 기준 0.14%).',
        f'이상 거래로 보고 뺐습니다(도시 {f(MM["dropped"]["city"])}개 · 암시장 {f(MM["dropped"]["bm"])}개, 도시 거래 개수 기준 {DROP_SHARE}).')
H = sub(H, '빈칸은 게임 데이터(ao-bin-dumps 0483dd9)에 그 티어·단계가 없다는 뜻입니다.', '빈칸은 게임 데이터(ao-bin-dumps d277a5c)에 그 티어·단계가 없다는 뜻입니다.')
H = sub(H, '마지막 거래가 11월 11일 이전(1주 넘게 지남)인 값입니다.', f'마지막 거래가 {WEAK_BEFORE.month}월 {WEAK_BEFORE.day}일 이전(1주 넘게 지남)인 값입니다.')
H = sub(H, '<li><b>판매 요청서 최저가</b>: 상세 화면에만 표시합니다. 수집 시점에 보인 도시 판매 요청서 중 가장 싼 값(일반~뛰어남)이며 이미 팔렸을 수 있습니다.',
        '<li><b>판매 요청서 최저가</b>: 상세 화면에만 표시합니다. 이번에는 패치 5 직전 24시간(11월 25일 19시–26일 19시, 한국 시간) 동안 보인 도시 판매 요청서 중 '
        '가장 싼 값(일반~뛰어남)이며 이미 팔렸을 수 있습니다.')
H = sub(H, '도감 수록 물약·음식의 패치 4 이후 효과 수치로 예외 없음을 다시 확인', '도감 수록 물약·음식의 패치 5 이후 효과 수치로 예외 없음을 다시 확인')
KIND_KO = [('armor', '방어구'), ('weapon', '무기'), ('offhand', '보조 장비'), ('cape', '망토'), ('bag', '가방'), ('potion', '물약'), ('food', '음식'), ('mount', '탈것')]
t0 = H.index('<tbody><tr><td>방어구</td><td>84</td><td>672</td>')
t1 = H.index('</tbody></table><p class="table-note">한 품목은 여덟 칸', t0)
rows = ''
tot = collections.Counter()
for k, ko in KIND_KO:
    s = MS['byKind'][k]
    vals = [s['items'], s['exists'], s.get('city', 0), s.get('bmOnly', 0), s.get('none', 0), s.get('noTier', 0)]
    for key, v in zip(('items', 'exists', 'city', 'bmOnly', 'none', 'noTier'), vals):
        tot[key] += v
    rows += f'<tr><td>{ko}</td>' + ''.join(f'<td>{f(v)}</td>' for v in vals) + '</tr>'
assert [tot[k] for k in ('exists', 'city', 'bmOnly', 'none', 'noTier')] == [CNT['exists'], CNT['city'], CNT['bmOnly'], CNT['none'], CNT['noTier']] and tot['items'] == 342
rows += '<tr><th>합계</th>' + ''.join(f'<th>{f(tot[k])}</th>' for k in ('items', 'exists', 'city', 'bmOnly', 'none', 'noTier')) + '</tr>'
H = H[:t0] + '<tbody>' + rows + H[t1:]
H = sub(H, '거래 기록이 없는 칸 중 395칸은 판매 요청서만 확인돼 상세에 참고로 표시합니다.', f'거래 기록이 없는 칸 중 {f(CNT["noneWithOrder"])}칸은 판매 요청서만 확인돼 상세에 참고로 표시합니다.')

# ------------------------------------------------------------------ patch panel, method grid, sources, footer
H = sub(H, f'<h2>11월 2일 드래곤파이어 패치 4 반영</h2><p><a href="{P4_URL}" target="_blank" rel="noopener noreferrer">공식 패치 노트</a>의 장비 변경 19개를 '
           '10월 12일·11월 2일 게임 데이터로 대조했습니다. 항목을 누르면 해당 설명이 열립니다. 그 전 패치 3(10월 12일, 20개)과 패치 2(9월 23일, 15개)의 변경은 목록 아래에서 펼쳐 볼 수 있습니다.</p>'
           '<div id="patchList"></div><p class="table-note">현재 장착 순위는 11월 13–18일 기록(공식 API로 실시간 수집)입니다.',
        f'<h2>11월 26일 드래곤파이어 패치 5 반영</h2><p><a href="{P5_URL}" target="_blank" rel="noopener noreferrer">공식 패치 노트</a>의 장비 변경 {P5_ENTRIES}개'
        f'(무기 스킬 17개·방어구 스킬 2개·천 몸통 {P5_ITEMS}종)를 11월 2일·11월 26일 게임 데이터로 대조했습니다. 항목을 누르면 해당 설명이 열립니다. '
        '그 전 패치 4(11월 2일, 19개)·패치 3(10월 12일, 20개)·패치 2(9월 23일, 15개)의 변경은 목록 아래에서 펼쳐 볼 수 있습니다.</p>'
        f'<div id="patchList"></div><p class="table-note">현재 장착 순위는 {SAMPLE_NOTE}인 {KO} 기록(공식 API로 실시간 수집)이라 이번 변경의 영향은 아직 들어 있지 않습니다.')
H = sub(H, '<h2>아시아 · 11월 13–18일 · 72,806건</h2>', f'<h2>아시아 · {KO} · {EV}건 · {SAMPLE_NOTE}</h2>')
H = sub(H, '<li>한국 시간 11월 13일 0시부터 18일 24시까지 6일입니다. 모두 11월 2일 패치 4 적용 뒤의 기록입니다. 실제 포함 기록: 2026.11.13 00:00:08–2026.11.18 23:59:57 (한국 시간).</li>',
        f'<li>한국 시간 {w0.month}월 {w0.day}일 0시부터 {d1.day}일 24시까지 {NDAYS}일입니다. 모두 11월 2일 패치 4 적용 뒤, 11월 26일 패치 5 적용 전의 기록입니다. '
        f'실제 포함 기록: {m["periodKstLabel"]}.</li>')
exc0 = m0['pvpExtras']['excluded']
H = sub(H, f"기간 안 고유 기록 {f(m0['pvpExtras']['uniqueEvents'])}건 중 조건 미충족 {f(sum(exc0.values()))}건(가해자 2명 이상 {f(exc0['not_single_participant'])}건, "
           f"그룹 2명 이상 {f(exc0['not_single_group_member'])}건, 명단 불일치 {f(exc0['roster_not_matching_killer'])}건)을 제외했습니다.",
        f'기간 안 고유 기록 {f(g["uniqueInWindow"])}건 중 조건 미충족 {f(EXC_SUM)}건(가해자 2명 이상 {f(EXC["not_single_participant"])}건, '
        f'그룹 2명 이상 {f(EXC["not_single_group_member"])}건, 명단 불일치 {f(EXC["roster_not_matching_killer"])}건)을 제외했습니다.')
H = sub(H, '<li>승자·사망자 양측을 모두 세어 부위당 145,612회입니다.', f'<li>승자·사망자 양측을 모두 세어 부위당 {OB}회입니다.')
H = sub(H, 'aria-label="11월 13–18일 날짜별 단독 가해자 표본 72,806건"', f'aria-label="{KO} 날짜별 단독 가해자 표본 {EV}건"')
arm = g['armor']
wo = sum(g['weapons']['outside'].values())
assert g['weapons']['mapped'] + wo + g['weapons']['missing'] == OBS and all(arm[s]['mapped'] + arm[s]['gathering'] + arm[s]['missing'] == OBS for s in arm)
H = sub(H, '<tbody><tr><td>머리</td><td>138,335</td><td>4,554</td><td>2,723</td></tr><tr><td>몸통</td><td>141,394</td><td>1,582</td><td>2,636</td></tr>'
           '<tr><td>신발</td><td>140,163</td><td>2,809</td><td>2,640</td></tr><tr><td>무기</td><td>143,246</td><td>90</td><td>2,276</td></tr></tbody>',
        '<tbody>' + ''.join(f'<tr><td>{ko}</td><td>{f(arm[s]["mapped"])}</td><td>{f(arm[s]["gathering"])}</td><td>{f(arm[s]["missing"])}</td></tr>'
                            for s, ko in (('HEAD', '머리'), ('ARMOR', '몸통'), ('SHOES', '신발')))
        + f'<tr><td>무기</td><td>{f(g["weapons"]["mapped"])}</td><td>{f(wo)}</td><td>{f(g["weapons"]["missing"])}</td></tr></tbody>')
H = sub(H, '<li>무기·방어구 비중 = 품목 장착 횟수 ÷ 145,612.', f'<li>무기·방어구 비중 = 품목 장착 횟수 ÷ {OB}.')
H = sub(H, '<li>순위 이력의 이전 버전은 11/5–11/12 공식 API 표본(93,065건), ',
        f'<li>순위 이력의 이전 버전은 {PREV["label"]} 공식 API 표본({f(PREV["events"])}건), 11/5–11/12 공식 API 표본(93,065건), ')
H = sub(H, '앞의 네 버전은 이번 버전과 수집 방법·집계 기준이 같고(10/23–10/29와 10/17–10/22는 패치 4 이전)',
        '앞의 다섯 버전은 이번 버전과 수집 방법·집계 기준이 같고(10/23–10/29와 10/17–10/22는 패치 4 이전)')
H = sub(H, '10월 16일부터 4분마다 최신 기록을 읽어 중복 없이 저장했고, 11월 13–18일 고유 기록 231,269건을 집계했습니다. 게임 서버 전수 통계는 아닙니다. '
           '직전 네 버전(11/5–11/12, 11/2–11/4, 10/23–10/29, 10/17–10/22)도 같은 방법으로 모았고',
        f'10월 16일부터 4분마다 최신 기록을 읽어 중복 없이 저장했고, {KO} 고유 기록 {f(g["uniqueInWindow"])}건({SAMPLE_NOTE})을 집계했습니다. 게임 서버 전수 통계는 아닙니다. '
        f'직전 다섯 버전({PREV["label"]}, 11/5–11/12, 11/2–11/4, 10/23–10/29, 10/17–10/22)도 같은 방법으로 모았고')
H = sub(H, f'<a href="https://github.com/ao-data/ao-bin-dumps/tree/{P4}" target="_blank" rel="noopener noreferrer">ao-data / ao-bin-dumps — 게임 클라이언트 데이터</a> · '
           '2026.11.02 업데이트(드래곤파이어 패치 4 적용 후 추출).',
        f'<a href="https://github.com/ao-data/ao-bin-dumps/tree/{P5}" target="_blank" rel="noopener noreferrer">ao-data / ao-bin-dumps — 게임 클라이언트 데이터</a> · '
        '2026.11.26 업데이트(드래곤파이어 패치 5 적용 후 추출).')
H = sub(H, '패치 4 수치 반영: 2026.11.05 · 수치 재대조: 2026.11.13(수치 원본은 11월 2일).',
        '패치 4 수치 반영: 2026.11.05 · 패치 5 수치 반영: 2026.11.26(수치 원본은 11월 26일).')
H = sub(H, f'https://github.com/ao-data/ao-bin-dumps/blob/{P4}/gamedata.xml', f'https://github.com/ao-data/ao-bin-dumps/blob/{P5}/gamedata.xml')
H = sub(H, f'https://github.com/ao-data/ao-bin-dumps/blob/{P4}/spells.xml', f'https://github.com/ao-data/ao-bin-dumps/blob/{P5}/spells.xml')
H = sub(H, '2026.11.19(한국 시간) 재확인 시 저장소 최신 커밋은 2026.11.02 추출본(0483dd9)입니다. 이전 자료(2026.10.12 추출본, 1a469e5)와 비교해 바뀐 스킬·장비를 반영했습니다.',
        f'{VERSION_DATE}(한국 시간) 재확인 시 저장소 최신 커밋은 2026.11.26 추출본(d277a5c)입니다. 이전 자료(2026.11.02 추출본, 0483dd9)와 비교해 바뀐 스킬·장비를 반영했습니다.')
H = sub(H, '<div>확인·업데이트 2026.11.19 · 시세 수집 2026.11.19 · 수치 원본 2026.11.02 · 표본 수집 2026.11.13–19 (한국 시간)<br>',
        f'<div>확인·업데이트 {VERSION_DATE} · 시세 수집 {t_fetch:%Y.%m.%d} · 수치 원본 2026.11.26 · 표본 수집 {COLLECT_DOT} (한국 시간)<br>')

# ------------------------------------------------------------------ app script
J = sub(J, '<small>효과: 2026.11.02 게임 데이터(드래곤파이어 패치 4 반영) · 피해·회복·보호막은 IP 등에 따라 달라집니다. 카운터는 효과에 근거한 대응 예시입니다. 시세: 2026.11.19 수집(아시아 서버).</small>',
        f'<small>효과: 2026.11.26 게임 데이터(드래곤파이어 패치 5 반영) · 피해·회복·보호막은 IP 등에 따라 달라집니다. 카운터는 효과에 근거한 대응 예시입니다. '
        f'시세: {t_fetch:%Y.%m.%d} 수집(아시아 서버, {SAMPLE_NOTE} 거래).</small>', 1, 'J')
J = sub(J, '수치 자료: 2026.11.02 추출본(드래곤파이어 패치 4 반영) · 계산·연결·문구 확인: 2026.10.16 · 패치 4 반영: 2026.11.05.',
        '수치 자료: 2026.11.26 추출본(드래곤파이어 패치 5 반영) · 계산·연결·문구 확인: 2026.10.16 · 패치 5 반영: 2026.11.26.', 1, 'J')
J = sub(J, '자료: 2026.11.02 게임 데이터(드래곤파이어 패치 4) · 공개 최신 원본 확인 2026.11.19 · 장착 빈도는 ${esc(RAW.meta.shortPeriod)} 단독 처치 표본 · 시세 2026.11.19 수집',
        f'자료: 2026.11.26 게임 데이터(드래곤파이어 패치 5) · 공개 최신 원본 확인 {VERSION_DATE} · 장착 빈도는 ${{esc(RAW.meta.shortPeriod)}} 단독 처치 표본({SAMPLE_NOTE}) · '
        f'시세 {t_fetch:%Y.%m.%d} 수집({SAMPLE_NOTE} 거래)', 1, 'J')
J = sub(J, '<li>수치 원본 2026.11.02(드래곤파이어 패치 4) · 계산 확인 2026.11.05(한국 시간).</li>',
        f'<li>수치 원본 2026.11.26(드래곤파이어 패치 5) · 계산 확인 {VERSION_DATE}(한국 시간).</li>', 1, 'J')
J = sub(J, '최근 14일', f'{SAMPLE_NOTE} {MDAYS}일', 9, 'J')
J = sub(J, '직전 버전(11/5–11/12)과 수집 방법·집계 기준이 같고 둘 다 패치 4 이후 표본입니다.',
        f'직전 버전({PREV["label"]})과 수집 방법·집계 기준이 같고 둘 다 패치 4 이후·패치 5 이전 표본입니다.', 1, 'J')
# a sample label (meta.sampleNote) next to the shares; the next version simply drops the key
J = sub(J, '`${RAW.meta.period} 최신 수집 표본 · 비중 분모',
        "`${RAW.meta.period} 최신 수집 표본${RAW.meta.sampleNote?'('+esc(RAW.meta.sampleNote)+')':''} · 비중 분모", 1, 'J')
J = sub(J, '<div class="hint">${fmt(RAW.meta.denominator)}회 기준</div>',
        "<div class=\"hint\">${fmt(RAW.meta.denominator)}회 기준${RAW.meta.sampleNote?' · '+esc(RAW.meta.sampleNote):''}</div>", 1, 'J')
# price window label (meta.market.windowNote) and the order window of a pre-patch snapshot
J = sub(J, '<p>${mdUTC(MK.since)}–${mdUTC(MK.until)} 실제 거래 평균 · 일반~뛰어남 품질 · 단위 실버</p>',
        "<p>${mdUTC(MK.since)}–${mdUTC(MK.until)}${MK.windowNote?' '+esc(MK.windowNote):''} 실제 거래 평균 · 일반~뛰어남 품질 · 단위 실버</p>", 1, 'J')
J = sub(J, '판매 요청서는 수집 때 보인 최저가라 이미 팔렸을 수 있습니다.',
        "판매 요청서는 ${MK.ordersBefore?'패치 직전 24시간 동안 보인':'수집 때 보인'} 최저가라 이미 팔렸을 수 있습니다.", 1, 'J')
# item-level patch notes (cloth robes) in the weapon/armour detail, as extras already show them
J = sub(J, '<span id="detailFavorite">${favoriteButton(i)}</span></div>${detailStats(i)}',
        "<span id=\"detailFavorite\">${favoriteButton(i)}</span></div>${i.patch?`<div class=\"patch-note\"><b>${esc(i.patchTitle||'패치 변경')}</b><p>${esc(i.patch)}</p></div>`:''}${detailStats(i)}",
        1, 'J')

# ------------------------------------------------------------------ write
D = json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
open(OUT, 'w', encoding='utf-8').write(H + D + J)
json.dump(moves, open(OUT + '.moves.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('written', OUT, len((H + D + J).encode('utf-8')), 'bytes | version', VERSION_ID, '| events', E, '| maint', MAINT_LO, MAINT_HI, '| market', M_DOT, PRICED,
      '| early/late', round(EARLY, 4), round(LATE, 4), '| premiums', [prem(q) for q in (2, 3, 4, 5)], '| drop', DROP_SHARE, '| bm', BM_RATIO,
      '| dps', len(m['dps']['skills']), len(m['dps']['nodmg']))
