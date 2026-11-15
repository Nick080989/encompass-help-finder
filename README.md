# Encompass Help Finder

A fast, searchable index of the **1,449 public articles** in the [Encompass Technologies help center](https://help.encompasstech.com/en-us/), built as a quick-reference tool for IT support at a beverage distributor.

**Live site: [nick080989.github.io/encompass-help-finder](https://nick080989.github.io/encompass-help-finder/)**

> Unofficial. Not affiliated with or endorsed by Encompass Technologies. All article content belongs to Encompass Technologies; every article links back to its original page.

## Features

- **Browse by module.** All 12 Encompass modules (Logistics, Platform, CRM, WMS, Accounting, and others) open as nested dropdowns that follow the help center's own collections.
- **Search ranked by relevance count.** Results are sorted by how many times your words appear in the article title and full text, and each result shows its mention count. Multi-word searches require every word; quotes match an exact phrase.
- **Match navigator.** Opening an article from a search highlights every match and lets you jump between them (buttons or the `N` key).
- **Module filters** with live result counts, an **IT quick start** panel (Platform, DevOps, Global Data), and one-click common IT searches.
- **Saved and recently viewed articles**, kept in your browser.
- Works on phones, supports light and dark mode, and has keyboard shortcuts (`/` to search, `Esc` to close).

## How it works

It's a static site with no server or database:

| File | Purpose |
|---|---|
| `index.html` | The whole app (HTML, CSS, JavaScript) with the category tree and article list built in |
| `articles.json` | The cleaned article text, loaded once for full-text search |
| `tools/` | Python scripts that rebuild the site from the live help center |

## Rebuilding with fresh articles

Requires Python 3. The crawler respects the help center's `robots.txt` (1 request per second), so a full run takes about 30 minutes.

```bash
python tools/download_articles.py crawl
python tools/build_index.py crawl build
python tools/assemble_site.py tools/template.html build .
```

Snapshot date of the current data: 14 November 2026.
