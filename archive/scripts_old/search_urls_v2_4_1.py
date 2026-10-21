"""Find landing URLs for included v2.4.1 studies missing both DOI and URL.

Run from the repository: python docs/dex_hff/search_urls_v2_4_1.py
Requires pandas; HTTP uses Python's standard library. Searches only titles in
OpenAlex (five results), caches every HTTP response, and resumes successful
lookups. No CrossRef queries or dataset edits. Normalized SequenceMatcher ratio
must be >= .95 and publication year within +/-1; equal best scores for distinct
works are ambiguous. URL preference: primary landing, other landing, PMID, DOI.
Information-only found_doi never updates the dataset. Sample: pandas random_state
20261013, 50 accepted rows, one HEAD request per URL with a 20-second timeout.
Use --retry-errors to retry cached terminal errors; --workers controls concurrency.
An optional authorized key can be read with --api-key-env VARIABLE_NAME or
--api-key-file PATH (the file must be inside this repository). Keys are not logged.
Add --daily-resume to wait until the next midnight UTC (plus 60 seconds), then
resume daily until budget exhaustion no longer occurs. Keep the process alive;
restart with the same command after a reboot. Each day refreshes the reports.
All artifacts stay in the existing git-ignored docs/dex_hff tree.
"""
import argparse
import concurrent.futures as cf
import difflib
from datetime import datetime, timedelta, timezone
import hashlib
import html
import json
import os
import re
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/dex_hff/v2_4_1/hff_analysis_dataset_v2_4_1_included.csv'
OUT = DATA.parent / 'url_search'
COLUMNS = ['record_id','title','year','match_title','match_year','similarity',
           'openalex_id','url','url_source','found_doi','decision']
MISSING = {'', 'na', 'could not find', 'none', 'nan'}
LOCK = threading.Lock()
NEXT = 0.0
EXHAUSTED = threading.Event()
API_KEY = ''

def missing(value):
    return str(value).strip().lower() in MISSING

def normalize(value):
    value = html.unescape(re.sub(r'<[^>]*>', ' ', str(value))).lower()
    value = ''.join(c if not unicodedata.category(c).startswith('P') else ' ' for c in value)
    return ' '.join(value.split())

def doi_key(value):
    if missing(value):
        return ''
    return re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', str(value).strip(), flags=re.I).lower()

