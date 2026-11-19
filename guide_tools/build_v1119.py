"""Build the 2026-11-19 guide from the 2026-11-13 page: new ranking sample (11/13-11/18 KST), new price snapshot
(11/06-11/19 UTC days), rank history v7, update notes. Game data unchanged (ao-bin-dumps 0483dd9 is still HEAD), so
items' static fields, spells and images are carried over byte for byte.

Usage: python3 -I build_v1119.py <11/13 page> <agg.json> <market.json> <checked UTC> <qa.json or -> <out.html>
  agg.json    = ao_log/tools/aggregate.py for 2026-11-13T00:00 .. 2026-11-19T00:00 KST
  market.json = build_market.py for 2026-11-06 .. 2026-11-19
  checked UTC = commit time of the newest collector data used (2026-11-19T08:32:35Z)
"""
import collections, datetime as dt, json, re, sys

SRC, AGG, MARKET, CHECKED, QA, OUT = sys.argv[1:7]
html = open(SRC, encoding='utf-8').read()
TAG = '<script id="guideData" type="application/json">'
a = html.index(TAG) + len(TAG)
b = html.index('</script>', a)
H, d, J = html[:a], json.loads(html[a:b]), html[b:]
g = json.load(open(AGG, encoding='utf-8'))
mk = json.load(open(MARKET, encoding='utf-8'))
MM, MS = mk['meta'], mk['stats']
qa = None if QA == '-' else json.load(open(QA, encoding='utf-8'))
m = d['meta']
assert m['versionDate'] == '2026.11.13' and len(m['rankHistory']) == 6, 'template must be the 11/13 page'


def sub(text, old, new, n=1, where=''):
    c = text.count(old)
    assert c == n, (where, c, n, old[:160])
    return text.replace(old, new)


f = lambda n: f'{n:,}'
KST = dt.timedelta(hours=9)
p_utc = lambda s: dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')

# ------------------------------------------------------------------ constants of this version
VERSION_DATE, REVIEW_KO, REVIEW_DAY = '2026.11.19', '2026년 11월 19일', '11월 19일'
PREV = {'label': '11/5–11/12', 'days': 8, 'events': 93065}
QW_CHECK = {'at': '2026-11-19 19:37 KST', 'events': 303, 'equipment': 4910, 'withActiveSpells': 0, 'withPassiveSpells': 0}
SEASON35 = 'https://steamcommunity.com/games/761890/announcements/detail/1849458702693040'
# polls whose read-back did not reach the full 3-minute overlap; the ranges they read still overlapped the previous poll
OVERLAP_SHORT = [
    {'atKst': '11/17 00:31:03', 'oldestRead': '00:18:16', 'overlapFrom': '00:18:09', 'previousNewest': '00:21:09'},
    {'atKst': '11/17 00:35:01', 'oldestRead': '00:23:16', 'overlapFrom': '00:22:11', 'previousNewest': '00:25:11'},
    {'atKst': '11/17 00:39:03', 'oldestRead': '00:26:42', 'overlapFrom': '00:26:10', 'previousNewest': '00:29:10'},
]
assert all(x['oldestRead'] <= x['previousNewest'] for x in OVERLAP_SHORT)

