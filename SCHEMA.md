# vendor.toml schema (v0)

One file per vendor at `vendors/<slug>/vendor.toml`. Every section is
optional except `[vendor]` — annotate what you've observed, skip what you
haven't. All glob patterns are [doublestar](https://github.com/bmatcuk/doublestar)
syntax, matched against paths relative to the vendor's library root.

## [vendor]

```toml
[vendor]
name     = "Samples From Mars"    # display name
slug     = "samples-from-mars"    # dir name; lowercase, hyphens
aliases  = ["SFM"]                # what people actually call it
homepage = "https://samplesfrommars.com"
observed = 2026-07-18             # date the facts below were last checked
                                  # against a real copy of the library
```

**Proposed 2026-08-19 — acquisition fields** (see materialized-tunes
SPEC §11.6; accept by deleting this sentence):

```toml
[vendor]
role    = "house"                 # house | marketplace | distributor | archive
domains = ["samplesfrommars.com", "shop.samplesfrommars.com"]
                                  # every host a pointer in this vendor's
                                  # files may use; subdomains match. A URL
                                  # whose host is declared nowhere FAILS
                                  # lint — "everyone knows where" is not a host.
```

`role = "distributor"` marks a vendor that ships *other* labels' packs
under licence (Loopmasters free samplers, Bandcamp, Splice). Pack files
point at a distributor with `[acquisition] via = "<its slug>"`, and the
pointer must then sit inside the distributor's `domains`.

**Curators are not distributors** *(ratified 2026-08-19)*. The role is
reserved for parties the rights-holder demonstrably licensed to
distribute. Curation surfaces — BPB, KVR threads, blogs, roundups — never
get distributor records, however useful they are for *finding* packs;
the pointer goes past them to the vendor's own page, always. No evidenced
licence, no `via`.

## [packs] — where pack boundaries are

```toml
[packs]
grammar     = "top-level-dirs"    # each top-level dir is one pack
dir_pattern = "* From Mars"       # naming convention; not a guarantee —
                                  # note exceptions in `exceptions`
exceptions  = ["Databenders Toolkit"]
sibling_zip = "archival-original" # <pack>.zip beside the pack dir is the
                                  # vendor's original download, not a pack
zip_name_grammar = "lower_snake or lower-hyphen of the dir name"
```

`grammar` values: `top-level-dirs` (the only one defined so far; propose
others as vendors demand them).

**Marketplaces.** A pack *house* (Samples From Mars, Polyend, Zero-G) has
a finite catalog; annotating every pack is a bounded job and belongs here.
A *marketplace* (Splice, Loopcloud) lists more packs every day and every
user holds a different partial subset — per-pack files would never be
complete and would swamp the repo. Marketplace vendors ship grammar only
and declare a resolver:

```toml
[packs]
grammar  = "top-level-dirs"
resolver = "splice-graphql"   # named strategy a consumer implements
```

The consumer asks the vendor's own public API about each pack dir it
actually has (name, slug, provider, product URL, cover pointer, tags) and
caches the answer locally, outside this repo. Document the endpoint and
query in the vendor.toml comments so the strategy is reproducible. `packs/`
and `manifests/` are absent for such vendors by design.

## [formats] — canonical audio vs parallel exports

Vendors ship the same sounds cut for many hosts. One tree is the canonical
audio; the rest are format exports and sidecar files that audio tools
should skip.

```toml
[formats]
canonical_dir      = "WAV"        # per-pack dir holding plain audio
parallel_dirs      = ["Ableton Live", "Kontakt", "Maschine", "..."]
sidecar_extensions = [".asd", ".als", ".nki", "..."]  # metadata riding
                                  # alongside audio anywhere in the tree
```

## [[category]] — folder grammar → shared vocabulary

The payoff section: maps a vendor's (inconsistent) folder names to a
shared category vocabulary, so "give me the one-shots" needs no globs.
`match` patterns apply to directory names under the canonical tree, at any
depth. A vendor's variants stay visible — they're the observed fact.

