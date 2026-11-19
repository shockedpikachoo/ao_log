"""Fetch an Asia-server market snapshot from the Albion Online Data Project for a list of item IDs.

Usage: python3 fetch_market.py <ids.json> <out dir> <first M-D-YYYY> <end M-D-YYYY>

Writes, in <out dir>:
  hist_NNN.json.gz    {"ids": [...], "rows": [...]}  stats/history (daily, time-scale 24), 7 cities + Black Market, qualities 1-5
  orders_NNN.json.gz  {"ids": [...], "rows": [...]}  stats/prices (current orders), 7 cities, qualities 1-3
  manifest_hist.json / manifest_orders.json  {host, query, started, finished, files: [{file, ids, rows}]}
One request every 2 seconds; a batch is retried up to 5 times; the run stops (exit 1) if a batch keeps failing,
so a snapshot on disk is always complete. The User-Agent is generic and carries no personal data.
"""
import gzip, json, os, sys, time, urllib.parse, urllib.request
import datetime as dt

IDS, OUT, FIRST, END = sys.argv[1:5]
HOST = 'https://east.albion-online-data.com'
CITIES = ['Bridgewatch', 'Fort Sterling', 'Lymhurst', 'Martlock', 'Thetford', 'Caerleon', 'Brecilien']
UA = 'albion-guide-price-snapshot/1.0 (static guide page; one request every 2 s)'
MAX_IDS_CHARS = 2900
os.makedirs(OUT, exist_ok=True)
ids = json.load(open(IDS, encoding='utf-8'))
assert len(ids) == len(set(ids)), 'duplicate IDs'

batches, cur = [], []
for i in ids:
    if cur and len(','.join(cur + [i])) > MAX_IDS_CHARS:
        batches.append(cur)
        cur = []
    cur.append(i)
if cur:
    batches.append(cur)

now = lambda: dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
last_call = [0.0]


def get(url):
    for attempt in range(5):
        wait = 2.0 - (time.time() - last_call[0])
        if wait > 0:
            time.sleep(wait)
        last_call[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=90) as r:
                body = r.read()
            return json.loads(body)
        except Exception as e:  # noqa: BLE001 - report and retry
            print(f'  retry {attempt + 1}: {type(e).__name__}: {str(e)[:120]}', flush=True)
            time.sleep(5 * (attempt + 1))
    sys.exit(f'giving up on {url[:160]}')


def run(kind, path, query):
    started = now()
    files = []
    for n, b in enumerate(batches):
        url = f"{HOST}/api/v2/stats/{path}/{urllib.parse.quote(','.join(b), safe=',@_')}.json?{urllib.parse.urlencode(query, safe=',')}"
        assert len(url) < 4000, len(url)
        rows = get(url)
        assert isinstance(rows, list), type(rows)
        name = f'{kind}_{n:03d}.json.gz'
        with gzip.open(os.path.join(OUT, name), 'wt', encoding='utf-8') as fh:
            json.dump({'ids': b, 'rows': rows}, fh, ensure_ascii=False)
        files.append({'file': name, 'ids': len(b), 'rows': len(rows)})
        print(f'{kind} {n + 1}/{len(batches)}: {len(b)} ids, {len(rows)} rows', flush=True)
    man = {'host': HOST, 'path': path, 'query': query, 'started': started, 'finished': now(), 'files': files,
           'idsTotal': sum(f['ids'] for f in files)}
    json.dump(man, open(os.path.join(OUT, f'manifest_{kind}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return man


h = run('hist', 'history', {'date': FIRST, 'end_date': END, 'locations': ','.join(CITIES + ['Black Market']),
                            'qualities': '1,2,3,4,5', 'time-scale': '24'})
o = run('orders', 'prices', {'locations': ','.join(CITIES), 'qualities': '1,2,3'})
print('history', h['started'], h['finished'], '| orders', o['started'], o['finished'], '| batches', len(batches), '| ids', len(ids))
