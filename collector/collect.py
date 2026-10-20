#!/usr/bin/env python3
"""Archive Asia-server kill events from the official Albion Online gameinfo API.

Runs inside GitHub Actions (.github/workflows/collect.yml). One run polls for up to --minutes
minutes and then exits; the next hourly run (queued behind it) continues, so collection is
continuous. New events are written every few minutes to data/<UTC date>/<UTC time>-<run>.jsonl
and pushed as a commit, so a stopped run loses at most one interval.

What is stored (no player names, guild names or player IDs):
  every event   {"i": EventId, "t": time (UTC, seconds), "n": numberOfParticipants,
                 "g": groupMemberCount}
  solo kills    (n == 1 and g == 1) additionally
                {"ty": Type, "a": KillArea,
                 "pk": the participant list is exactly the killer,
                 "gk": the group list is empty or exactly the killer,
                 "ki"/"vi": average item power of killer / victim,
                 "ke"/"ve": equipment Type per slot, in SLOTS order (null = empty slot)}
Per-poll coverage (pages read, new events, time range, gap flag) goes to logs/<UTC date>/<run>.jsonl.

The API returns the newest events first, at most 51 per page and offset <= 1000 (about 1,050
events, i.e. 20-50 minutes of Asia traffic). Each poll pages back until it overlaps what the
previous poll (or the stored data) already covered, minus a safety margin for late events.
"""
import argparse
import datetime as dt
import glob
import json
import os
import random
import subprocess
import sys
import time
import urllib.error
import urllib.request

SLOTS = ('MainHand', 'OffHand', 'Head', 'Armor', 'Shoes', 'Bag', 'Cape', 'Mount', 'Potion', 'Food')
API = 'https://gameinfo-{server}.albiononline.com/api/gameinfo/events?limit=51&offset={off}&_={bust}'
UA = 'ao_log/1.0 (+https://github.com/shockedpikachoo/ao_log; personal equipment statistics)'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_OFFSET = 1000


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


def stamp(t):
    return t.strftime('%Y-%m-%dT%H:%M:%SZ')


def sec(ts):
    """API timestamps carry 3-7 fractional digits; compare them at whole seconds."""
    return ts[:19] + 'Z'


def shift(ts, seconds):
    t = dt.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)
    return stamp(t + dt.timedelta(seconds=seconds))


