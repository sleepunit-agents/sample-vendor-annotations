#!/usr/bin/env python3
"""Lint the annotations repo — proposed 2026-08-19 (SCHEMA.md: [acquisition],
[[relation]], hosts.toml). Rules L1–L6. Exit 1 on any error; warnings are
reported and do not fail. Needs Python 3.11+ (tomllib) and nothing else.

  tools/lint.py            # L1–L5 (+L6 freshness warning)
  tools/lint.py --live     # also HEAD every pointer (slow; for scheduled CI)
"""
import sys, os, glob, tomllib, datetime, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BYTE_EXT = ('.zip', '.rar', '.7z', '.tar', '.gz', '.wav', '.aif', '.aiff', '.flac', '.mp3')
CLASSES = {'vendor-free', 'vendor-paid', 'distributor', 'orphan'}
GATES = {'none', 'email', 'account', 'purchase'}
LICENSES = {'royalty-free', 'cc0', 'cc-by', 'cc-by-nc', 'informal-free', 'uncleared', 'purchase', 'unknown'}
REL_TYPES = {'subset-of', 'sampler-of', 'superseded-by', 'bundle-of', 'reissue-of'}
REL_BASIS = {'sha', 'vendor-states', 'observed'}
ROLES = {'house', 'marketplace', 'distributor', 'archive'}

errors, warns = [], []
def err(where, msg): errors.append(f"{where}: {msg}")
def warn(where, msg): warns.append(f"{where}: {msg}")

def load(path):
    with open(path, 'rb') as f: return tomllib.load(f)

def host_of(url):
    try: return (urllib.parse.urlsplit(url).hostname or '').lower()
    except Exception: return ''

def in_domains(host, domains):
    return any(host == d or host.endswith('.' + d) for d in domains)

ref_hosts = []
if os.path.exists(os.path.join(ROOT, 'hosts.toml')):
    ref_hosts = [d.lower() for d in load(os.path.join(ROOT, 'hosts.toml')).get('reference', {}).get('domains', [])]

lex_ids = set()
if os.path.exists(os.path.join(ROOT, 'instruments.toml')):
    lex_ids = {i['id'] for i in load(os.path.join(ROOT, 'instruments.toml')).get('instrument', [])}

vendors = {}
for vt in sorted(glob.glob(os.path.join(ROOT, 'vendors', '*', 'vendor.toml'))):
    slug = os.path.basename(os.path.dirname(vt))
    d = load(vt)
    v = d.get('vendor', {})
    if v.get('slug') and v['slug'] != slug:
        err(vt, f"slug {v['slug']!r} != dir {slug!r}")
    role = v.get('role', 'house')
    if role not in ROLES: err(vt, f"[vendor] role {role!r} not in {sorted(ROLES)}")
    domains = [x.lower() for x in v.get('domains', [])]
    if not domains: warn(vt, "[vendor] domains missing — every pointer in this vendor will fail L1")
    hp = v.get('homepage')
    if hp and domains and not in_domains(host_of(hp), domains):
        err(vt, f"L1 homepage host {host_of(hp)!r} not in domains")
    vendors[slug] = {'role': role, 'domains': domains, 'path': vt,
                     'instruments': {i['id'] for i in d.get('instrument', [])}}

def check_url(where, url, domains, allow_ref=False, label='url'):
    h = host_of(url)
    if not h: err(where, f"{label} unparsable: {url!r}"); return
    ok = in_domains(h, domains) or (allow_ref and in_domains(h, ref_hosts))
    if not ok:
        err(where, f"L1 {label} host {h!r} not in vendor domains" + (" or hosts.toml reference list" if allow_ref else ""))
    if urllib.parse.urlsplit(url).path.lower().endswith(BYTE_EXT):
        err(where, f"L2 {label} points at bytes, not a page: {url}")

packs = {}   # "vendor/pack" -> (path, data)
for slug, V in vendors.items():
    for pt in sorted(glob.glob(os.path.join(ROOT, 'vendors', slug, 'packs', '*.toml'))):
        d = load(pt)
        ps = d.get('pack', {}).get('slug') or os.path.splitext(os.path.basename(pt))[0]
        packs[f"{slug}/{ps}"] = (pt, d, slug)

