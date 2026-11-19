"""Static checks of the built guide: stale strings, external references, script safety, data block integrity.

Usage: python3 -I final_checks.py <built html> <previous html> [--final]
"""
import json, re, sys

NEW, PREV = sys.argv[1:3]
FINAL = '--final' in sys.argv
ALLOWED_NEW_URLS = {'https://steamcommunity.com/games/761890/announcements/detail/1849458702693040'}
problems = []


def split(path):
    html = open(path, encoding='utf-8').read()
    tag = '<script id="guideData" type="application/json">'
    a = html.index(tag) + len(tag)
    b = html.index('</script>', a)
    return html, html[:a], html[a:b], html[b:]


html, H, D, J = split(NEW)
html0, H0, D0, J0 = split(PREV)
data, data0 = json.loads(D), json.loads(D0)
body = H[H.index('<body'):]
cur = body[:body.index('<details class="update-history">')]          # everything before the older update records
rest = body[body.index('<details class="update-history">'):]
hist_end = rest.index('</section>')
after = rest[hist_end:]                                                # market panel, method grid, sources, footer

# 1. data block
if '</' in D or '<!--' in D:
    problems.append('data block contains a sequence that could end the script element')
if html.count('<script id="guideData"') != 1 or len(data['items']) != 342 or len(data['spells']) != 476 or list(data) != list(data0):
    problems.append('data block shape')

# 2. strings of the previous version that must be gone from the current parts (history records may keep them)
for pat in ('최근 11일', '2026.11.13 수집', '11/2–11/12', '11월 5–12일', '11/5–12', '186,130', '294,194', '08:27', '6번째', '세 버전', '1,421', '303칸', '11월 4일 이전',
            '2026.11.05–12', '11.05–13', '8-DAY', '종합판10월', '504 오류', '15:09–16:49'):
    for part, name in ((cur, 'current notes/hero'), (after, 'panels/footer'), (J, 'script')):
        if pat in part:
            problems.append(f'{name}: stale {pat!r}: …{part[max(0, part.index(pat) - 60):part.index(pat) + 40]}…')
for pat, n in (('(검증 문장은 점검을 마친 뒤 채웁니다.)', 0 if FINAL else 1), ('id="featureQaText"', 1), ('id="marketPanel"', 1), ('id="featureReview"', 1)):
    if html.count(pat) != n:
        problems.append(f'{pat!r} appears {html.count(pat)}× (expected {n})')
for pat in ('undefined', 'NaN', '[object Object]'):
    if pat in body:
        problems.append(f'{pat} in the page text')


def walk(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f'{path}.{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f'{path}[{i}]')
    elif isinstance(o, str):
        yield path, o


for path, s in walk({k: v for k, v in data.items() if k != 'images'}):
    if path.startswith(('.meta.rankHistory', '.meta.review', '.meta.market.previous', '.meta.pvpExtras.previous', '.meta.patch', '.meta.update')):
        continue
    for pat in ('11/5–12', '11월 5–12일', '2.2일', '10월 12일 게임 데이터', '최근 11일', '2026.11.13'):
        if pat == '2026.11.13' and path in ('.meta.period', '.meta.periodKstLabel', '.meta.numericCheckedDate'):
            continue                     # the new sample starts on 11/13; numbers were last re-compared on 11/13
        if pat in s:
            problems.append(f'data string {path}: {pat!r} in {s[:120]!r}')

# 3. external references
urls = lambda s: set(re.findall(r'https?://[^\s"\'<>)\\]+', s))
new_urls = urls(H + J) - urls(H0 + J0)
if new_urls - ALLOWED_NEW_URLS:
    problems.append(f'new URLs: {sorted(new_urls - ALLOWED_NEW_URLS)}')
gone = urls(H0 + J0) - urls(H + J)
if gone:
    problems.append(f'URLs that disappeared: {sorted(gone)}')

# 4. script safety: no network or dynamic-code calls beyond what the previous page had
for tok in ('fetch(', 'XMLHttpRequest', 'WebSocket', 'eval(', 'new Function', 'import(', 'sendBeacon', 'document.cookie', 'postMessage'):
    if (J + H).count(tok) != (J0 + H0).count(tok):
        problems.append(f'{tok} count changed')
if len(re.findall(r'<script\b', html)) != len(re.findall(r'<script\b', html0)):
    problems.append('number of script blocks changed')

# 5. nothing personal
low = html.lower()
# words that must never appear in the page (account names, repository address ...): comma-separated in GUIDE_PRIVATE_TOKENS
import os
for tok in [t.strip().lower() for t in os.environ.get('GUIDE_PRIVATE_TOKENS', '').split(',') if t.strip()] + ['ao_log', '@gmail']:
    if tok in low:
        problems.append(f'personal token in page: {tok}')
mail = re.search(r'[\w.+-]+@[\w-]+\.[a-z]{2,}', H + J)
if mail:
    problems.append('an e-mail address appears in the page: ' + mail.group(0))

# 6. functions the page needs are defined once
for fn in ('priceSection', 'priceMini', 'priceList', 'priceTable', 'sortByPrice', 'coUsage', 'detailJump', 'extraSampleNote', 'detailStats', 'openDetail', 'openComparison'):
    n = len(re.findall(r'function ' + fn + r'\(', J)) + len(re.findall(r'(?:const|let)\s+' + fn + r'\s*=', J))
    if n != 1:
        problems.append(f'{fn} defined {n}×')
report = {'bytes': len(html.encode('utf-8')), 'newUrls': sorted(new_urls), 'problems': problems}
print(json.dumps(report, ensure_ascii=False, indent=1))
sys.exit(1 if problems else 0)