# ------------------------------------------------------------------ sample figures
assert g['windowKst'] == ['2026-11-13T00:00', '2026-11-19T00:00']
w0 = dt.datetime.strptime(g['windowKst'][0], '%Y-%m-%dT%H:%M')
w1 = dt.datetime.strptime(g['windowKst'][1], '%Y-%m-%dT%H:%M')
d1 = w1 - dt.timedelta(days=1)
assert w0.month == d1.month == w1.month
NDAYS = (w1 - w0).days
KO = f'{w0.month}월 {w0.day}–{d1.day}일'                        # 11월 13–18일
SLASH = f'{w0.month}/{w0.day}–{d1.day}'                          # 11/13–18
SLASH_FULL = f'{w0.month}/{w0.day}–{d1.month}/{d1.day}'          # 11/13–11/18
DOT = f'{w0:%Y.%m.%d}–{d1:%d}'                                   # 2026.11.13–18
PERIOD = f'{w0:%Y.%m.%d}–{d1:%m.%d}'                             # 2026.11.13–11.18
COLLECT_DOT = f'{w0:%Y.%m.%d}–{w1:%d}'                           # 2026.11.13–19
E, OBS = g['events'], g['observations']
EV, OB = f(E), f(OBS)
assert OBS == 2 * E and len(g['daily']) == NDAYS and sum(g['daily'].values()) == E
first, last = p_utc(g['firstEvent']) + KST, p_utc(g['lastEvent']) + KST
assert w0 <= first < w0 + dt.timedelta(minutes=5) and w1 - dt.timedelta(minutes=5) < last < w1
EXC = g['excluded']
EXC_SUM = sum(EXC.values())
assert g['uniqueInWindow'] - EXC_SUM == E
h = g['health']
assert h['failedPolls'] == 0 and h['fetchWarnings'] == 0
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
assert VERSION_ID.startswith('20261119-')

# ------------------------------------------------------------------ market figures
since, until = dt.date.fromisoformat(MM['since']), dt.date.fromisoformat(MM['until'])
fresh = dt.date.fromisoformat(MM['fresh'])
MDAYS = MM['days']
assert (until - since).days + 1 == MDAYS == 14 and since == dt.date(2026, 11, 6)       # no balance patch inside: full 14 days
M_SLASH = f'{since.month}/{since.day}–{until.month}/{until.day}'                        # 11/6–11/19
M_KO = f'{since.month}월 {since.day}–{until.day}일'                                      # 11월 6–19일
M_DOT = f'{since:%Y.%m.%d}–{until:%m.%d}'                                               # 2026.11.06–11.19
t_fetch = p_utc(MM['histFetched'][0]) + KST
FETCH_HM = f'{t_fetch:%H:%M}'
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
assert 0.6 < EARLY < 0.85 and LATE < 0.1, (EARLY, LATE)
WEAK_BEFORE = fresh - dt.timedelta(days=1)

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
m['versionId'], m['versionDate'] = VERSION_ID, VERSION_DATE
m['checkedDate'] = VERSION_DATE                 # latest public game data re-checked today (HEAD still 0483dd9)
assert m['numericCheckedDate'] == '2026.11.13'  # numbers not re-compared this time: data identical to the 11/13 page
POLL_SUMMARY = (f"확인 {f(h['polls'])}회는 모두 성공했습니다. 11월 17일 0시 31–39분에는 기록이 몰려 세 번의 확인에서 "
                '겹쳐 읽는 여유분(3분)을 다 읽지 못했지만, 읽은 구간 자체는 끊기지 않고 이어졌습니다.')
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
    xk['hint'] = sub(xk['hint'], '11월 5–12일', KO, 1, k)
    e = g['extras'][k]
    new_note = re.sub(r'11/5–12 단독 처치 표본 · 장착 [\d,]+회 · 도감 밖 [\d,]+회',
                      f"{SLASH} 단독 처치 표본 · 장착 {f(e['equipped'])}회 · 도감 밖 {f(e['outsideCount'])}회", xk['note'])
    assert new_note != xk['note'], k
    xk['note'] = new_note
m['coUsage']['window'] = g['windowKst']
m['coUsage']['anchors'] = len(g['co'])
ranks, counts = {}, {}
for it in d['items']:
    ranks[it['id']], counts[it['id']] = it['rank'], it['count']
sample_label = f'{first:%m/%d %H:%M:%S}–{last:%m/%d %H:%M:%S} KST · {EV}건'
m['rankHistory'].append({'id': VERSION_ID, 'date': VERSION_DATE, 'label': f'{VERSION_DATE} · {SLASH} 공식 API 표본', 'ranks': ranks, 'counts': counts,
                         'samples': {k: sample_label for k in ranks}, 'source': pv['source'], 'eventsCount': E, 'observations': OBS,
                         'sequence': 7})