Vocabulary so far: `one-shots`, `loops`, `multisamples`, `fx`. (`kits`
was retired 2026-08-30: a kit is a folder of one-shots, so "kit" words
are one-shots aliases now.)
Extend it in a PR when a vendor genuinely doesn't fit.

A **shared category lexicon** lives at the repo root in `categories.toml`,
mirroring `instruments.toml`: whole-word aliases over normalized path
segments (directories deepest-first, filename stem last, first hit wins).
It is the fallback tier — consumers apply a vendor's own `[[dir]]` maps,
`[[category]]` rules, and `dedicated_packs` first, and consult the shared
lexicon only when those say nothing, so it also covers vendors with no
annotation at all (a user's own dump of loose packs).

```toml
[[category]]
id    = "one-shots"
match = ["*Individual Hits*", "*One Shots*", "*One Hits*"]

[[category]]
id             = "loops"
match          = ["*Loop*", "*Full Beats*"]
dedicated_packs = ["* Loops From Mars"]   # whole packs that ARE this category
```

## [[instrument]] — vendor-local instrument overrides

The shared instrument vocabulary lives at the repo root in
`instruments.toml` (canonical id, family, the words vendors write for it,
and `avoid` phrases). It is applied to every vendor, because reading a
folder called `01. Bass Drum` is transcription, not inference.

A vendor adds `[[instrument]]` blocks only for its own abbreviations —
ones that are unambiguous inside that library but far too generic to put
in the shared lexicon. These are consulted **before** `instruments.toml`.

```toml
[[instrument]]
id      = "hat"                       # a canonical id from instruments.toml
aliases = ["ch", "oh", "hh", "chh"]   # what THIS vendor writes for it
```

Consumers normalize each path segment and the filename stem (lowercase,
order prefixes dropped, non-alphanumerics to spaces), collect every label
found, and keep the most specific one — earliest in `instruments.toml`.
So `04. Rimshot/Rimshot TOM 31.wav` is a rimshot even though the machine
name in the filename also says "TOM", while `Drums/Kick 01.wav` is still
a kick. Unlabelled files stay unlabelled: never guess.

The shared `instruments.toml` also carries `[[family]]` blocks — rendering
knowledge about a whole family. `flat = true` tells consumers that build
folder trees not to split that family by instrument (bass sub-typing is
genre jargon, not a reliable label); the instrument entries still resolve
into metadata. A `[[family]]` id must be a family some instrument entry
belongs to (linted). Families are shared-lexicon-only — vendors don't
override them.

```toml
[[family]]
id   = "bass"
flat = true
```

## [naming] — filename grammar

Conventions inside filenames, for tools that rename for constrained
displays and filesystems (note-aware sanitizing, distinguishing-first
reordering, common-token stripping).

```toml
[naming]
dir_order_prefix = "NN. "         # "01. Individual Hits" — ordering only,
                                  # safe to strip for display
note_suffix      = "_<note><octave>"  # pitched files: "..._C#4.wav";
                                  # sharps use '#'
take_suffix      = " NN"          # variations count up at the tail —
                                  # the distinguishing token is LAST
key_suffix       = " - <camelot>" # musical key at the tail in Camelot
                                  # notation ("Champion Sub - 10A")
bpm_dir_suffix   = true           # loop folders END in their BPM
                                  # ("Bass Lines 166.5/", "Tha Size 167.5/")
```

Consumers harvest per-file facts from these (key from `note_suffix` /
`key_suffix`, bpm from `bpm_dir_suffix` and any literal "124 Bpm" token)
into their own local cache — the harvested values are per-file vendor
data and stay out of this repo (see Tags).

## [install] — where the library lives by default

Per-OS default install paths, so a consumer can offer "you have this
installed, add it as a source?" instead of crawling the user's disk.
`~` is the user's home. Only offer paths that actually exist.

```toml
[install]
macos   = ["~/Splice/sounds/packs"]
windows = ["~/Splice/sounds/packs"]
note    = "app-managed: new samples land continuously, so rescan often"
```

## Pack files — `vendors/<vendor>/packs/<slug>.toml`

One file per pack. Two audiences at once: display metadata for UIs, and a
machine-readable map of the pack's layout. Generated stubs (see
`tools/generate-packs.py`) carry `[pack]` + `[identity]` and a commented
directory skeleton; humans add `[meta]` and the `[[dir]]` map.

