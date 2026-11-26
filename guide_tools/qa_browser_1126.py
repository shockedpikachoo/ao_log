"""Open the built guide in Chromium and exercise every page, including the price feature.

Usage: python3 qa_browser_1126.py <guide.html> <screenshot dir> <agg.json> [report.json]
Prints a JSON report; exits 1 if a check fails or the page logs a script error.
"""
import json, os, re, sys, time
from playwright.sync_api import sync_playwright

PAGE, SHOTS = os.path.abspath(sys.argv[1]), sys.argv[2]
AGG = json.load(open(sys.argv[3], encoding='utf-8'))
REPORT = sys.argv[4] if len(sys.argv) > 4 else None
EV, OBS = f"{AGG['events']:,}", f"{AGG['observations']:,}"
os.makedirs(SHOTS, exist_ok=True)
report = {'errors': [], 'checks': {}, 'fail': []}
html = open(PAGE, encoding='utf-8').read()
DATA = json.loads(re.search(r'<script id="guideData" type="application/json">(.*?)</script>', html, re.S).group(1))
ITEMS = {i['id']: i for i in DATA['items']}
MK = DATA['meta']['market']
KINDS = ('armor', 'weapon', 'offhand', 'cape', 'bag', 'potion', 'food', 'mount')
EXPECT = {'armor': 84, 'weapon': 136, 'offhand': 18, 'cape': 15, 'bag': 2, 'potion': 15, 'food': 21, 'mount': 51}
WIDTHS = (1440, 1100, 1000, 860, 600, 390, 360)


def check(name, ok, detail=''):
    report['checks'][name] = {'ok': bool(ok), 'detail': str(detail)[:400]}
    if not ok:
        report['fail'].append(name)


def watch(page, tag):
    page.on('pageerror', lambda e: report['errors'].append(f'{tag} pageerror: {e}'))
    page.on('console', lambda m: report['errors'].append(f'{tag} console: {m.text}') if m.type == 'error' and 'render.albiononline.com' not in m.text and 'net::' not in m.text else None)