old_mk = m['market']
m['market'] = dict(MM)
m['market']['previous'] = {k: old_mk[k] for k in ('since', 'until', 'histFetched', 'ordersFetched', 'counts', 'dropped')}
m['review20261119'] = {
    'date': VERSION_DATE, 'timezone': 'Asia/Seoul', 'sample': f'{SLASH_FULL} KST official API', 'windowKst': g['windowKst'],
    'events': E, 'observations': OBS, 'uniqueInWindow': g['uniqueInWindow'], 'excluded': EXC, 'health': h,
    'maintenanceMinutes': {k: round(v, 1) for k, v in sorted(maint.items())}, 'afterMaintenanceLulls': lulls,
    'outages': [], 'collectionGaps': [], 'overlapShortfalls': OVERLAP_SHORT,
    'dataDate': '2026.11.02', 'latestCommit': m['commit'],
    'patchCheck': 'ao-bin-dumps HEAD 0483dd9 and Steam announcements checked 2026-11-19 (KST): nothing after Dragonfire Patch 4 (11/02); '
                  'the Season 35 notice (2026-11-17) says Dragonfire Patch 5 comes later in November',
    'staticCheck': 'items static fields, spells and images identical to the 2026.11.13 page',
    'qwCheck': QW_CHECK, 'market': {'stats': MS, 'window': [MM['since'], MM['until']], 'rule': 'last 14 UTC days, from a balance patch day if one falls inside'},
}
if qa:
    m['review20261119']['qa'] = qa
assert m['commit'] == '0483dd97f1581dfaf02eed42f25f5ea2a3cb75e5'

# ------------------------------------------------------------------ static page text
H = sub(H, '<title>알비온 장비 도감 · 342종 · 2026.11.13 업데이트</title>', f'<title>알비온 장비 도감 · 342종 · {VERSION_DATE} 업데이트</title>')
H = sub(H, '<div class="eyebrow">ASIA · 8-DAY OFFICIAL API SAMPLE</div>', f'<div class="eyebrow">ASIA · {NDAYS}-DAY OFFICIAL API SAMPLE</div>')
H = sub(H, '<div><strong>93,065</strong><small>단독 가해자 기록</small></div><div><strong>8일</strong><small>2026.11.05–12</small></div>',
        f'<div><strong>{EV}</strong><small>단독 가해자 기록</small></div><div><strong>{NDAYS}일</strong><small>{DOT}</small></div>')
H = sub(H, '<div class="sample-foot">아시아 서버 · 11월 5–12일 기록 · ', f'<div class="sample-foot">아시아 서버 · {KO} 기록 · ')
H = sub(H, '<span><b>2026.11.13 업데이트 · 종합판</b>10월 25일판의 티어별 시세와 11월 5일판의 패치 4 반영·같이 많이 쓰는 장비 TOP 3를 한 파일로 합쳤습니다. '
           '장착 순위·비중은 11월 5–12일 새 표본(단독 처치 93,065건)으로, 시세는 패치 4 적용일부터 11일(11/2–11/12)의 거래로 새로 받았습니다.</span>',
        f'<span><b>{VERSION_DATE} 업데이트</b>장착 순위·비중과 같이 많이 쓰는 장비 TOP 3를 {KO} 새 표본(단독 처치 {EV}건)으로 다시 매기고, '
        f'시세는 최근 {MDAYS}일({M_SLASH})의 거래로 새로 받았습니다. 게임 데이터는 바뀌지 않아 설명·수치는 그대로입니다.</span>')
