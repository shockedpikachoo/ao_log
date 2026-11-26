"""Static checks of the built guide: stale strings, external references, script safety, data block integrity.

Usage: python3 -I final_checks.py <built html> <previous html> [--final]
"""
import json, re, sys

NEW, PREV = sys.argv[1:3]
FINAL = '--final' in sys.argv
ALLOWED_NEW_URLS = {'https://steamcommunity.com/games/761890/announcements/detail/1850460852984814',
                    'https://github.com/ao-data/ao-bin-dumps/tree/d277a5cf8a76535f1dccadbf35b36350ae2665aa',
                    'https://github.com/ao-data/ao-bin-dumps/blob/d277a5cf8a76535f1dccadbf35b36350ae2665aa/gamedata.xml',
                    'https://github.com/ao-data/ao-bin-dumps/blob/d277a5cf8a76535f1dccadbf35b36350ae2665aa/spells.xml'}
ALLOWED_GONE_URLS = {'https://steamcommunity.com/games/761890/announcements/detail/1847920302247585',
                     'https://github.com/ao-data/ao-bin-dumps/tree/0483dd97f1581dfaf02eed42f25f5ea2a3cb75e5',
                     'https://github.com/ao-data/ao-bin-dumps/blob/0483dd97f1581dfaf02eed42f25f5ea2a3cb75e5/gamedata.xml',
                     'https://github.com/ao-data/ao-bin-dumps/blob/0483dd97f1581dfaf02eed42f25f5ea2a3cb75e5/spells.xml'}
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
for pat in ('2026.11.19 수집', '11/6–11/19', '11월 6일–11월 19일', '11월 13–18일', '11/13–18', '145,612', '231,269', '158,463', '17:42', '7번째', '네 버전', '395칸',
            '11월 11일 이전', '2026.11.13–18', '11.13–19', '6-DAY', '0.14%', '2026.11.02 게임 데이터', '최신 커밋은 2026.11.02 추출본', '수치 원본 2026.11.02',
            '패치 4 반영: 2026.11.05', '11월 2일 드래곤파이어 패치 4 반영', '원본 2026.11.02(패치 4', '2026.11.02 업데이트(드래곤파이어 패치 4', '수치 재대조: 2026.11.13',
            '최근 11일', '11월 17일 0시 31–39분', '+0.3%', '+145%', '612개'):
    for part, name in ((cur, 'current notes/hero'), (after, 'panels/footer'), (J, 'script')):
        if pat in part:
            problems.append(f'{name}: stale {pat!r}: …{part[max(0, part.index(pat) - 60):part.index(pat) + 40]}…')
if '최근 14일' in J:
    problems.append('script: 최근 14일 left (this version shows 패치 5 이전 14일)')
for pat, n in (('패치 5 이전 14일', 9),):
    if J.count(pat) != n:
        problems.append(f'script: {pat!r} {J.count(pat)}x (expected {n})')
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
    for pat in ('11/13–18', '11월 13–18일', '11월 2일 게임 데이터', '10월 12일 게임 데이터', '최근 11일', '2026.11.19', '2026.11.13'):
        if pat == '2026.11.19' and path in ('.meta.period', '.meta.periodKstLabel'):
            continue                     # the new sample starts on 11/19
        if pat in s:
            problems.append(f'data string {path}: {pat!r} in {s[:120]!r}')

# 3. external references
urls = lambda s: set(re.findall(r'https?://[^\s"\'<>)\\]+', s))
new_urls = urls(H + J) - urls(H0 + J0)
if new_urls - ALLOWED_NEW_URLS:
    problems.append(f'new URLs: {sorted(new_urls - ALLOWED_NEW_URLS)}')
gone = urls(H0 + J0) - urls(H + J) - ALLOWED_GONE_URLS
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