class Collector:
    def __init__(self, cfg, run_id, use_git):
        self.cfg = cfg
        self.run = run_id
        self.git = use_git
        self.events = []
        self.logs = []
        self.seen = set()
        self.newest = None          # newest event time (whole seconds) already covered
        self.load_recent()

    # ------------------------------------------------------------------ state
    def load_recent(self):
        """Event IDs and newest time from the last two UTC dates of stored data."""
        days = sorted(glob.glob(os.path.join(ROOT, 'data', '20??-??-??')))[-2:]
        for day in days:
            for fn in glob.glob(os.path.join(day, '*.jsonl')):
                with open(fn, encoding='utf-8') as f:
                    for line in f:
                        try:
                            r = json.loads(line)
                        except ValueError:
                            continue
                        self.seen.add(r['i'])
                        if self.newest is None or r['t'] > self.newest:
                            self.newest = r['t']
        self.log({'start': True, 'run': self.run, 'knownEvents': len(self.seen), 'storedNewest': self.newest})

    def log(self, entry):
        entry = {'at': stamp(utcnow()), **entry}
        self.logs.append(entry)
        print(json.dumps(entry, ensure_ascii=False), flush=True)

    # ------------------------------------------------------------------ API
    def fetch(self, off):
        url = API.format(server=self.cfg['server'], off=off, bust=random.randrange(10 ** 12))
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.loads(r.read().decode('utf-8'))
                if isinstance(data, list):
                    return data
                self.log({'warn': 'unexpected body', 'off': off, 'body': str(data)[:200]})
            except Exception as e:  # noqa: BLE001 - URLError, IncompleteRead, timeouts, bad JSON: all retried
                self.log({'warn': 'fetch failed', 'off': off, 'attempt': attempt, 'error': f'{type(e).__name__}: {e}'[:200]})
            time.sleep(10 + 20 * attempt)
        return None

    @staticmethod
    def record(e):
        n, g = e.get('numberOfParticipants'), e.get('groupMemberCount')
        r = {'i': e['EventId'], 't': sec(e['TimeStamp']), 'n': n, 'g': g}
        if n == 1 and g == 1:
            k, v = e.get('Killer') or {}, e.get('Victim') or {}
            parts = [p.get('Id') for p in (e.get('Participants') or [])]
            group = [p.get('Id') for p in (e.get('GroupMembers') or [])]

            def gear(p):
                eq = p.get('Equipment') or {}
                return [(eq.get(s) or {}).get('Type') for s in SLOTS]

            r.update({'ty': e.get('Type'), 'a': e.get('KillArea'),
                      'pk': parts == [k.get('Id')], 'gk': (not group) or group == [k.get('Id')],
                      'ki': round(k.get('AverageItemPower') or 0, 1), 'vi': round(v.get('AverageItemPower') or 0, 1),
                      'ke': gear(k), 've': gear(v)})
        return r

    def poll(self):
        """Read pages until they overlap the covered range.

        A poll that fails part-way does not move the covered range forward, so the next poll reads
        the same stretch again. Only when all offsets are used up without reaching the covered range
        is a real gap recorded ("gap": true) and accepted.
        """
        target = shift(self.newest, -self.cfg['overlapSeconds']) if self.newest else None
        pages = new = solo = 0
        oldest = newest = None
        reached = failed = False
        off = 0
        while True:
            page = self.fetch(off)
            pages += 1
            if page is None:
                failed = True
                break
            if not page:
                reached = True
                break
            for e in page:
                ts = sec(e['TimeStamp'])
                oldest = ts if oldest is None or ts < oldest else oldest
                newest = ts if newest is None or ts > newest else newest
                if e['EventId'] in self.seen:
                    continue
                self.seen.add(e['EventId'])
                r = self.record(e)
                self.events.append(r)
                new += 1
                solo += 'ke' in r
            if target and oldest and oldest <= target and pages >= 2:
                reached = True
                break
            if off >= MAX_OFFSET:
                break
            off = min(off + 51, MAX_OFFSET)
            time.sleep(self.cfg['pageDelaySeconds'])
        gap = bool(target) and not reached and not failed
        self.log({'pages': pages, 'new': new, 'newSolo': solo, 'oldest': oldest, 'newest': newest,
                  'coveredFrom': target, 'gap': gap, 'failed': failed})
        if not failed and newest and (self.newest is None or newest > self.newest):
            self.newest = newest
        return not (gap or failed)

    # ------------------------------------------------------------------ storage
    def flush(self, final=False):
        if not self.events and not self.logs:
            return
        t = utcnow()
        n_new, n_solo = len(self.events), sum('ke' in r for r in self.events)
        if self.events:
            path = os.path.join(ROOT, 'data', t.strftime('%Y-%m-%d'), f'{t:%H%M%S}-{self.run}.jsonl')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                for r in sorted(self.events, key=lambda r: r['i']):
                    f.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n')
        logpath = os.path.join(ROOT, 'logs', t.strftime('%Y-%m-%d'), f'{self.run}.jsonl')
        os.makedirs(os.path.dirname(logpath), exist_ok=True)
        with open(logpath, 'a', encoding='utf-8') as f:
            for entry in self.logs:
                f.write(json.dumps(entry, ensure_ascii=False, separators=(',', ':')) + '\n')
        self.events, self.logs = [], []
        if self.git:
            msg = f'data: +{n_new} events ({n_solo} solo) up to {self.newest}' + (' [run end]' if final else '')
            self.commit(msg)

    def commit(self, msg):
        def git(*args, check=True):
            return subprocess.run(['git', '-C', ROOT, *args], check=check, capture_output=True, text=True)
        git('add', 'data', 'logs')
        if not git('diff', '--cached', '--quiet', check=False).returncode:
            return
        git('commit', '-q', '-m', msg)
        for attempt in range(4):
            if not git('push', '-q', check=False).returncode:
                return
            time.sleep(5 + 10 * attempt)
            git('pull', '-q', '--rebase', check=False)
        print('push failed; the data stays committed locally and is retried next flush', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--minutes', type=float, default=345, help='stop after this many minutes')
    ap.add_argument('--polls', type=int, default=0, help='stop after this many polls (0 = no limit)')
    ap.add_argument('--no-git', action='store_true', help='write files but do not commit or push')
    a = ap.parse_args()
    with open(os.path.join(ROOT, 'collector', 'config.json'), encoding='utf-8') as f:
        cfg = json.load(f)
    start = utcnow()
    stop_at = dt.datetime.fromisoformat(cfg['stopAt'])
    if start >= stop_at:
        print(f'collection window ended at {cfg["stopAt"]}; nothing to do')
        return
    deadline = min(start + dt.timedelta(minutes=a.minutes), stop_at)
    c = Collector(cfg, os.environ.get('GITHUB_RUN_ID', 'local'), not a.no_git)
    last_flush, polls = time.time(), 0
    try:
        while utcnow() < deadline:
            t0 = time.time()
            try:
                c.poll()
            except Exception as e:  # noqa: BLE001 - keep collecting; the next poll re-reads the same range
                c.log({'warn': 'poll crashed', 'error': f'{type(e).__name__}: {e}'[:200]})
            polls += 1
            if a.polls and polls >= a.polls:
                break
            if time.time() - last_flush >= cfg['commitMinutes'] * 60:
                c.flush()
                last_flush = time.time()
            wait = max(30.0, cfg['pollSeconds'] - (time.time() - t0))
            if utcnow() + dt.timedelta(seconds=wait) >= deadline:
                break
            time.sleep(wait)
    finally:
        c.log({'end': True, 'polls': polls})
        c.flush(final=True)


if __name__ == '__main__':
    main()