H = sub(H, '<p id="resultNote">비중은 각 장비 슬롯의 전체 장착 기회 186,130회 기준입니다.</p>', f'<p id="resultNote">비중은 각 장비 슬롯의 전체 장착 기회 {OB}회 기준입니다.</p>')
H = sub(H, '시세는 아시아 서버의 최근 11일(11/2–11/12, 패치 4 적용일부터) 실제 거래 평균입니다.', f'시세는 아시아 서버의 최근 {MDAYS}일({M_SLASH}) 실제 거래 평균입니다.')
H = sub(H, '시세는 아시아 서버에서 최근 11일 동안 실제로 거래된 평균 가격(실버)입니다.', f'시세는 아시아 서버에서 최근 {MDAYS}일 동안 실제로 거래된 평균 가격(실버)입니다.')
H = sub(H, '이번 자료에서는 대체로 도시보다 높게(중앙값 약 1.6배) 사 갔습니다.', f'이번 자료에서는 대체로 도시보다 높게(중앙값 약 {BM_RATIO}배) 사 갔습니다.')
H = sub(H, '<p>2026년 11월 13일 기준으로 확인했습니다. 장착 순위는 공식 킬 기록 API로 직접 모은 11/5–11/12 아시아 단독 처치 93,065건을 사용합니다. '
           '수치와 신발 이동거리의 원본은 이날 확인한 최신 공개 추출본인 11월 2일 자료(드래곤파이어 패치 4 적용 후)입니다. 티어별 시세는 11월 13일 08:27쯤(한국 시간)에 따로 수집했습니다.',
        f'<p>{REVIEW_KO} 기준으로 확인했습니다. 장착 순위는 공식 킬 기록 API로 직접 모은 {SLASH_FULL} 아시아 단독 처치 {EV}건을 사용합니다. '
        f'수치와 신발 이동거리의 원본은 이날 확인한 최신 공개 추출본인 11월 2일 자료(드래곤파이어 패치 4 적용 후)입니다. 티어별 시세는 {REVIEW_DAY} {FETCH_HM}쯤(한국 시간)에 따로 수집했습니다.')

# update notes: new section on top, the 11/13 notes become the newest history entry
SEC = '<section class="reading-panel feature-review" id="featureReview"><h2>2026년 11월 13일 업데이트 · 종합판</h2><ul>\n'
i0 = H.index(SEC)
END13 = '</ul><p>기준일: 2026.11.13 / 시세: 2026.11.02–11.12 거래(11.13 08:27쯤 수집) / 수치 원본: 2026.11.02 (0483dd9) / 장착 표본: 2026.11.05–12 (공식 API, 한국 시간).</p>\n'
i1 = H.index(END13, i0)
body13 = H[i0 + len(SEC):i1]
assert body13.count('<span id="featureQaText">') == 1 and body13.count('<li>') == 8
history13 = ('<details class="update-history"><summary>이전 기록 · 2026년 11월 13일 업데이트 · 종합판</summary><ul>\n'
             + body13.replace('<span id="featureQaText">', '<span>') + END13 + '</details>\n')
if qa:
    QA_TEXT = (f"실제 브라우저(Chromium)로 8개 분류의 카드·표·시세표와 정렬, 장비 {qa['detailsOpened']}종 상세의 시세·순위 변화·TOP 3 영역과 바로 가기, 비교 창, "
               f"DPS·이동거리·1:1 순위 화면을 열어 스크립트 오류 {qa['scriptErrors']}건을 확인했습니다. {qa['widths']}px 화면과 어두운 테마에서 가로 넘침이 없는지도 확인했습니다.")
else:
    QA_TEXT = '(검증 문장은 점검을 마친 뒤 채웁니다.)'