def atomic_json(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    tmp.replace(path)

def throttle():
    global NEXT
    with LOCK:
        now = time.monotonic()
        if NEXT > now:
            time.sleep(NEXT - now)
        NEXT = time.monotonic() + 0.125

def lookup(title, retry_errors):
    key = hashlib.sha256(title.encode('utf-8')).hexdigest()
    folder = OUT / 'cache' / key[:2]
    folder.mkdir(parents=True, exist_ok=True)
    final = folder / (key + '.json')
    if final.exists():
        cached = json.loads(final.read_text(encoding='utf-8'))
        if not cached.get('error') or (not retry_errors and not cached.get('budget_exhausted')):
            return cached
    if EXHAUSTED.is_set():
        return {'error':'Not attempted: daily API budget exhausted', 'unattempted':True}
    # OpenAlex interprets literal ? and * as wildcards and rejects stemmed
    # searches containing them. Remove these punctuation marks from the query
    # only; matching always uses the original, fully normalized study title.
    query_title = title.replace('?', ' ').replace('*', ' ')
    params = {'search':query_title, 'per-page':5}
    url = 'https://api.openalex.org/works?' + urllib.parse.urlencode(params)
    for attempt in range(7):
        if EXHAUSTED.is_set():
            return {'error':'Not attempted: daily API budget exhausted', 'unattempted':True}
        throttle()
        status, body, error = None, '', ''
        try:
            headers = {'User-Agent':'HFF-URL-evidence-search/1.0'}
            if API_KEY:
                headers['Authorization'] = 'Bearer ' + API_KEY
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as response:
                status = response.status
                body = response.read().decode('utf-8')
            payload = json.loads(body)
            if not isinstance(payload.get('results'), list):
                raise ValueError('Missing results list')
            result = {'status':status, 'response':payload}
        except urllib.error.HTTPError as exc:
            status = exc.code
            body = exc.read().decode('utf-8', errors='replace')
            # HTTPError text contains the request URL, potentially including a
            # key. Never persist that URL or the key in caches/logs.
            error = f'HTTP {status}: {exc.reason}'
            result = {'status':status, 'error':error}
        except Exception as exc:
            error = str(exc)
            result = {'status':status, 'error':error}
        stamp = time.time_ns()
        atomic_json(folder / f'{key}.attempt-{stamp}.json', {'status':status,'body':body,'error':error})
        if status == 429 and ('Insufficient budget' in body or 'dailyRemainingUsd":0' in body):
            EXHAUSTED.set()
            result['budget_exhausted'] = True
            atomic_json(final, result)
            return result
        if not error:
            atomic_json(final, result)
            return result
        if status is not None and status != 429 and status < 500:
            break
        if attempt < 6:
            time.sleep(min(60, 2 ** (attempt + 1)))
    atomic_json(final, result)
    return result

def choose_url(work):
    value = (work.get('primary_location') or {}).get('landing_page_url')
    if value and not missing(value):
        return value, 'primary_location.landing_page_url'
    for location in work.get('locations') or []:
        value = location.get('landing_page_url')
        if value and not missing(value):
            return value, 'locations.landing_page_url'
    value = (work.get('ids') or {}).get('pmid')
    if value and not missing(value):
        pmid = str(value).rstrip('/').split('/')[-1]
        return f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/', 'ids.pmid'
    value = work.get('doi')
    if value and not missing(value):
        return 'https://doi.org/' + doi_key(value), 'doi'
    return '', ''

def match(row, response):
    result = {c:'' for c in COLUMNS}
    result.update({k:row[k] for k in ['record_id','title','year']})
    if response.get('error'):
        result['decision'] = 'error'
        return result
    candidates = []
    for work in response['response']['results'][:5]:
        score = difflib.SequenceMatcher(None, normalize(row['title']), normalize(work.get('title') or ''), autojunk=False).ratio()
        try:
            year_ok = abs(float(row['year']) - float(work['publication_year'])) <= 1
        except (ValueError, TypeError, KeyError):
            year_ok = False
        candidates.append((score, year_ok, work))
    if not candidates:
        result['decision'] = 'no_match'
        return result
    candidates.sort(key=lambda c:c[0], reverse=True)
    passing = [c for c in candidates if c[0] >= .95 and c[1]]
    best = passing[0] if passing else candidates[0]
    score, _, work = best
    result.update(match_title=work.get('title') or '', match_year=work.get('publication_year'), similarity=score,
                  openalex_id=work.get('id') or '', found_doi=work.get('doi') or '')
    if not passing:
        result['decision'] = 'year_mismatch' if any(c[0] >= .95 for c in candidates) else 'below_threshold'
    elif len({c[2].get('id') for c in passing if c[0] == score}) > 1:
        result['decision'] = 'ambiguous'
    else:
        result['url'], result['url_source'] = choose_url(work)
        result['decision'] = 'accepted' if result['url'] else 'no_match'
    return result

def check_url(row):
    key = hashlib.sha256((str(row['record_id']) + '\0' + row['url']).encode()).hexdigest()
    path = OUT / 'sample_cache' / (key + '.json')
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    result = dict(row)
    result.update(http_status='', http_error='', final_url='', http_method='HEAD')
    try:
        req = urllib.request.Request(row['url'], method='HEAD', headers={'User-Agent':'HFF-URL-evidence-search/1.0'})
        with urllib.request.urlopen(req, timeout=20) as response:
            result.update(http_status=response.status, final_url=response.url)
    except urllib.error.HTTPError as exc:
        result.update(http_status=exc.code, http_error=str(exc), final_url=exc.url)
    except Exception as exc:
        result['http_error'] = str(exc)
    atomic_json(path, result)
    return result

def main():
    global API_KEY
    EXHAUSTED.clear()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retry-errors', action='store_true')
    parser.add_argument('--workers', type=int, default=24)
    parser.add_argument('--daily-resume', action='store_true', help='Wait for next UTC budget reset, then resume daily while budgets exhaust')
    parser.add_argument('--api-key-env', help='Name of environment variable containing an optional authorized API key')
    parser.add_argument('--api-key-file', type=Path, help='Repository-local text file containing an optional authorized API key')
    args = parser.parse_args()
    if args.api_key_env and args.api_key_file:
        parser.error('Use only one API key source')
    if args.api_key_env:
        API_KEY = os.environ.get(args.api_key_env, '')
        if not API_KEY:
            parser.error('The specified API key environment variable is empty')
    if args.api_key_file:
        path = args.api_key_file.resolve()
        if not path.is_relative_to(ROOT):
            parser.error('API key file must be inside this repository')
        API_KEY = path.read_text(encoding='utf-8-sig').strip()
        if not API_KEY:
            parser.error('The specified API key file is empty')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'sample_cache').mkdir(exist_ok=True)
    data = pd.read_csv(DATA, dtype=str, keep_default_na=False)
    selected = data[data.doi.map(missing) & data.url.map(missing)]
    rows = selected[['record_id','title','year']].to_dict('records')
    # One lookup per exact title; identical-title records share its response.
    groups = defaultdict(list)
    for row in rows:
        groups[row['title']].append(row)
    results = {}
    started = time.monotonic()
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(lookup, title, args.retry_errors):title for title in groups}
        for i, future in enumerate(cf.as_completed(futures), 1):
            title = futures[future]
            response = future.result()
            for row in groups[title]:
                results[row['record_id']] = match(row, response)
            if i % 100 == 0 or i == len(groups):
                print(f'{i}/{len(groups)} unique titles; {len(results)}/{len(rows)} studies; {dict(Counter(r["decision"] for r in results.values()))}; elapsed {time.monotonic()-started:.0f}s', flush=True)
    frame = pd.DataFrame([results[r['record_id']] for r in rows], columns=COLUMNS)
    frame.to_csv(OUT / 'url_search_results.csv', index=False, encoding='utf-8')
    accepted = frame[frame.decision == 'accepted']
    sample = accepted.sample(n=min(50,len(accepted)), random_state=20261013)
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        checked = list(pool.map(check_url, sample.to_dict('records')))
    checks = pd.DataFrame(checked, columns=COLUMNS+['http_status','http_error','final_url','http_method'])
    checks.to_csv(OUT / 'url_search_sample_check.csv', index=False, encoding='utf-8')
    doi_owners = defaultdict(list)
    for row in data[['record_id','title','doi']].to_dict('records'):
        key = doi_key(row['doi'])
        if key:
            doi_owners[key].append(row)
    completed_titles = set()
    attempted_titles = set()
    attempted_keys = {p.name.split('.attempt-',1)[0] for p in (OUT / 'cache').rglob('*.attempt-*.json')}
    for title in groups:
        key = hashlib.sha256(title.encode('utf-8')).hexdigest()
        folder = OUT / 'cache' / key[:2]
        if key in attempted_keys:
            attempted_titles.add(title)
        path = folder / (key+'.json')
        if path.exists() and not json.loads(path.read_text(encoding='utf-8')).get('error'):
            completed_titles.add(title)
    completed_count = sum(len(groups[t]) for t in completed_titles)
    attempted_count = sum(len(groups[t]) for t in attempted_titles)
    lines = ['# HFF v2.4.1 OpenAlex URL search', '', f'Included dataset: {len(data):,} studies. Selected: {len(frame):,} studies ({len(groups):,} unique exact titles). Successfully searched: {completed_count:,} studies; attempted at least once: {attempted_count:,} studies.', '']
    if completed_count != len(frame):
        lines += [f'**INCOMPLETE RUN.** {attempted_count-completed_count:,} studies had unsuccessful lookup attempts; {len(frame)-attempted_count:,} were not attempted after API budget exhaustion. Both are marked error, not negative bibliographic results. Rerun after the budget resets, or with an authorized API key using --api-key-env VARIABLE_NAME --retry-errors or --api-key-file PATH --retry-errors. Successful cached lookups will not be repeated.', '']
    lines += ['## Decisions', '']
    for decision in ['accepted','no_match','below_threshold','year_mismatch','ambiguous','error']:
        lines.append(f'- {decision}: {int((frame.decision == decision).sum()):,}')
    lines += ['', '## Accepted URL sources', '']
    lines += [f'- {source}: {count:,}' for source,count in accepted.url_source.value_counts().items()]
    routes = accepted[['record_id']].merge(selected[['record_id','origin']], on='record_id', validate='one_to_one')
    lines += ['', '## Accepted URLs by origin (route)', '']
    lines += [f'- {route or "(empty)"}: {count:,}' for route,count in routes.origin.value_counts(dropna=False).items()]
    lines += ['', f'Accepted matches carrying a DOI (information only): {int(accepted.found_doi.map(lambda x:bool(doi_key(x))).sum()):,}.', '', '## Possible duplicates', '']
    duplicates = []
    for row in accepted.to_dict('records'):
        owners = [o for o in doi_owners.get(doi_key(row['found_doi']),[]) if o['record_id'] != row['record_id']]
        for owner in owners:
            duplicates.append((row,owner))
    lines.append(f'{len(duplicates):,} DOI ownership links across {len({r["record_id"] for r,o in duplicates}):,} accepted studies. Listed for review; no action taken.')
    for row,owner in duplicates:
        lines.append(f'- Search record {row["record_id"]}: {row["found_doi"]}; already on included record {owner["record_id"]}: {owner["title"].replace(chr(10)," ")}')
    lines += ['', '## Spot-check HTTP results', '', f'{len(checks)} accepted matches sampled with pandas random_state=20261013. One HEAD fetch per sampled URL (redirects followed), 20-second timeout; cached on rerun. HTTP success does not establish bibliographic correctness.']
    statuses = Counter(str(r['http_status']) if r['http_status'] != '' else 'network/timeout error' for r in checked)
    lines += [f'- {status}: {count}' for status,count in sorted(statuses.items())]
    lines += ['', '## Exact rules and limitations', '',
              '- Missing means empty or NA, Could not find, None, nan, case-insensitive after trimming, in BOTH doi and url.',
              '- OpenAlex works search receives only the title (literal ? and * replaced by spaces because the API rejects these wildcard punctuation marks in stemmed searches); per-page=5; no mailto or CrossRef. An API key is used only if explicitly supplied through --api-key-env or --api-key-file. Shared request-start limit: 8/second. Up to seven attempts, exponential backoff capped at 60 seconds for 429, 5xx, or transport errors. Explicit daily-budget exhaustion stops further requests until a later rerun. Every HTTP response body is cached alongside the final lookup result.',
              '- Normalize by stripping HTML tags, decoding HTML entities, lower-casing, replacing Unicode punctuation with spaces, and collapsing whitespace. Compare with difflib.SequenceMatcher(autojunk=False).ratio(), threshold >=0.95; publication_year must be within +/-1 of our numeric year. Missing/invalid years cannot pass.',
              '- Choose the highest similarity among candidates satisfying BOTH tests. Exact equal scores for distinct OpenAlex IDs are ambiguous; no URL is accepted. No candidates means no_match; no title passing means below_threshold; title passing but no qualifying year means year_mismatch. A qualifying work without any eligible URL is no_match. Terminal lookup failures are error.',
              '- Best-candidate columns use the best passing candidate when available, otherwise highest title similarity. Ties retain API order for informational columns only. found_doi is informational even for rejected candidates; duplicate checks cover accepted rows only.',
              '- URL preference: primary_location.landing_page_url, first nonempty locations landing_page_url, ids.pmid converted to a PubMed URL, then work DOI converted to https://doi.org/. No OpenAlex work URL fallback.',
              '- found_doi ownership comparisons remove DOI resolver prefixes and doi: and compare case-insensitively against all included records, excluding the same record_id.',
              '- Full responses may contain OpenAlex metadata; only dataset titles were transmitted. Dataset and existing repository files were not modified. Human spot-check review is required before any separate dataset/site integration.', '']
    (OUT / 'url_search_summary.md').write_text('\n'.join(lines), encoding='utf-8')
    print('DONE', dict(frame.decision.value_counts()), flush=True)
    return EXHAUSTED.is_set()

def wait_for_reset():
    now = datetime.now(timezone.utc)
    resume = (now + timedelta(days=1)).replace(hour=0, minute=1, second=0, microsecond=0)
    OUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / 'daily_resume_status.json', {'state':'waiting_for_daily_reset', 'next_run_utc':resume.isoformat()})
    print(f'Waiting for free daily budget reset: {resume.isoformat()}', flush=True)
    while True:
        remaining = (resume - datetime.now(timezone.utc)).total_seconds()
        if remaining <= 0:
            break
        time.sleep(min(60, remaining))
    atomic_json(OUT / 'daily_resume_status.json', {'state':'running', 'started_utc':datetime.now(timezone.utc).isoformat()})

if __name__ == '__main__':
    if '--daily-resume' in sys.argv:
        while True:
            wait_for_reset()
            if not main():
                atomic_json(OUT / 'daily_resume_status.json', {'state':'finished', 'finished_utc':datetime.now(timezone.utc).isoformat(), 'note':'Check summary for any non-budget errors requiring review.'})
                break
    else:
        main()
