#!/usr/bin/env python3
"""Delete stored events that a guide update has already used.

Usage: python3 tools/prune.py <cutoff KST 'YYYY-MM-DDTHH:MM'> [--dry-run]

data/  every event older than the cutoff is removed. Files with only older events are deleted;
       files that straddle the cutoff keep their newer lines unchanged. The collector writes each
       data file once and never changes it, so this is safe while a collection run is active.
logs/  a run's log file is deleted when the run has finished (an "end" entry, or no entry for
       longer than any run can last) and all its entries are older than the cutoff. An active run
       appends to its log file, and changing that file would make the run's next push conflict,
       so those files are never touched.
Empty date folders are removed. Commit the result yourself:
       git add -A data logs && git commit -m "data: prune events used for the guide" && git push
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KST = dt.timezone(dt.timedelta(hours=9))
RUN_MAX = dt.timedelta(hours=6.5)   # collect.yml stops a job after 358 minutes


def parse(ts):
    return dt.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('cutoff', help="KST 'YYYY-MM-DDTHH:MM'; events before it are removed")
    ap.add_argument('--dry-run', action='store_true', help='only report what would change')
    a = ap.parse_args()
    cut = dt.datetime.strptime(a.cutoff, '%Y-%m-%dT%H:%M').replace(tzinfo=KST).astimezone(dt.timezone.utc)
    cut_s = cut.strftime('%Y-%m-%dT%H:%M:%SZ')
    now = dt.datetime.now(dt.timezone.utc)
    if cut > now:
        sys.exit('the cutoff is in the future')
    act = not a.dry_run
    print(f'cutoff {a.cutoff} KST = {cut_s}' + ('  (dry run)' if a.dry_run else ''))

    # ------------------------------------------------------------------ data
    kept = removed = unreadable = 0
    deleted = trimmed = 0
    oldest_kept = None
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', '*', '*.jsonl'))):
        with open(f, encoding='utf-8', newline='') as fh:
            lines = fh.readlines()
        keep = []
        for line in lines:
            try:
                t = json.loads(line)['t']
            except (ValueError, KeyError):
                unreadable += 1          # keep what cannot be read; aggregate.py will report it
                keep.append(line)
                continue
            if t >= cut_s:
                keep.append(line)
                oldest_kept = t if oldest_kept is None or t < oldest_kept else oldest_kept
        kept += len(keep)
        removed += len(lines) - len(keep)
        if len(keep) == len(lines):
            continue
        if keep:
            trimmed += 1
            print(f'  trim {os.path.relpath(f, ROOT)}: -{len(lines) - len(keep)} / keep {len(keep)}')
            if act:
                with open(f, 'w', encoding='utf-8', newline='') as fh:
                    fh.writelines(keep)
        else:
            deleted += 1
            if act:
                os.remove(f)
    print(f'data: {removed} events removed, {kept} kept (oldest kept {oldest_kept}); '
          f'{deleted} files deleted, {trimmed} trimmed' + (f'; {unreadable} unreadable lines kept' if unreadable else ''))

    # ------------------------------------------------------------------ logs
    gone = 0
    for f in sorted(glob.glob(os.path.join(ROOT, 'logs', '*', '*.jsonl'))):
        entries = []
        with open(f, encoding='utf-8') as fh:
            for line in fh:
                try:
                    entries.append(json.loads(line))
                except ValueError:
                    pass
        last = max((x.get('at', '') for x in entries), default='')
        finished = any(x.get('end') for x in entries) or (last and parse(last) < now - RUN_MAX)
        if finished and last < cut_s:
            gone += 1
            if act:
                os.remove(f)
        else:
            why = 'run still active' if not finished else 'has entries after the cutoff'
            print(f'  keep {os.path.relpath(f, ROOT)} ({why}, last entry {last})')
    print(f'logs: {gone} files deleted')

    # ------------------------------------------------------------------ empty folders
    if act:
        for d in glob.glob(os.path.join(ROOT, 'data', '*')) + glob.glob(os.path.join(ROOT, 'logs', '*')):
            if os.path.isdir(d) and not os.listdir(d):
                os.rmdir(d)


if __name__ == '__main__':
    main()