NEW_NOTES = (
    f'<section class="reading-panel feature-review" id="featureReview"><h2>{REVIEW_KO} 업데이트</h2><ul>\n'
    f'<li><b>새 장착 표본</b>: {KO}(한국 시간, {NDAYS}일) 아시아 서버의 단독 처치 {EV}건으로 무기·방어구 순위와 비중, 기타 장비 6종의 1:1 참고 순위, '
    f'같이 많이 쓰는 장비 TOP 3를 새로 매겼습니다(승자·사망자 양측 {OB}회). 모두 11월 2일 패치 4 적용 뒤의 기록입니다.</li>\n'
    f'<li><b>새 시세</b>: Albion Online Data Project 아시아 서버 공개 API에서 {MM["collectedLabel"].replace("(한국 시간)", "")}(한국 시간)에 다시 받았습니다. '
    f'최근 {MDAYS}일({M_KO})의 실제 거래 평균이며, 이 기간에는 밸런스 패치가 없어 {MDAYS}일을 모두 썼습니다(11월 13일판은 패치 4 적용일인 11월 2일부터 11일). '
    f'게임에 있는 {f(CNT["exists"])}칸 중 {f(PRICED)}칸에 가격이 있고(도시 거래 {f(CNT["city"])}칸, 암시장 거래만 있는 칸 {f(CNT["bmOnly"])}칸), '
    f'수집된 거래가 없는 {f(CNT["none"])}칸은 ‘–’, 게임에 없는 단계 {f(CNT["noTier"])}칸은 빈칸입니다. 계산 기준은 아래 ‘티어별 시세 · 읽는 법과 계산 기준’에 있습니다.</li>\n'
    f'<li><b>설명·수치</b>: 바꾸지 않았습니다(11월 2일 드래곤파이어 패치 4 기준). {REVIEW_DAY} 확인 때도 새 패치와 새 게임 데이터 추출본은 없고(ao-bin-dumps 최신 커밋 0483dd9 그대로), '
    f'스킬 476종과 장비 342종의 이름·설명·수치 자료가 11월 13일판과 똑같음을 확인했습니다. '
    f'<a href="{SEASON35}" target="_blank" rel="noopener noreferrer">11월 17일 시즌 35 공지</a>에 따르면 드래곤파이어 패치 5가 이달 중 나올 예정이지만, 아직 적용 전이라 반영하지 않았습니다.</li>\n'
    f'<li><b>빠진 시간</b>: 매일 아침 8시 전후 {MAINT_LO}–{MAINT_HI}분은 서버 점검으로 기록 자체가 없습니다. 그 밖에 수집이 끊긴 구간은 없고 확인 {f(h["polls"])}회는 모두 성공했습니다. '
    '11월 17일 0시 31–39분에는 기록이 몰려 세 번의 확인에서 겹쳐 읽는 여유분(3분)을 다 읽지 못했지만, 읽은 구간 자체는 끊기지 않고 이어졌습니다.</li>\n'
    f'<li><b>순위 변화</b>: 순위 옆 (▲·▼)와 최근 10개 버전 그래프에 이번 버전(7번째 기록)을 더했습니다. 직전 버전({PREV["label"]}, {PREV["days"]}일, 단독 처치 {f(PREV["events"])}건)과 '
    '수집 방법·집계 기준이 같고 둘 다 패치 4 이후 표본입니다. 장착 횟수가 적은 품목은 표본에 따라 순위가 크게 흔들릴 수 있습니다.</li>\n'
    f'<li><b>Q·W 순위</b>: 이번에도 만들 수 없었습니다. 공식 킬 기록의 스킬 칸은 {REVIEW_DAY} 확인 때도 모두 비어 있습니다(최근 기록 {QW_CHECK["events"]}건의 장비 {f(QW_CHECK["equipment"])}개 모두 빈 값).</li>\n'
    '<li><b>검증</b>: 순위·비중과 같이 많이 쓰는 장비 TOP 3는 원본 기록에서 따로 다시 세어 342종 모두 일치함을 확인했습니다. '
    f'시세는 아이템 ID {f(MS["idsQueried"])}개 전부를 저장해 둔 API 응답에서 별도 코드로 다시 계산해 차이 0건을 확인했고, 그 아이템 ID가 모두 지금 게임 데이터(0483dd9)의 아이템 목록에 있는지도 다시 대조했습니다. '
    f'<span id="featureQaText">{QA_TEXT}</span></li>\n'
    f'</ul><p>기준일: {VERSION_DATE} / 시세: {M_DOT} 거래({t_fetch:%m.%d} {FETCH_HM}쯤 수집) / 수치 원본: 2026.11.02 (0483dd9) / 장착 표본: {DOT} (공식 API, 한국 시간).</p>\n'
)
H = H[:i0] + NEW_NOTES + history13 + H[i1 + len(END13):]
H = sub(H, '현재 표본과 이번 변경 사항은 위 11월 13일 업데이트를 기준으로 읽으세요.', f'현재 표본과 이번 변경 사항은 위 {REVIEW_DAY} 업데이트를 기준으로 읽으세요.')

