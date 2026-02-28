#!/usr/bin/env python3
"""Import weekly strategy posts from monty-trader.com into local blog markdown files.

This script fetches weekly posts from WordPress REST API, extracts allocation hints
from HTML tables, converts them into ETF allocations, and writes simplified markdown
compatible with the existing backtest parser.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

BASE_URL = "https://monty-trader.com"
API_ROOT = f"{BASE_URL}/wp-json/wp/v2"


@dataclass(frozen=True)
class PostMeta:
    post_id: int
    post_date: str
    title: str
    slug: str
    link: str
    week_date: date


_WEEK_PATTERNS = (
    re.compile(r"(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日週"),
    re.compile(r"(20\d{2})[/-](\d{1,2})[/-](\d{1,2})週"),
    re.compile(r"(20\d{2})[._-](\d{1,2})[._-](\d{1,2})\s*週"),
)

_SLUG_PATTERNS = (
    re.compile(r"weekly-strategy-(20\d{2})-(\d{2})-(\d{2})"),
    re.compile(r"weekly-review-(20\d{2})-(\d{2})-(\d{2})"),
    re.compile(r"weekly-report-(20\d{2})(\d{2})(\d{2})"),
)

_ETF_PATTERN = re.compile(r"\b(SPY|QQQ|DIA|XLV|XLP|GLD|XLE|TLT|BIL|URA|SH|SDS)\b\s*([0-9]+(?:\.[0-9]+)?)\s*%")
_PCT_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)?)(?:\s*[-–〜~]\s*([0-9]+(?:\.[0-9]+)?))?\s*%")
_TAG_RE = re.compile(r"(?is)<[^>]+>")

# Category keyword -> ETF mix
_CATEGORY_MAP: list[tuple[tuple[str, ...], dict[str, float]]] = [
    (("コア", "指数"), {"SPY": 0.65, "QQQ": 0.25, "DIA": 0.10}),
    (("ハイテク", "テクノロジー", "クオリティ", "決算"), {"QQQ": 1.0}),
    (("ウラン",), {"URA": 1.0}),
    (("現金", "短期債"), {"BIL": 1.0}),
    (("長期債",), {"TLT": 1.0}),
    (("防御", "ディフェンシブ", "低ボラ", "ユーティリティ"), {"XLV": 0.5, "XLP": 0.5}),
    (("素材", "エネルギー"), {"XLE": 1.0}),
    (("金", "ゴールド"), {"GLD": 1.0}),
    (("ヘッジ", "テーマ"), {"GLD": 0.6, "XLE": 0.4}),
]


def _get_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": "weekly-trade-strategy-importer"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _clean_text(s: str) -> str:
    text = html.unescape(s)
    text = _TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_week_date(title: str, slug: str) -> date | None:
    for p in _WEEK_PATTERNS:
        m = p.search(title)
        if m:
            y, mo, d = map(int, m.groups())
            return date(y, mo, d)

    for p in _SLUG_PATTERNS:
        m = p.search(slug)
        if m:
            y, mo, d = map(int, m.groups())
            return date(y, mo, d)
    return None


def _iter_category_posts(category_id: int) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while True:
        params = urllib.parse.urlencode(
            {
                "per_page": 100,
                "page": page,
                "categories": category_id,
                "orderby": "date",
                "order": "asc",
                "_fields": "id,date,slug,title,link",
            }
        )
        url = f"{API_ROOT}/posts?{params}"
        try:
            data = _get_json(url)
        except urllib.error.HTTPError as exc:
            # WP returns 400 for page overflow.
            if exc.code == 400:
                break
            raise
        if not isinstance(data, list) or not data:
            break
        rows.extend(data)
        page += 1
    return rows


def _fetch_post_content(post_id: int) -> str:
    url = f"{API_ROOT}/posts/{post_id}?_fields=content"
    data = _get_json(url)
    if not isinstance(data, dict):
        return ""
    content = data.get("content", {})
    if isinstance(content, dict):
        rendered = content.get("rendered", "")
        if isinstance(rendered, str):
            return html.unescape(rendered)
    return ""


def _parse_table_rows(table_html: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for tr in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", table_html):
        cells = [
            _clean_text(cell)
            for cell in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)
        ]
        if cells:
            rows.append(cells)
    return rows


def _parse_pct(text: str) -> float | None:
    m = _PCT_PATTERN.search(text)
    if not m:
        return None
    lo = float(m.group(1))
    hi = m.group(2)
    if hi:
        return (lo + float(hi)) / 2
    return lo


def _table_score(rows: list[list[str]]) -> int:
    score = 0
    for row in rows:
        cat = row[0] if row else ""
        row_text = " ".join(row)
        if re.search(r"コア|防御|ディフェンシブ|現金|短期債|ヘッジ|テーマ|ウラン|素材|エネルギー|ユーティリティ|ブロック|配分|比率", cat):
            score += 4
        if _PCT_PATTERN.search(row_text):
            score += 1
        if _ETF_PATTERN.search(row_text):
            score += 2
    return score


def _map_category(cat: str) -> dict[str, float]:
    for keywords, mix in _CATEGORY_MAP:
        if any(k in cat for k in keywords):
            return dict(mix)
    return {}


def _extract_allocations(content_html: str) -> dict[str, float]:
    tables = re.findall(r"(?is)<table[^>]*>(.*?)</table>", content_html)
    parsed_tables = [_parse_table_rows(t) for t in tables]
    parsed_tables = [t for t in parsed_tables if t]
    if not parsed_tables:
        return {}

    best_rows = max(parsed_tables, key=_table_score)
    if _table_score(best_rows) < 12:
        return {}

    alloc: dict[str, float] = defaultdict(float)
    for row in best_rows:
        if len(row) < 2:
            continue
        cat = row[0]
        if not re.search(r"コア|防御|ディフェンシブ|現金|短期債|ヘッジ|テーマ|ウラン|素材|エネルギー|ユーティリティ|テクノロジー|クオリティ|決算", cat):
            continue

        pct = _parse_pct(row[1])
        if pct is None and len(row) >= 3:
            pct = _parse_pct(row[2])
        if pct is None:
            continue

        detail = row[2] if len(row) >= 3 else row[1]
        etf_hits = _ETF_PATTERN.findall(detail)
        if etf_hits:
            for sym, p in etf_hits:
                alloc[sym] += float(p)
            continue

        mapped = _map_category(cat)
        if not mapped:
            continue
        for sym, w in mapped.items():
            alloc[sym] += pct * w

    if not alloc:
        return {}

    total = sum(alloc.values())
    if total < 90:
        alloc["BIL"] += 100 - total
        total = sum(alloc.values())
    if total > 110:
        factor = 100.0 / total
        alloc = {k: v * factor for k, v in alloc.items()}

    rounded = {k: round(v, 1) for k, v in alloc.items() if v >= 0.2}
    total = sum(rounded.values())
    if total < 90 or total > 110:
        return {}
    return rounded


def _render_blog_markdown(meta: PostMeta, alloc: dict[str, float]) -> str:
    ordered = sorted(alloc.items(), key=lambda kv: (-kv[1], kv[0]))
    rows = "\n".join(f"| {sym} | {pct:.1f}% |" for sym, pct in ordered)
    etf_line = "、".join(f"{sym} {pct:.1f}%" for sym, pct in ordered)
    return f"""# {meta.title}

