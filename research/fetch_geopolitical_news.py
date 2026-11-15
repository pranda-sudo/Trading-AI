"""Fetch public Google News RSS search results; headlines only, no article scraping."""
import json, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

QUERIES = [
    ("Geopolitika", "geopolitics sanctions tariffs war oil markets when:2d"),
    ("Zlato a dolar", "gold dollar treasury yields fed inflation markets when:2d"),
    ("Akciové indexy", "stocks wall street nasdaq dax economy volatility when:2d"),
]
UA = {"User-Agent": "TradingAI-NewsMonitor/1.0 (+public RSS; research)"}
items = []
errors = []
for category, query in QUERIES:
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as response:
            root = ET.fromstring(response.read(2_000_000))
        for node in root.findall("./channel/item")[:20]:
            title = (node.findtext("title") or "").strip()
            link = (node.findtext("link") or "").strip()
            source = (node.findtext("source") or "").strip()
            raw_date = node.findtext("pubDate") or ""
            try:
                published = parsedate_to_datetime(raw_date).astimezone(timezone.utc)
            except (TypeError, ValueError, OverflowError):
                continue
            if not title or not link.startswith("https://") or len(title)>300:
                continue
            age = (datetime.now(timezone.utc) - published).total_seconds()
            if age < -3600 or age > 72*3600:
                continue
            items.append({"title":title, "url":link, "source":source or "Google News",
                          "published_utc":published.isoformat(), "category":category})
    except Exception as exc:
        errors.append(category + ": " + type(exc).__name__)
seen = set()
unique = []
for item in sorted(items, key=lambda x:x["published_utc"], reverse=True):
    normalized = re.sub(r"\W+", "", item["title"].lower())[:130]
    if normalized in seen:
        continue
    seen.add(normalized)
    unique.append(item)
if not unique:
    raise SystemExit("No valid RSS articles; keeping previous published feed. " + "; ".join(errors))
output = {"updated_utc":datetime.now(timezone.utc).isoformat(),
          "source_note":"Google News RSS search aggregation; links point to publisher via Google News",
          "errors":errors, "items":unique[:45]}
Path("geopolitical-news.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Saved",len(output["items"]),"articles; source errors:",errors)