# market panel
H = sub(H, '<li><b>수집</b>: 2026.11.13 08:27–08:29(한국 시간). 아이템 ID 2,243개(여덟 단계)와 참고 티어 10개를 한 번에 조회했습니다.</li>',
        f'<li><b>수집</b>: {MM["collectedLabel"]}. 아이템 ID {f(CNT["exists"])}개(여덟 단계)와 참고 티어 {MS["refIds"]}개를 한 번에 조회했습니다.</li>')
H = sub(H, '<li><b>기간</b>: 11월 2일(드래곤파이어 패치 4 적용일)–11월 12일, 11일. 최근 14일을 기본으로 하되 그 안에 밸런스 패치가 있으면 패치 날부터 셉니다'
           '(10월 25일판은 패치 3 적용일인 10월 12일부터 14일). 날짜는 UTC 일별 묶음이라 한국 시간 오전 9시에 하루가 바뀝니다. '
           '패치 4는 11월 2일 19시(한국 시간)에 적용되어 첫 묶음(2일)에는 패치 전 10시간의 거래도 들어 있고, 마지막 묶음(12일)은 수집 시점까지입니다.</li>',
        f'<li><b>기간</b>: {since.month}월 {since.day}일–{until.month}월 {until.day}일, {MDAYS}일. 최근 14일을 기본으로 하되 그 안에 밸런스 패치가 있으면 패치 날부터 셉니다'
        f'(이번 기간에는 패치가 없어 14일을 모두 썼고, 11월 13일판은 패치 4 적용일인 11월 2일부터 11일이었습니다). 날짜는 UTC 일별 묶음이라 한국 시간 오전 9시에 하루가 바뀝니다. '
        f'마지막 묶음({until.day}일)은 수집 시점까지입니다.</li>')
H = sub(H, '이번 자료의 도시 거래 개수는 11월 2–5일이 63%, 11월 10–12일이 6%여서 평균은 기간 앞쪽의 가격을 더 많이 반영합니다.',
        f'이번 자료의 도시 거래 개수는 {since.month}월 {since.day}–{EARLY_TO.day}일(앞 7일)이 {EARLY * 100:.0f}%, {LATE_FROM.month}월 {LATE_FROM.day}–{until.day}일이 {LATE * 100:.0f}%여서 평균은 기간 앞쪽의 가격을 더 많이 반영합니다.')
H = sub(H, '두 값이 모두 있는 장비에서 암시장 평균은 도시 평균의 중앙값 약 1.6배였습니다.', f'두 값이 모두 있는 장비에서 암시장 평균은 도시 평균의 중앙값 약 {BM_RATIO}배였습니다.')
H = sub(H, '같은 도시·날짜에서 일반 품질 대비 중앙값이 좋음 +1%, 뛰어남 +7%, 우수함 +39%, 걸작 +142%라서 우수함·걸작은 뺐습니다.',
        f'같은 도시·날짜에서 일반 품질 대비 중앙값이 좋음 {prem(2)}, 뛰어남 {prem(3)}, 우수함 {prem(4)}, 걸작 {prem(5)}라서 우수함·걸작은 뺐습니다.')
H = sub(H, '이상 거래로 보고 뺐습니다(도시 397개 · 암시장 3개, 도시 거래 개수 기준 0.13%).',
        f'이상 거래로 보고 뺐습니다(도시 {f(MM["dropped"]["city"])}개 · 암시장 {f(MM["dropped"]["bm"])}개, 도시 거래 개수 기준 {DROP_SHARE}).')
H = sub(H, '마지막 거래가 11월 4일 이전(1주 넘게 지남)인 값입니다.', f'마지막 거래가 {WEAK_BEFORE.month}월 {WEAK_BEFORE.day}일 이전(1주 넘게 지남)인 값입니다.')
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
H = sub(H, '거래 기록이 없는 칸 중 303칸은 판매 요청서만 확인돼 상세에 참고로 표시합니다.', f'거래 기록이 없는 칸 중 {f(CNT["noneWithOrder"])}칸은 판매 요청서만 확인돼 상세에 참고로 표시합니다.')