Source: {meta.link}
Imported Date: {meta.post_date}

## セクター配分（変換）

| ETF | 配分 |
| --- | --- |
{rows}

ETF内訳: {etf_line}

合計: {sum(alloc.values()):.1f}%

## シナリオ別プラン

### Base Case: Imported from monty-trader.com (100%)
**トリガー**: imported-default
"""


def build_import(output_dir: Path, categories: list[int]) -> tuple[int, int, list[str]]:
    raw_posts: dict[int, dict] = {}
    for cat in categories:
        for item in _iter_category_posts(cat):
            post_id = int(item["id"])
            raw_posts[post_id] = item

    candidates: dict[date, PostMeta] = {}
    for item in raw_posts.values():
        title = html.unescape(item["title"]["rendered"])
        slug = item["slug"]
        week_date = _extract_week_date(title, slug)
        if not week_date:
            continue
        if not re.search(r"戦略|プラン|weekly", title, flags=re.IGNORECASE) and "weekly" not in slug:
            continue
        meta = PostMeta(
            post_id=int(item["id"]),
            post_date=item["date"],
            title=title,
            slug=slug,
            link=item["link"],
            week_date=week_date,
        )
        current = candidates.get(week_date)
        # Keep the latest post when duplicates exist for same strategy week.
        if current is None or meta.post_date > current.post_date:
            candidates[week_date] = meta

    output_dir.mkdir(parents=True, exist_ok=True)
    generated = 0
    skipped: list[str] = []

    for week_d in sorted(candidates):
        meta = candidates[week_d]
        content = _fetch_post_content(meta.post_id)
        alloc = _extract_allocations(content)
        if not alloc:
            skipped.append(f"{week_d.isoformat()} id={meta.post_id} no-alloc")
            continue
        md = _render_blog_markdown(meta, alloc)
        out = output_dir / f"{week_d.isoformat()}-weekly-strategy.md"
        out.write_text(md, encoding="utf-8")
        generated += 1

    return len(candidates), generated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Import weekly strategy posts from monty-trader.com")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/imported_blogs_monty"),
        help="Output directory for generated markdown blogs",
    )
    parser.add_argument(
        "--categories",
        type=int,
        nargs="+",
        default=[37, 39],
        help="WordPress category IDs to scan (default: 37 39)",
    )
    parser.add_argument(
        "--verbose-skip",
        action="store_true",
        help="Print skipped entries",
    )
    args = parser.parse_args()

    candidates, generated, skipped = build_import(args.output_dir, args.categories)
    print(f"Candidates with week-date: {candidates}")
    print(f"Generated markdown blogs: {generated}")
    print(f"Skipped: {len(skipped)}")
    if args.verbose_skip:
        for row in skipped:
            print(" -", row)


if __name__ == "__main__":
    main()