today = datetime.date.today()
live_urls = []
for key, (pt, d, slug) in packs.items():
    V = vendors[slug]; domains = V['domains']
    pack = d.get('pack', {}); meta = d.get('meta', {}); acq = d.get('acquisition')
    disc = bool(pack.get('discontinued'))
    # [pack] url / [meta] image / sources
    if pack.get('url'):   check_url(pt, pack['url'], domains, allow_ref=disc, label='[pack] url')
    if meta.get('image'): check_url(pt, meta['image'], domains, allow_ref=disc, label='[meta] image')
    for s in pack.get('sources', []):
        h = host_of(s)
        if not (in_domains(h, domains) or in_domains(h, ref_hosts)):
            err(pt, f"L1 sources host {h!r} not in vendor domains or hosts.toml")
    # [acquisition]
    if acq is not None:
        cls = acq.get('class')
        if cls not in CLASSES: err(pt, f"[acquisition] class {cls!r} not in {sorted(CLASSES)}")
        if acq.get('gate', 'none') not in GATES: err(pt, f"[acquisition] gate {acq.get('gate')!r} invalid")
        if acq.get('license', 'unknown') not in LICENSES: err(pt, f"[acquisition] license {acq.get('license')!r} invalid")
        if disc and cls != 'orphan': err(pt, "L3 discontinued pack must be class = \"orphan\"")
        if cls == 'orphan':
            if acq.get('url'): err(pt, "L3 orphan carries a pointer — remove [acquisition] url")
        else:
            if not acq.get('url'): err(pt, f"[acquisition] class {cls} requires url")
            else:
                pdom = domains
                if cls == 'distributor':
                    via = acq.get('via')
                    if not via or via not in vendors: err(pt, f"L4 via {via!r} is not a vendor record")
                    elif vendors[via]['role'] != 'distributor' or not vendors[via]['domains']:
                        err(pt, f"L4 via {via!r} must have role = \"distributor\" and domains")
                    else: pdom = vendors[via]['domains']
                elif acq.get('via'): err(pt, "[acquisition] via only valid with class = \"distributor\"")
                check_url(pt, acq['url'], pdom, label='[acquisition] url')
                live_urls.append((pt, acq['url']))
        obs = acq.get('observed')
        if not obs: warn(pt, "[acquisition] observed missing")
        elif isinstance(obs, datetime.date) and (today - obs).days > 365:
            warn(pt, f"L6 [acquisition] observed {obs} is >365 days old")
    # [[dir]] instrument pins — a typo'd id would silently pin files to an
    # instrument no consumer's lexicon knows
    for dd in d.get('dir', []):
        pin = dd.get('instrument')
        if pin and pin not in lex_ids and pin not in V['instruments']:
            err(pt, f"[[dir]] {dd.get('path')!r} instrument {pin!r} not in instruments.toml")
    # [[relation]]
    for r in d.get('relation', []):
        if r.get('type') not in REL_TYPES: err(pt, f"[[relation]] type {r.get('type')!r} invalid")
        if r.get('basis') not in REL_BASIS: err(pt, f"[[relation]] basis {r.get('basis')!r} invalid")
        tgt = r.get('pack')
        if tgt not in packs: err(pt, f"L5 [[relation]] pack {tgt!r} does not exist"); continue
        if r.get('basis') == 'vendor-states':
            if not r.get('source'): err(pt, "L5 basis vendor-states needs source")
            else: check_url(pt, r['source'], domains, label='[[relation]] source')
        if r.get('basis') == 'sha' and r.get('type') in ('subset-of', 'sampler-of'):
            def lines(p, dd):
                m = dd.get('identity', {}).get('manifest')
                if not m: return None
                mp = os.path.join(os.path.dirname(os.path.dirname(p)), m)
                return set(l.strip() for l in open(mp) if l.strip()) if os.path.exists(mp) else None
            a, b = lines(pt, d), lines(packs[tgt][0], packs[tgt][1])
            if a is None or b is None: err(pt, "L5 basis sha but a manifest is missing")
            elif not a <= b:
                frac = len(a & b) / max(1, len(a))
                err(pt, f"L5 basis sha: only {frac:.1%} of this pack's manifest is in {tgt}")

if '--live' in sys.argv:
    for pt, u in live_urls:
        try:
            req = urllib.request.Request(u, method='HEAD', headers={'User-Agent': 'sample-vendor-annotations-lint'})
            with urllib.request.urlopen(req, timeout=15) as r:
                if r.status >= 400: warn(pt, f"L6 live: {u} -> {r.status}")
        except Exception as e:
            warn(pt, f"L6 live: {u} -> {e}")

for w in warns: print("warn:", w)
for e in errors: print("ERROR:", e)
print(f"{len(vendors)} vendors, {len(packs)} packs, {len(errors)} errors, {len(warns)} warnings")
sys.exit(1 if errors else 0)