# patch panel, method grid, sources, footer
H = sub(H, '<p class="table-note">현재 장착 순위는 11월 5–12일 기록(공식 API로 실시간 수집)입니다.', f'<p class="table-note">현재 장착 순위는 {KO} 기록(공식 API로 실시간 수집)입니다.')
H = sub(H, '<h2>아시아 · 11월 5–12일 · 93,065건</h2>', f'<h2>아시아 · {KO} · {EV}건</h2>')
H = sub(H, '<li>한국 시간 11월 5일 0시부터 12일 24시까지 8일입니다. 모두 11월 2일 패치 4 적용 뒤의 기록입니다. 실제 포함 기록: 2026.11.05 00:00:03–2026.11.12 23:59:54 (한국 시간).</li>',
        f'<li>한국 시간 {w0.month}월 {w0.day}일 0시부터 {d1.day}일 24시까지 {NDAYS}일입니다. 모두 11월 2일 패치 4 적용 뒤의 기록입니다. 실제 포함 기록: {m["periodKstLabel"]}.</li>')
H = sub(H, '기간 안 고유 기록 294,194건 중 조건 미충족 201,129건(가해자 2명 이상 196,064건, 그룹 2명 이상 4,737건, 명단 불일치 328건)을 제외했습니다.',
        f'기간 안 고유 기록 {f(g["uniqueInWindow"])}건 중 조건 미충족 {f(EXC_SUM)}건(가해자 2명 이상 {f(EXC["not_single_participant"])}건, '
        f'그룹 2명 이상 {f(EXC["not_single_group_member"])}건, 명단 불일치 {f(EXC["roster_not_matching_killer"])}건)을 제외했습니다.')
H = sub(H, '<li>승자·사망자 양측을 모두 세어 부위당 186,130회입니다.', f'<li>승자·사망자 양측을 모두 세어 부위당 {OB}회입니다.')
H = sub(H, '<li>매일 아침 8시 전후의 서버 점검 시간에는 기록이 없습니다. 11월 7일 15:09–16:49(100분)과 18:05–18:29(25분)에도 게임 서버 쪽 장애로 보이는 중단 때문에 기록이 없으며, 그 밖에 수집이 끊긴 구간은 없습니다.',
        '<li>매일 아침 8시 전후의 서버 점검 시간에는 기록이 없으며, 그 밖에 수집이 끊긴 구간은 없습니다.')
H = sub(H, 'aria-label="11월 5–12일 날짜별 단독 가해자 표본 93,065건"', f'aria-label="{KO} 날짜별 단독 가해자 표본 {EV}건"')
arm = g['armor']
wo = sum(g['weapons']['outside'].values())
assert g['weapons']['mapped'] + wo + g['weapons']['missing'] == OBS and all(arm[s]['mapped'] + arm[s]['gathering'] + arm[s]['missing'] == OBS for s in arm)
H = sub(H, '<tbody><tr><td>머리</td><td>176,439</td><td>5,798</td><td>3,893</td></tr><tr><td>몸통</td><td>180,310</td><td>1,977</td><td>3,843</td></tr>'
           '<tr><td>신발</td><td>178,830</td><td>3,542</td><td>3,758</td></tr><tr><td>무기</td><td>182,642</td><td>116</td><td>3,372</td></tr></tbody>',
        '<tbody>' + ''.join(f'<tr><td>{ko}</td><td>{f(arm[s]["mapped"])}</td><td>{f(arm[s]["gathering"])}</td><td>{f(arm[s]["missing"])}</td></tr>'
                            for s, ko in (('HEAD', '머리'), ('ARMOR', '몸통'), ('SHOES', '신발')))
        + f'<tr><td>무기</td><td>{f(g["weapons"]["mapped"])}</td><td>{f(wo)}</td><td>{f(g["weapons"]["missing"])}</td></tr></tbody>')
H = sub(H, '<li>무기·방어구 비중 = 품목 장착 횟수 ÷ 186,130.', f'<li>무기·방어구 비중 = 품목 장착 횟수 ÷ {OB}.')
H = sub(H, '<li>순위 이력의 이전 버전은 11/2 19:30–11/4 공식 API 표본(패치 4 이후 약 2.2일, 단독 처치 27,106건), ',
        f'<li>순위 이력의 이전 버전은 {PREV["label"]} 공식 API 표본({f(PREV["events"])}건), 11/2 19:30–11/4 공식 API 표본(패치 4 이후 약 2.2일, 단독 처치 27,106건), ')