def load(page):
    page.goto('file://' + PAGE, wait_until='load', timeout=180000)
    page.wait_for_selector('#results .item-card', timeout=120000)


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = ctx.new_page()
    watch(page, 'desk')
    t0 = time.time()
    load(page)
    report['loadSeconds'] = round(time.time() - t0, 1)

    # ------------------------------------------------------------ header, hero, banner
    check('title', page.title() == '알비온 장비 도감 · 342종 · 2026.11.26 업데이트', page.title())
    bt = page.inner_text('.patch-banner')
    check('banner', '2026.11.26 업데이트 · 드래곤파이어 패치 5 반영' in bt and EV in bt and '11/12–11/25' in bt and 'TOP 3' in bt and '패치 5 이전 14일' in bt and '장비 변경 28개' in bt and '패치 5 이전 기록' in bt, bt)
    check('banner-buttons', page.locator('.patch-banner button').all_inner_texts() == ['검증 내역 보기', '시세 기준 보기'])
    hs = page.inner_text('.hero-side')
    check('hero-sample', EV in hs and '2026.11.19–25' in hs and '7일' in hs and '7-DAY OFFICIAL API SAMPLE' in hs and '11월 19–25일 기록(패치 5 이전)' in hs, hs)
    page.click('.patch-banner button:has-text("시세 기준 보기")')
    page.wait_for_timeout(400)
    geo = page.evaluate("(()=>{const r=document.querySelector('#marketPanel').getBoundingClientRect();return {top:r.top,hidden:document.querySelector('#sourcesPage').hidden}})()")
    check('banner-market-anchor', not geo['hidden'] and -2 <= geo['top'] <= 400, json.dumps(geo))
    page.screenshot(path=f'{SHOTS}/anchor_market.png')
    page.click('[data-page="catalog"]')
    page.click('.patch-banner button:has-text("검증 내역 보기")')
    page.wait_for_timeout(300)
    check('banner-sources', page.evaluate("!document.querySelector('#sourcesPage').hidden && document.querySelector('#catalogPage').hidden"))
    page.click('[data-page="catalog"]')

    # ------------------------------------------------------------ catalog: every kind in card, table and price view
    counts, price_rows, minis = {}, {}, {}
    for kind in KINDS:
        page.click(f'[data-kind="{kind}"]')
        if kind == 'armor':
            page.click('[data-slot="all"]')
        counts[kind] = page.locator('#results .item-card').count()
        minis[kind] = page.locator('#results .item-card .price-mini').count()
        page.click('#tableView')
        rows = page.locator('#results tbody tr').count()
        check(f'table-{kind}', rows == counts[kind], f'{rows} rows vs {counts[kind]} cards')
        page.click('#priceView')
        page.wait_for_selector('#results table.ptable')
        price_rows[kind] = page.locator('#results table.ptable tbody tr').count()
        heads = page.locator('#results table.ptable [data-psort]').all_inner_texts()
        want_heads = [t for t in MK['tiers'] if any(i['kind'] == kind and i['market']['t'][t] for i in DATA['items'])]
        order = ['4.0', '4.1', '5.0', '4.2', '5.1', '6.0', '7.0', '8.0']
        check(f'ptable-heads-{kind}', [h.replace('↕', '').strip() for h in heads] == [t for t in order if t in want_heads], heads)
        page.click('#cardView')
    check('catalog-counts', counts == EXPECT, json.dumps(counts))
    check('price-mini-on-every-card', minis == EXPECT, json.dumps(minis))
    check('price-table-rows', price_rows == EXPECT, json.dumps(price_rows))

    page.click('[data-kind="weapon"]')
    page.click('#priceView')
    page.wait_for_selector('#results table.ptable')

    def col_ids():
        return page.evaluate("[...document.querySelectorAll('#results table.ptable tbody tr .pt-name')].map(b=>b.dataset.detail)")

    base_order = col_ids()
    price = lambda i: (ITEMS[i]['market']['t']['6.0'] or {}).get('p')
    page.click('[data-psort="6.0"]')
    page.wait_for_timeout(150)
    vals = [price(i) for i in col_ids()]
    known = [v for v in vals if v is not None]
    check('psort-asc', known == sorted(known) and all(v is None for v in vals[len(known):]) and len(vals) == 136 and page.locator('th[aria-sort=ascending]').count() == 1, vals[:8])
    page.click('[data-psort="6.0"]')
    page.wait_for_timeout(150)
    vals = [price(i) for i in col_ids()]
    known = [v for v in vals if v is not None]
    check('psort-desc', known == sorted(known, reverse=True) and all(v is None for v in vals[len(known):]) and page.locator('th[aria-sort=descending]').count() == 1, vals[:8])
    page.click('[data-psort="6.0"]')
    page.wait_for_timeout(150)
    check('psort-reset', col_ids() == base_order and page.locator('th[aria-sort=ascending],th[aria-sort=descending]').count() == 0)
    first = base_order[0]
    c = ITEMS[first]['market']['t']['4.0']
    tip = page.locator('#results table.ptable tbody tr').first.locator('td').first.get_attribute('title')
    check('ptable-cell-tip', (c['p'] is None and '거래 기록 없음' in tip) or f"{c['p']:,}실버" in tip, tip)
    page.screenshot(path=f'{SHOTS}/price_table.png')
    page.click('#cardView')
    rn = page.inner_text('#resultNote')
    check('result-note', '2026.11.19–11.25 최신 수집 표본(패치 5 이전)' in rn and OBS in rn, rn)
    ph = page.inner_text('.price-hint')
    check('price-hint', '패치 5 이전 14일(11/12–11/25) 실제 거래 평균' in ph and '최근 14일' not in ph, ph[:80])

    page.click('[data-kind="armor"]')
    deltas = page.locator('#results .rank-change').all_inner_texts()
    check('rank-deltas', any('▲' in x for x in deltas) and any('▼' in x for x in deltas), f'{len(deltas)} markers, sample {deltas[:6]}')
    page.click('[data-kind="weapon"]')
    flags = page.locator('#results .patch-flag').all_inner_texts()
    check('weapon-flags', any('11.26' in f for f in flags) and any('11.02' in f for f in flags) and any('10.12' in f for f in flags), f'{len(flags)} flags, sample {flags[:4]}')
    page.click('[data-kind="armor"]')
    page.click('[data-slot="ARMOR"]')
    robe_flags = page.evaluate("[...document.querySelectorAll('#results .item-card')].filter(c=>c.querySelector('[data-detail^=ARMOR_CLOTH]')).map(c=>(c.querySelector('.patch-flag')||{}).textContent||'')")
    check('robe-flags', len(robe_flags) == 9 and all(x == '11.26 변경' for x in robe_flags), robe_flags)
    page.click('[data-slot="all"]')
    page.click('[data-kind="weapon"]')

    def open_item(item_id, skill=None):
        page.evaluate(f"openDetail({json.dumps(item_id)}, {json.dumps(skill)})")
        page.wait_for_selector('#detailDialog[open]')

    def close():
        page.evaluate("closeDialog('detailDialog')")

    # ------------------------------------------------------------ details carried over
    open_item('2H_KNUCKLES_SET2', 'DIVEPUNCH_RISE')
    txt = page.inner_text('#detailContent')
    check('falcon-smash-note', '10월 12일 패치 3 오류 수정' in txt and '10.12 수정' in txt)
    close()
    open_item('MAIN_AXE')
    dt_ = page.inner_text('#detailContent')
    check('rank-history-8', '8/10 기록' in dt_ and '11/26' in dt_ and '11/19' in dt_ and '11/13' in dt_ and '버전 8' in dt_, dt_[dt_.find('최근 10개'):dt_.find('최근 10개') + 80])
    hist_txt = page.text_content('#detailContent .rank-history')
    check('rank-history-labels', '2026.11.26 · 11/19–25 공식 API 표본(패치 5 이전)' in hist_txt and f'{EV}건' in hist_txt and '2026.11.19 · 11/13–18 공식 API 표본' in hist_txt, hist_txt[-500:])
    close()
    open_item('MAIN_HOLYSTAFF', 'SMITE_AOE')
    txt = page.inner_text('#detailContent')
    check('smite-note', '10월 12일 패치 3 변경' in txt and '115' in txt)
    close()
    open_item(page.evaluate("DB.find(i=>i.active.includes('DASHKICK')).id"), 'DASHKICK')
    txt = page.inner_text('#spellPanel')
    check('dashkick-stage2', '추가 사용 1' in txt and '7초' in txt)
    close()
    owner = page.evaluate("DB.find(i=>i.active.includes('IMMORTAL')).id")
    open_item(owner, 'IMMORTAL')
    txt = page.inner_text('#spellPanel')
    check('max-energy-render', '최대 에너지의' in txt and '% 최대 에너지' not in txt)
    close()
    open_item('MOUNT_DRAKE_FIRE')
    txt = page.inner_text('#detailContent')
    check('mount-patch-note', '10월 12일 패치 3 변경' in txt and '60초' in txt)
    check('extra-sample-note', '11/19–25 자료' in txt and '장착 빈도는 11/19–25 단독 처치 표본(패치 5 이전)' in txt and '공개 최신 원본 확인 2026.11.26' in txt and '2026.11.26 게임 데이터(드래곤파이어 패치 5)' in txt and '시세 2026.11.26 수집(패치 5 이전 거래)' in txt, txt[-300:])
    check('mount-notice-date', '이동 속도·탈것 체력은 11월 26일 게임 데이터(드래곤파이어 패치 5) 원본 값입니다.' in txt and '11월 2일 게임 데이터' not in txt)
    check('extra-no-jump', page.locator('#detailContent .detail-jump').count() == 0)
    check('mount-price', page.locator('#detailContent .price-section').count() == 1 and '탈것은 인챈트 단계가 없어 티어별로만 표시합니다.' in txt)
    close()
    open_item('MOUNT_MAMMOTH_BATTLE')
    txt = page.inner_text('#detailContent')
    check('extra-unseen', '미관측' in txt and ITEMS['MOUNT_MAMMOTH_BATTLE']['count'] == 0, txt[:200])
    close()
    open_item('CAPE')
    check('cape-notice-date', '패시브 수치는 11월 26일 게임 데이터(드래곤파이어 패치 5)의 원본 기본값입니다.' in page.inner_text('#detailContent'))
    close()
    open_item('MEAL_SOUP')
    txt = page.inner_text('#detailContent')
    check('food-notice-date', '수치는 11월 26일 게임 데이터(드래곤파이어 패치 5) 원본 기준입니다.' in txt and '11월 2일 게임 데이터' not in txt, txt[-400:])
    close()
    open_item('MEAL_GRILLEDFISH')
    txt = page.inner_text('#detailContent')
    check('food-ref-tier', '여덟 단계 밖의 티어 · 참고 시세' in txt and '이 품목은 4.0–8.0 여덟 단계에 해당하는 티어가 없습니다.' in txt, txt[:300])
    close()
    open_item('MOUNT_HORSE')
    txt = page.inner_text('#detailContent')
    ref = ITEMS['MOUNT_HORSE']['market']['ref'][0]
    check('mount-ref-tier', '여덟 단계 밖의 티어 · 참고 시세' in txt and f"{ref['p']:,}" in txt and f"{ref['n']:,}개" in txt, txt[txt.find('참고 시세'):txt.find('참고 시세') + 200])
    close()
    open_item('OFF_TORCH')
    txt = page.inner_text('#detailContent')
    check('offhand-labels', '재사용 대기 시간 감소 속도' in txt and '일반 공격 속도 보너스' in txt and 'T4.0 원본' not in txt)
    close()
    open_item('2H_CLAYMORE', 'CLAYMORECHARGE')
    txt = page.inner_text('#detailContent')
    check('p4-claymore', '11월 2일 패치 4 변경' in txt and '66%에서 100%' in txt and '경로 피해' not in txt)
    close()
    open_item('HEAD_LEATHER_DRAGON', 'FLARE')
    txt = page.inner_text('#detailContent')
    check('p4-flare-fix', '11.02 수정' in txt and '11월 2일 패치 4 설명 오류 수정' in txt and '2.9배' in txt)
    close()
    open_item('2H_QUARTERSTAFF', 'CONCUSSIVEBLOW_MULTI_1')
    txt = page.inner_text('#spellPanel')
    check('p4-quarterstaff-slow', '8%만큼 둔화' in txt and '최대 2번 중첩' in txt)
    close()
    open_item('SHOES_PLATE_UNDEAD', 'BATTLEFRENZY')
    check('p4-battlefrenzy', '6초 동안 이동 속도가 55%' in page.inner_text('#spellPanel'))
    close()
    open_item('POTION_HEAL')
    txt = page.inner_text('#detailContent')
    check('p4-heal-potion', '11월 2일 패치 4 변경' in txt and '6%' in txt)
    check('potion-price-groups', 'T4급' in txt and 'T6급' in txt and '4.2 · 6.0 효과가 같음' in txt and '게임에 없는 단계 · 5.0 · 5.1 · 7.0 · 8.0' in txt, txt[txt.find('아시아 서버 시세'):txt.find('아시아 서버 시세') + 200])
    close()


    # ------------------------------------------------------------ Patch 5 (11/26) skills, counters and robes
    def base_text(item_id, skill):
        open_item(item_id, skill)
        page.evaluate("numberMode='base';refreshNumericViews()")
        page.wait_for_timeout(120)
        t = page.inner_text('#spellPanel')
        page.evaluate("numberMode='ip';refreshNumericViews()")
        return t, page.inner_text('#detailContent')

    sp, dt5 = base_text('2H_ARCANE_RINGPAIR_AVALON', 'ARCANE_METEOR')
    cs = page.inner_text('#spellPanel .counter-section') if page.locator('#spellPanel .counter-section').count() else ''
    check('p5-dark-sphere', '11월 26일 패치 5 변경' in sp and '11.26 변경' in dt5 and all(x in sp for x in ('179', '0.9초', '25%', '25초', '155')) and '중첩됩니다' not in sp
          and '지속 피해 제거' in cs and '제어·디버프 정화' not in cs and '지속 피해 제거 효과로만' in sp, sp[:600])
    close()
    sp, _ = base_text('2H_KNUCKLES_SET1', 'KNUCKLECOMBO')
    check('p5-devastating-combo', '1.1초 동안 속박시킵니다' in sp and '12초' in sp and '기절시킵니다' not in sp and '11월 26일 패치 5 변경' in sp, sp[:500])
    close()
    sp, _ = base_text('MAIN_FROSTSTAFF', 'ICE_SCULPTURE')
    cs = page.inner_text('#spellPanel .counter-section') if page.locator('#spellPanel .counter-section').count() else ''
    check('p5-obelisk', '3초 동안 최대 200의 피해(저항력 계산 전)를 흡수하는 보호막' in sp and '마법 피해를 입힙니다' not in sp and '피해 타이밍 방어' not in cs and '버프 제거' in cs, sp[-900:])
    close()
    sp, _ = base_text('MAIN_FROSTSTAFF', 'FROSTBEAM')
    check('p5-frostbeam', '주변 5m 범위' in sp and '4m 범위' not in sp, sp[:300])
    close()
    sp, _ = base_text('2H_CROSSBOW_CANNON_AVALON', 'CROSSBOW_DIVINE_SHOT')
    check('p5-divine-engine', all(x in sp for x in ('첫 회 74', '마지막 회 138', '954', '플레이어 대상 피해의 반복 구조', '몬스터 대상 피해의 반복 구조')), sp[:900])
    close()
    sp, _ = base_text('HEAD_PLATE_SET2', 'DISRUPTIONIMMUNITY')
    check('p5-displacement', '5초 동안 강제 이동 효과와 둔화에 대한 면역' in sp and '7초에서 5초' in sp, sp[:400])
    close()
    open_item(page.evaluate("DB.find(i=>i.active.includes('PBAOE_KNOCKBACK')).id"), 'PBAOE_KNOCKBACK')
    check('p5-di-counter-text', '둔화는 패치 5부터 함께 막습니다' in page.inner_text('#spellPanel'))
    close()
    sp, _ = base_text('2H_DAGGERPAIR', 'EXECUTEDAGGER')
    cs = page.inner_text('#spellPanel .counter-section') if page.locator('#spellPanel .counter-section').count() else ''
    check('p5-slit-throat', '두 번째 슬롯 스킬의 재사용 대기 시간을 초기화' in sp and '출혈 피해:' not in sp and '지속 피해 제거' not in cs and '309' in sp, sp[:500])
    close()
    sp, dt5 = base_text('ARMOR_LEATHER_DRAGON', 'IMMUNEAREA')
    check('p5-wings-of-fire', '완전 면역' in sp and '11월 26일 패치 5 변경' in sp and '피해와 재사용 대기 시간 감소 속도가' not in sp, sp[:400])
    close()
    sp, _ = base_text('MAIN_AXE', 'AXE_CHARGE')
    check('p5-battle-rush', '가한 피해의 15%만큼 체력을 회복' in sp and '받는 회복량을' not in sp, sp[:400])
    close()
    sp, _ = base_text('2H_WILDSTAFF', 'WELLOFLIFE2')
    check('p5-well-of-life', '만드는 즉시' in sp and '345' in sp and '276' in sp, sp[:500])
    close()
    sp, _ = base_text('2H_KNUCKLES_MORGANA', 'GROWING_PUNCH')
    check('p5-earth-crusher', '0.7초' in sp and '1.4초' in sp, sp[:500])
    close()
    open_item('MAIN_NATURESTAFF', 'REJUVENATION')
    dt5 = page.inner_text('#detailContent')
    check('p5-rejuvenation-fix', '11.26 수정' in dt5 and '11월 26일 패치 5 오류 수정' in dt5)
    close()
    open_item('MAIN_HOLYSTAFF', 'HOLYFLASH')
    check('p5-holy-flash', '11m' in page.inner_text('#spellPanel') and '13m에서 11m' in page.inner_text('#spellPanel'))
    close()
    open_item('ARMOR_CLOTH_SET1')
    dt5 = page.inner_text('#detailContent')
    pos = page.evaluate("(()=>{const c=document.querySelector('#detailContent');const t=s=>{const e=c.querySelector(s);return e?e.getBoundingClientRect().top:null};return [t('.detail-heading'),t('.patch-note'),t('.detail-stats')]})()")
    check('p5-cloth-robe-note', '11월 26일 패치 5 변경' in dt5 and '회복력 관통 15%' in dt5 and all(v is not None for v in pos) and pos == sorted(pos), json.dumps(pos))
    page.screenshot(path=f'{SHOTS}/robe_detail.png')
    close()
    open_item('HEAD_CLOTH_SET1')
    check('p5-no-note-elsewhere', page.locator('#detailContent .patch-note').count() == 0)
    close()

    # ------------------------------------------------------------ weapon detail: order, jump row, price, TOP 3
    open_item('MAIN_SWORD')
    txt = page.inner_text('#detailContent')
    sword = ITEMS['MAIN_SWORD']
    st = page.inner_text('#detailContent .detail-stats')
    check('detail-stats', f"{sword['rank']}" in st and f"{sword['count']:,}" in st and '11/19–25 표본 비중' in txt and OBS in st and '패치 5 이전' in st, st[:200])
    order = page.evaluate("(()=>{const c=document.querySelector('#detailContent');const top=s=>{const e=c.querySelector(s);return e?e.getBoundingClientRect().top:null};return [top('.detail-stats'),top('.detail-jump'),top('.price-section'),top('.rank-history'),top('.co-use'),top('.skill-header')]})()")
    check('detail-order', all(v is not None for v in order) and order == sorted(order), json.dumps(order))
    check('jump-buttons', page.locator('#detailContent .detail-jump button').all_inner_texts() == ['시세', '순위 변화', '같이 쓰는 장비', '스킬'])
    c40 = sword['market']['t']['4.0']
    ps = page.inner_text('#detailContent .price-section')
    check('detail-price-section', page.locator('#detailContent .price-section .pr-row').count() == 8 and '아시아 서버 시세' in ps and '11/12–11/25 패치 5 이전 실제 거래 평균' in ps
          and f"{c40['p']:,}" in ps and ('b' not in c40 or f"{c40['b'][0]:,}" in ps) and ('o' not in c40 or f"{c40['o'][0]:,}" in ps) and MK['collectedLabel'] in ps
          and '패치 직전 24시간 동안 보인 최저가' in ps, ps[:200])
    check('detail-price-text', '최근 14일' not in txt and '2026.11.19 수집' not in txt and '시세: 2026.11.26 수집(아시아 서버, 패치 5 이전 거래)' in txt and '드래곤파이어 패치 5 반영' in txt)
    jump = {}
    for key, sel in (('price', '.price-section'), ('rank', '.rank-history'), ('co', '.co-use'), ('skills', '.skill-header')):
        page.evaluate(f"document.querySelector('#detailContent [data-jump=\"{key}\"]').click()")
        page.wait_for_timeout(900)
        jump[key] = page.evaluate(f"(()=>{{const d=document.querySelector('#detailDialog').getBoundingClientRect();const bar=document.querySelector('#detailDialog .dialog-top').getBoundingClientRect();const r=document.querySelector('#detailContent {sel}').getBoundingClientRect();return [Math.round(r.top-bar.bottom),Math.round(d.bottom-r.top)]}})()")
        if key == 'rank':
            page.screenshot(path=f'{SHOTS}/jump_rank.png')
    check('jump-scrolls', all(-2 <= v[0] <= 40 and v[1] > 100 for v in jump.values()), json.dumps(jump))
    page.evaluate("document.querySelector('#detailDialog').scrollTop=0")
    groups = page.locator('#detailContent .co-use .co-group h4').all_inner_texts()
    rows = page.locator('#detailContent .co-use li').count()
    check('co-weapon', groups == ['머리', '몸통', '신발', '보조 장비', '망토', '물약', '음식', '탈것'] and rows == 24, f'{groups} {rows}')
    co_txt = page.inner_text('#detailContent .co-use')
    top_head = sword['co']['HEAD'][0]
    check('co-values', ITEMS[top_head[0]]['ko'] in co_txt and f"{top_head[1] / sword['count'] * 100:.1f}%" in co_txt and '11/19–25 표본' in co_txt, co_txt[:200])
    first = page.locator('#detailContent .co-use li button').first
    target = first.get_attribute('data-co-open')
    first.click()
    page.wait_for_timeout(300)
    check('co-click-opens', page.evaluate('currentItem.id') == target and page.locator('#detailContent .detail-back').count() == 1, f'{target}')
    close()
    open_item('HEAD_LEATHER_SET1')
    groups = page.locator('#detailContent .co-use .co-group h4').all_inner_texts()
    check('co-armor', groups == ['무기', '몸통', '신발', '망토', '물약', '음식', '탈것'] and page.locator('#detailContent .detail-jump button').count() == 4, f'{groups}')
    close()
    open_item('2H_CLAYMORE')
    check('co-2h-no-offhand', '보조 장비' not in page.locator('#detailContent .co-use .co-group h4').all_inner_texts())
    close()

    # ------------------------------------------------------------ comparison dialog with the price row
    page.click('[data-kind="weapon"]')
    picks = page.locator('#results [data-pick]')
    picks.nth(0).click()
    picks.nth(1).click()
    page.click('#compareOpen')
    page.wait_for_selector('#compareDialog[open]')
    ct = page.inner_text('#compareContent')
    check('compare', page.locator('#compareContent .compare-cell').count() >= 10 and page.locator('#compareContent .price-vlist').count() == 2 and '시세 · 패치 5 이전 14일 거래 평균' in ct, ct[:120])
    page.screenshot(path=f'{SHOTS}/compare.png')
    page.evaluate("closeDialog('compareDialog')")
    page.evaluate("selection.slice().forEach(id=>pick(id))")
    check('compare-cleared', page.evaluate("selection.length") == 0)

    page.fill('#search', '11.26 패치 변경')
    n = page.locator('#results .item-card').count()
    check('search-patch', n > 0, f'{n} results')
    page.fill('#search', '')

    # ------------------------------------------------------------ DPS, movement, 1:1
    page.click('[data-page="dps"]')
    page.wait_for_selector('#dpsList .dps-row')
    check('dps-rows', page.locator('#dpsList .dps-row').count() == 99)
    check('dps-method-date', '수치 원본 2026.11.26(드래곤파이어 패치 5)' in page.text_content('#dpsMethod') and '2026.11.02' not in page.text_content('#dpsMethod'))
    check('dps-excluded', page.inner_text('#dpsExcludedTitle') == '정량 순위에서 제외한 Q·W 스킬 34종' and '빙하 오벨리스크' in page.text_content('#dpsExcluded'))
    page.click('[data-dps-tab="aa"]')
    check('dps-aa', page.locator('#dpsList .dps-row').count() == 136)
    page.click('[data-page="movement"]')
    page.wait_for_selector('#moveList .move-row')
    check('movement-rows', page.locator('#moveList .move-row').count() > 20)
    page.click('[data-page="pvp"]')
    page.wait_for_selector('#pvpList .pvp-row')
    check('pvp-rows', page.locator('#pvpList .pvp-row').count() > 5)
    sc = page.inner_text('#pvpScope')
    check('pvp-scope', '11/19–25 · 7일' in sc and '공식 API 수집' in sc and EV in sc and OBS in sc, sc)
    mt = page.text_content('#pvpMethod')
    exc = sum(AGG['excluded'].values())
    check('pvp-method', all(x in mt for x in (
        '공식 킬 기록 API', '확인 2,546회는 모두 성공했고, 일시적인 서버 오류 2회는 다시 받아 채웠습니다.',
        '11월 22일 0시 4분과 11월 25일 23시 58분에는 기록이 몰려 겹쳐 읽는 여유분(3분)을 각각 5초·14초 덜 읽었지만',
        '그 밖에 수집이 끊긴 구간은 없습니다.', '직전 버전(11/13–11/18)과 수집 방법·집계 기준이 같고 둘 다 패치 4 이후·패치 5 이전 표본입니다.',
        f"기간 안 고유 기록 {AGG['uniqueInWindow']:,}건 중 조건 미충족 {exc:,}건")) and '장애로 보이는 중단' not in mt and '교대가 늦어' not in mt
          and '2.2일' not in mt, mt[:500])
    for kind in ('offhand', 'cape', 'bag', 'potion', 'food', 'mount'):
        page.click(f'[data-pvp-kind="{kind}"]')
        page.wait_for_timeout(120)
        e = AGG['extras'][kind]
        s = page.inner_text('#pvpSummary')
        check(f'pvp-summary-{kind}', f"{e['equipped']:,}회" in s and f"{e['empty']:,}회" in s and f"도감 밖 {e['outsideCount']:,}회" in s, s)

    # ------------------------------------------------------------ sources
    page.click('[data-page="sources"]')
    txt = page.inner_text('#sourcesPage')
    titles = ['이전 기록 · 2026년 11월 19일 업데이트', '이전 기록 · 2026년 11월 13일 업데이트 · 종합판', '이전 기록 · 2026년 11월 5일 업데이트', '이전 기록 · 2026년 10월 30일 업데이트', '이전 기록 · 2026년 10월 25일 업데이트 · 티어별 시세',
              '이전 기록 · 2026년 10월 23일 업데이트', '이전 기록 · 2026년 10월 16일 업데이트', '이전 기록 · 2026년 10월 14일 업데이트', '이전 기록 · 2026년 10월 8일 업데이트']
    got = page.locator('#featureReview details.update-history > summary').all_inner_texts()
    check('sources-update', '2026년 11월 26일 업데이트 · 드래곤파이어 패치 5 반영' in txt and got == titles and 'Q·W 순위' in txt and page.locator('#featureQaText').count() == 1, got)
    check('sources-sample', f'아시아 · 11월 19–25일 · {EV}건 · 패치 5 이전' in txt and OBS in txt and '2026.11.26(한국 시간) 재확인' in txt and 'd277a5c' in txt
          and '표본 수집 2026.11.19–26' in page.inner_text('footer') and '수치 원본 2026.11.26' in page.inner_text('footer') and '시세 수집 2026.11.26' in page.inner_text('footer'))
    bars = page.locator('#dailyBars .day-col').all_inner_texts()
    want_bars = [f"{v:,}\n{k}" for k, v in AGG['daily'].items()]
    check('daily-bars', [b.replace('\n\n', '\n') for b in bars] == want_bars, bars)
    mp = page.inner_text('#marketPanel')
    cnt = MK['counts']
    check('market-panel', all(x in mp for x in (MK['collectedLabel'], '11월 12일–11월 25일, 14일(패치 5 이전)', f"{cnt['exists']:,}", f"{cnt['city']:,}", f"{cnt['bmOnly']:,}", f"{cnt['none']:,}",
                                                 f"{cnt['noTier']:,}", f"{cnt['noneWithOrder']:,}칸은 판매 요청서만", 'd277a5c', '날짜별 기록량', '11월 17일 이전(1주 넘게 지남)',
                                                 '패치 5 직전 24시간')), mp[:300])
    plist = page.locator('#patchList button')
    check('patch-list', plist.count() == 28 + 19 + 20 + 15, f'{plist.count()} buttons')
    pl = page.inner_text('#patchList')
    check('patch-groups', all(x in pl for x in ('드래곤파이어 패치 5 · 2026.11.26', '무기 스킬 17개 (밸런스 16 · 오류 수정 1)', '방어구 스킬 2개', '천 몸통 9종',
                                                '드래곤파이어 패치 4 · 2026.11.02 변경 19개 보기', '드래곤파이어 패치 3 · 2026.10.12 변경 20개 보기')), pl[:300])
    page.click('#patchList button:has-text("학자 로브")')
    page.wait_for_selector('#detailDialog[open]')
    check('patch-robe-click', '회복력 관통 15%' in page.inner_text('#detailContent') and page.evaluate('currentItem.id') == 'ARMOR_CLOTH_SET1')
    close()
    page.click('#patchList button:has-text("어둠의 구체")')
    page.wait_for_selector('#detailDialog[open]')
    check('patch-skill-click', page.evaluate('currentSkill') == 'ARCANE_METEOR' and '11월 26일 패치 5 변경' in page.inner_text('#spellPanel'))
    close()
    page.evaluate("document.querySelectorAll('#patchList details').forEach(d=>d.open=true)")
    page.click('#patchList button:has-text("안장을 얹은 다이어베어")')
    page.wait_for_selector('#detailDialog[open]')
    dtx = page.inner_text('#detailContent')
    check('patch-mount-click', '안장을 얹은 다이어베어' in dtx and '+85%' in dtx and '돌격' in dtx and '11월 2일 패치 4 변경' in dtx)
    close()
    page.screenshot(path=f'{SHOTS}/sources.png')
    page.click('[data-page="learn"]')
    lt = page.text_content('#learnPage')
    check('glossary', '재사용 대기 시간 감소 속도' in lt and '시세 칸 읽기' in lt and '14일 동안 실제로 거래된 평균 가격(실버)입니다(이번 판은 패치 5 이전 11월 12–25일)' in lt)

    # ------------------------------------------------------------ dark theme
    page.click('#themeBtn')
    check('dark-theme', page.evaluate("document.documentElement.dataset.theme") == 'dark')
    page.click('[data-page="catalog"]')
    page.screenshot(path=f'{SHOTS}/catalog_dark.png')
    open_item('MAIN_SWORD')
    page.screenshot(path=f'{SHOTS}/detail_dark.png')
    close()
    page.click('#themeBtn')
    ctx.close()

    # ------------------------------------------------------------ widths: no horizontal overflow anywhere, both themes
    over = {}
    for w in WIDTHS:
        c2 = browser.new_context(viewport={'width': w, 'height': 900}, device_scale_factor=1)
        pg = c2.new_page()
        watch(pg, f'w{w}')
        load(pg)
        for themed in ('light', 'dark'):
            if themed == 'dark':
                pg.click('#themeBtn')
            res = {}
            for name in ('catalog', 'dps', 'movement', 'pvp', 'learn', 'sources'):
                pg.evaluate(f"setPage('{name}')")
                pg.wait_for_timeout(250)
                if name == 'sources':
                    pg.evaluate("document.querySelectorAll('#sourcesPage details').forEach(d=>d.open=true)")
                    pg.wait_for_timeout(150)
                res[name] = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            pg.evaluate("setPage('catalog')")
            for kind in ('weapon', 'potion', 'mount'):
                pg.click(f'[data-kind="{kind}"]')
                for view in ('tableView', 'priceView', 'cardView'):
                    pg.click(f'#{view}')
                    pg.wait_for_timeout(120)
                    res[f'{kind}-{view}'] = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            for iid in ('MAIN_SWORD', 'HEAD_LEATHER_SET1', 'POTION_HEAL', 'MOUNT_HORSE', 'MEAL_SOUP', 'BAG', 'ARMOR_CLOTH_SET1', '2H_ARCANE_RINGPAIR_AVALON'):
                pg.evaluate(f"openDetail('{iid}')")
                pg.wait_for_selector('#detailDialog[open]')
                pg.wait_for_timeout(150)
                res[f'detail-{iid}'] = pg.evaluate("(()=>{const d=document.querySelector('#detailDialog');return Math.max(d.scrollWidth-d.clientWidth, Math.round(d.getBoundingClientRect().right-window.innerWidth))})()")
                pg.evaluate("closeDialog('detailDialog')")
            pg.click('[data-kind="weapon"]')
            pg.evaluate("pick('MAIN_SWORD');pick('2H_CLAYMORE');openComparison()")
            pg.wait_for_selector('#compareDialog[open]')
            res['compare'] = pg.evaluate("(()=>{const d=document.querySelector('#compareDialog');return Math.max(d.scrollWidth-d.clientWidth, Math.round(d.getBoundingClientRect().right-window.innerWidth))})()")
            pg.evaluate("closeDialog('compareDialog');selection.slice().forEach(id=>pick(id))")
            over[f'{w}-{themed}'] = {k: v for k, v in res.items() if v > 1}
        if w in (390, 360, 860):
            pg.click('#themeBtn')
            pg.evaluate("setPage('catalog')")
            pg.screenshot(path=f'{SHOTS}/w{w}_catalog.png')
            pg.evaluate("openDetail('MAIN_SWORD')")
            pg.wait_for_selector('#detailDialog[open]')
            pg.wait_for_timeout(200)
            pg.screenshot(path=f'{SHOTS}/w{w}_detail.png')
            pg.evaluate("closeDialog('detailDialog')")
        c2.close()
    check('no-overflow-all-widths', not any(over.values()), json.dumps(over))
    report['widths'] = list(WIDTHS)

    # ------------------------------------------------------------ every detail, desktop and phone
    opened = {}
    for w in (1440, 390):
        c3 = browser.new_context(viewport={'width': w, 'height': 900})
        pg = c3.new_page()
        watch(pg, f'all{w}')
        load(pg)
        res = pg.evaluate("""(()=>{const out={n:0,noPrice:[],noJump:[],noCo:[],noChart:[],overflow:[],rows:0,wrongRows:[]};
          for(const i of DB){openDetail(i.id);const c=document.querySelector('#detailContent'),d=document.querySelector('#detailDialog');out.n++;
            const ps=c.querySelector('.price-section');if(!ps)out.noPrice.push(i.id);
            const want=Object.values(i.market.t).filter(Boolean).length,got=c.querySelectorAll('.price-section .pr-row').length;out.rows+=got;if(got!==want)out.wrongRows.push([i.id,got,want]);
            if(!c.querySelector('.rank-history'))out.noChart.push(i.id);
            if(!isExtra(i)){if(c.querySelectorAll('.detail-jump button').length!==4)out.noJump.push(i.id);if(!c.querySelector('.co-use'))out.noCo.push(i.id)}
            if(d.scrollWidth-d.clientWidth>1)out.overflow.push([i.id,d.scrollWidth-d.clientWidth]);
            closeDialog('detailDialog')}
          return out})()""")
        opened[w] = res
        c3.close()
    ok = all(r['n'] == 342 and not r['noPrice'] and not r['noJump'] and not r['noCo'] and not r['noChart'] and not r['overflow'] and not r['wrongRows'] and r['rows'] == MK['counts']['exists'] for r in opened.values())
    check('all-342-details', ok, json.dumps({w: {k: (v if not isinstance(v, list) else v[:5]) for k, v in r.items()} for w, r in opened.items()}))
    report['detailsOpened'] = opened[1440]['n']
    browser.close()

check('no-script-errors', not report['errors'], '; '.join(report['errors'][:5]))
report['scriptErrors'] = len(report['errors'])
print(json.dumps(report, ensure_ascii=False, indent=1))
if REPORT:
    json.dump(report, open(REPORT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
sys.exit(1 if report['fail'] else 0)