### [pack]

```toml
[pack]
name = "Acid From Mars"
slug = "acid-from-mars"
dir  = "Acid From Mars"    # dir name as the vendor ships it
url  = "https://samplesfrommars.com/products/acid-from-mars"
archives = ["acid_from_mars.zip"]  # download names as the vendor ships them —
                                   # the dumbest identity signal there is, and
                                   # it catches everyone who unzips-and-leaves-it
provider = "Sample Tools by Cr2"   # for distributor vendors (Splice): the
                                   # label the pack is BY; omit when the
                                   # vendor is the label
samples_listed = 315               # the vendor's own sample count — the
                                   # honest denominator when local copies
                                   # are partial (Splice downloads
                                   # per-sample); omit for unzip-the-whole-
                                   # pack vendors
```

### [meta] — display pointers, og:-style

Lifted from the vendor's product page (OpenGraph tags exist for exactly
this). **Pointers only**: this repo distributes facts and links, never the
vendor's creative content. An image *URL* is a fact; the image bytes are
not. A title is an identifying fact; the marketing description is prose —
consumers that want it fetch the `url`'s og tags themselves and cache
locally, outside this repo.

```toml
[meta]
title = "ACID FROM MARS"   # og:title as published — identifying, keep
type  = "product"          # og:type
image = "https://samplesfrommars.com/cdn/shop/products/acid-from-mars_grande.jpg"
# NO description field: og:description is the vendor's copy. Link, don't
# reproduce. Same reason no prices: dated instantly, one click via `url`.
```

**The discontinued exception.** When a product is dead — delisted by the
vendor, distributor gone, nothing to link to and nothing to buy — "link,
don't reproduce" has nowhere to point, and the annotation becomes the only
place the record survives. Such packs set `discontinued = true` in `[pack]`
and MAY carry `[meta] description` (assembled from booklet scans, archived
listings, and reviews — cite them in `sources`), plus release facts
(`released`, `catalog_number`, `credits`). `url` and `image` become
archival pointers (a Discogs release, a cover scan). Image *bytes* still
stay out. The bar for flipping the flag is "no legitimate new-copy source
exists"; note the check date. Zero-G's Jungle Warfare (1995–97; delisted
2020) is the reference case.

```toml
[pack]
discontinued   = true
released       = 1995
catalog_number = "TAS CD 62"
credits        = "…"
sources        = ["https://www.discogs.com/release/…", "https://www.soundonsound.com/…"]

[meta]
title       = "…"
image       = "https://i.discogs.com/…"   # archival cover scan pointer
description = '''…the historical record…'''
```

### [acquisition] — where someone who doesn't own it may go `(proposed 2026-08-19)`

Identity is unconditional — any real pack may be annotated. Whether the
annotation also says *where to get it* is gated by class, and the gate is
lint, not review. Pointers are **pages, never bytes**: the product page,
the Bandcamp release, the vendor's free-download landing page — wherever
the vendor collects whatever they price the pack at (dollars, an email,
attention). Consumers link out; they never download.

```toml
[acquisition]
class    = "vendor-free"   # vendor-free | vendor-paid | distributor | orphan
url      = "https://blumarten.bandcamp.com/album/jungle-jungle-1989-1999-samplepack"
via      = "loopmasters"   # distributor vendor slug; required iff class = "distributor"
gate     = "email"         # none | email | account | purchase — what the page asks for
license  = "royalty-free"  # royalty-free | cc0 | cc-by | cc-by-nc | informal-free | uncleared | purchase | unknown
                           # (see notes/2026-08-19-source-survey.md for what each covers)
                           # Display posture (ratified 2026-08-19): the value is a
                           # ceiling on claims, not a badge mandate — consumers may
                           # show `uncleared` quietly or not at all, but only
                           # `royalty-free` may ever be LABELLED royalty-free.
                           # Saying nothing is always allowed; upgrading never is.
observed = 2026-08-19      # when the pointer was last seen resolving
```