H = sub(H, '앞의 세 버전은 이번 버전과 수집 방법·집계 기준이 같고(10/23–10/29와 10/17–10/22는 패치 4 이전)',
        '앞의 네 버전은 이번 버전과 수집 방법·집계 기준이 같고(10/23–10/29와 10/17–10/22는 패치 4 이전)')
H = sub(H, '10월 16일부터 4분마다 최신 기록을 읽어 중복 없이 저장했고, 11월 5–12일 고유 기록 294,194건을 집계했습니다. 게임 서버 전수 통계는 아닙니다. 직전 세 버전(11/2–11/4, 10/23–10/29, 10/17–10/22)도 같은 방법으로 모았고',
        f'10월 16일부터 4분마다 최신 기록을 읽어 중복 없이 저장했고, {KO} 고유 기록 {f(g["uniqueInWindow"])}건을 집계했습니다. 게임 서버 전수 통계는 아닙니다. '
        f'직전 네 버전({PREV["label"]}, 11/2–11/4, 10/23–10/29, 10/17–10/22)도 같은 방법으로 모았고')
H = sub(H, '2026.11.13(한국 시간) 재확인 시 저장소 최신 커밋은 2026.11.02 추출본(0483dd9)입니다.', f'{VERSION_DATE}(한국 시간) 재확인 시 저장소 최신 커밋은 2026.11.02 추출본(0483dd9)입니다.')
H = sub(H, '<div>확인·업데이트 2026.11.13 · 시세 수집 2026.11.13 · 수치 원본 2026.11.02 · 표본 수집 2026.11.05–13 (한국 시간)<br>',
        f'<div>확인·업데이트 {VERSION_DATE} · 시세 수집 {t_fetch:%Y.%m.%d} · 수치 원본 2026.11.02 · 표본 수집 {COLLECT_DOT} (한국 시간)<br>')

# ------------------------------------------------------------------ app script
J = sub(J, '시세: 2026.11.13 수집(아시아 서버).', f'시세: {t_fetch:%Y.%m.%d} 수집(아시아 서버).', 1, 'J')
J = sub(J, '공개 최신 원본 확인 2026.11.13 · 장착 빈도는 ${esc(RAW.meta.shortPeriod)} 단독 처치 표본 · 시세 2026.11.13 수집',
        f'공개 최신 원본 확인 {VERSION_DATE} · 장착 빈도는 ${{esc(RAW.meta.shortPeriod)}} 단독 처치 표본 · 시세 {t_fetch:%Y.%m.%d} 수집', 1, 'J')
J = sub(J, '최근 11일', f'최근 {MDAYS}일', 9, 'J')
J = sub(J, '직전 버전(11/2 19:30–11/4)과 수집 방법·집계 기준이 같고 둘 다 패치 4 이후 표본입니다. 다만 직전 표본이 약 2.2일로 짧아, 장착 횟수가 적은 품목은 순위가 크게 흔들릴 수 있습니다.',
        f'직전 버전({PREV["label"]})과 수집 방법·집계 기준이 같고 둘 다 패치 4 이후 표본입니다. 장착 횟수가 적은 품목은 표본에 따라 순위가 크게 흔들릴 수 있습니다.', 1, 'J')

# ------------------------------------------------------------------ write
D = json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
open(OUT, 'w', encoding='utf-8').write(H + D + J)
json.dump(moves, open(OUT + '.moves.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('written', OUT, len((H + D + J).encode('utf-8')), 'bytes | version', VERSION_ID, '| events', E, '| maint', MAINT_LO, MAINT_HI, '| market', M_DOT, PRICED,
      '| early/late', round(EARLY, 4), round(LATE, 4), '| premiums', [prem(q) for q in (2, 3, 4, 5)], '| drop', DROP_SHARE, '| bm', BM_RATIO)