| class | pointer | consumer behaviour |
|---|---|---|
| `vendor-free` | rights-holder's own $0 page | listed as acquirable |
| `vendor-paid` | rights-holder's store page | listed as acquirable |
| `distributor` | licensed third party's page; `via` names it | listed as acquirable |
| `orphan` | **none** (`url` forbidden) | "recognized, not sourced" |

`discontinued = true` packs are always `orphan`. Their `[pack] url`,
`[meta] image` and `sources` are *archival* pointers — record that it
existed, never where a copy is — and are restricted to the hosts in the
root `hosts.toml` `[reference]` list.

Lint rules (`tools/lint.py`, run in CI):

- **L1 domain closure** — every URL in a vendor's files resolves to a host
  in that vendor's `domains` (or the `via` distributor's), except archival
  pointers on discontinued packs, which must be in `hosts.toml`.
- **L2 pages not bytes** — no pointer path ends in `.zip .rar .7z .tar
  .gz .wav .aif .aiff .flac .mp3`.
- **L3 orphans carry no pointer** — `class = "orphan"` ⇒ no `url`;
  `discontinued = true` ⇒ class is `orphan` if `[acquisition]` is present.
- **L4 distributors are vendors** — `via` names an existing vendor with
  `role = "distributor"` and non-empty `domains`.
- **L5 relations resolve** — see `[[relation]]`.
- **L6 freshness** — `observed` older than 365 days warns; `lint --live`
  HEADs each pointer (scheduled, not per-PR).

### [[relation]] — subsets, samplers, bundles `(proposed 2026-08-19)`

Vendors cut freebies from paid packs, re-issue, and bundle volumes. When
the free pack's manifest lines are a subset of the paid one's, consumers
derive the relation from `[identity]` with no assertion here. When the
vendor re-encoded or renamed (common), assert it:

```toml
[[relation]]
type     = "subset-of"       # subset-of | sampler-of | superseded-by | bundle-of | reissue-of
pack     = "samples-from-mars/808-from-mars"   # <vendor slug>/<pack slug>
basis    = "vendor-states"   # sha | vendor-states | observed
source   = "https://samplesfrommars.com/products/free-808"  # for vendor-states; in domains
note     = "24 of the 808's 300 hits, re-exported at 24-bit"
observed = 2026-08-19
```

`basis = "sha"` is lint-verified against both manifests (containment must
hold). The payoff for consumers: "you own X; this freebie is 100%
contained, skip it" and "you have the sampler; the full pack is at <url>".

### [identity] — "oh, you have this pack"

Computed over **audio files only** (`.wav`/`.aif*`), because format trees
(Ableton/Kontakt/…) and docs get pruned by users; the audio is the pack.
Path-free, so renames and re-organizations don't break recognition.

```toml
[identity]
algo        = "sha256-sorted-v1"
audio_files = 533
audio_bytes = 1372294742
digest      = "<sha256 of the manifest file bytes>"
anchors     = ["<first 8 sha256s of the sorted list>"]
manifest    = "manifests/acid-from-mars.sha256"
```

The manifest sidecar is the full sorted list of per-file content SHA-256s,
one hex digest per line. Match semantics for consumers:

- **exact**: your computed digest equals `digest`
- **partial**: fraction of manifest lines present in your catalog
  ("you have 96% of Acid From Mars") — report the fraction, don't round
  it to a lie
- **probable**: ≥2 `anchors` present — cheap indexed lookup across all
  packs without loading manifests; confirm with the manifest before
  asserting

### [[dir]] — the layout map

What's where and why. Paths are relative to the pack dir, globs allowed.
Semantics: a file's governing entry is the **deepest matching** `[[dir]]`;
`category` comes from the governing entry; `tags` are the **union** of
every matching prefix's tags; `desc` is for humans and UIs. Where no
`[[dir]]` claims a path, the vendor-level `[[category]]` rules still
apply — pack maps override, they don't replace.

`role` marks structural facts: `canonical-audio` (the real content),
`format-tree` (parallel DAW/sampler exports — audio tools skip these),
`docs` (manuals, artwork). `category`/`tags` describe musical content and
usually live under the canonical tree.

`instrument` pins every file under the entry to one id from the shared
instrument lexicon (`instruments.toml`), overriding whatever the filenames
appear to say — same deepest-match rule as `category`. Use it when names
carry no honest instrument signal: jungle breaks named after their sources
("Sub-Urban", "Clint Eastwood") read as anything but drums, and no lexicon
can fix that. Pin only dirs whose content is genuinely uniform; where
filenames do describe the sound, leave the lexicon to read them.

```toml
[[dir]]
path = "WAV"
role = "canonical-audio"

[[dir]]
path     = "WAV/Acid Synths"
category = "multisamples"
tags     = ["303", "acid"]
desc     = "Multisampled TB-303 patches, per-note, tube/tape processed"

[[dir]]
path     = "WAV/Acid Synths/Basic Sub"
tags     = ["sub", "bass"]
```

This is where the free stuff comes from: **views by pack** (identity),
**views by category** (dir map + vendor rules), **tags** (path unions) —
any consumer that can walk a tree gets them without understanding the
vendor's naming.

## Tags — `tags.toml` and `[pack] tags`

Canonical tag vocabulary lives at the repo root in `tags.toml`. The rules,
in order:

1. **Mechanical normalization first** (implemented by consumers, never by
   alias entries): lowercase, non-alphanumerics collapse to `-`. Vendor
   "House" and "house" are the same tag by construction.
2. **`[aliases]`** — vendor phrasing → one or more canonical tags. For
   compounds ("80s Drum Samples" → `80s` + `drums`), renames
   (`lofi` → `lo-fi`), and plural/singular ("kicks" → `kick`).
3. **`drop`** — glob patterns for vendor tags that describe compatibility
   or store plumbing, not sound (`ableton*`, `mpc*`, `wav-samples`).

Conventions: instrument pieces singular (`kick`, `snare`), families
collective (`drums`, `percussion`), decades bare (`80s`), genres
kebab-cased (`acid-house`).

Pack files carry the RESULT: `tags = ["808", "80s", "drums"]` in `[pack]`
is always canonical — harvest tooling translates before writing. A pack's
tags are facts about the pack (like its title) and distribute; per-FILE
vendor metadata (bpm, key, per-sample tags) is the vendor's database and
stays in the consumer's local cache, never in this repo.

## `hosts.toml` — archival / reference hosts `(proposed 2026-08-19)`

The only hosts allowed in pointers that belong to no vendor: used for
`discontinued` packs' `url` / `image` and for `sources` citations
anywhere. These record that a thing existed; none of them is a place to
get a copy.

```toml
[reference]
domains = ["discogs.com", "i.discogs.com", "web.archive.org",
           "soundonsound.com", "audiofanzine.com", "yumpu.com",
           "musicradar.com", "wikipedia.org"]
```

Adding a host here is a PR with a one-line reason; a host that serves
pack bytes does not qualify.

## What does not belong

- Taste ("the good kicks are in folder X")
- Per-user state (ratings, favorites)
- Anything you haven't verified against a real copy of the library
- **The vendor's creative content**: descriptions, marketing copy, image
  files, audio — link to it (`url`, `image`), never reproduce it. Facts
  and pointers distribute; prose and pixels get fetched by the consumer
  and cached locally. (Sole exception: `discontinued = true` packs, above.)
- **Acquisition pointers to anywhere but the rights-holder or a declared
  distributor** — no mirrors, no "everyone knows" hosts, no file URLs.
  Lint enforces it (`[acquisition]`, `hosts.toml`).
- Per-FILE content hashes as annotation data. Pack-level identity is
  settled (`[identity]` + the manifest sidecar, `sha256-sorted-v1`) —
  that's the *only* hash shape here; don't invent others
