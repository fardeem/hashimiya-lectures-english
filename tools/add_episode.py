#!/usr/bin/env python3
"""Publish a new episode to the Hashimiya Lectures in English podcast.

Usage:
  add_episode.py --mp3 FILE --title TITLE --date YYYY-MM-DD --description TEXT_OR_@FILE \
                 --source-url YOUTUBE_URL [--pdf FILE] [--slug SLUG] [--no-push]

What it does:
  1. Creates a GitHub Release (tag = slug) in the repo and uploads the MP3 (and optional PDF) as assets.
  2. Adds the episode to episodes.json (newest first), regenerates feed.xml and index.html.
  3. Commits and pushes to main (GitHub Pages redeploys automatically).
MP3s are never committed to git.
"""
import argparse, datetime as dt, email.utils, html, json, os, re, subprocess, sys
from xml.sax.saxutils import escape

OWNER = "fardeem"
REPO = "hashimiya-lectures-english"
HERE = os.path.dirname(os.path.abspath(__file__))
CLONE = os.path.join(HERE, "repo")
SITE = f"https://{OWNER}.github.io/{REPO}"
GH_REPO = f"https://github.com/{OWNER}/{REPO}"
YT = "https://www.youtube.com/@tariqalhashimiya"

CHANNEL = {
    "title": "Hashimiya Lectures in English",
    "author": "Shaykh Abd al-Kabir al-Balghithi (unofficial English narration)",
    "owner_name": "Fardeem",
    "summary": (
        "Unofficial English translations and narrations of the lessons of Shaykh (Sidi Mawlay) "
        "Abd al-Kabir al-Balghithi of the Hashimiyya-Habibiyya Darqawiyya-Shadhiliyya order, "
        f"originally delivered in Moroccan Arabic and Classical Arabic on the YouTube channel {YT}. "
        "Each episode is an edited English rendering read aloud by a synthetic voice; it is not "
        "affiliated with or endorsed by the channel. Please refer to the original recordings for the Shaykh's own words."
    ),
}


def run(cmd, **kw):
    print("+", " ".join(cmd), file=sys.stderr)
    return subprocess.run(cmd, check=True, text=True, capture_output=True, **kw).stdout


def mp3_duration(path):
    secs = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).strip())
    s = int(round(secs))
    h, m, s = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def slugify(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:60]


def upload_release(tag, title, files, notes):
    try:
        run(["gh", "release", "view", tag, "-R", f"{OWNER}/{REPO}"])
        run(["gh", "release", "upload", tag, *files, "--clobber", "-R", f"{OWNER}/{REPO}"])
    except subprocess.CalledProcessError:
        run(["gh", "release", "create", tag, *files, "-R", f"{OWNER}/{REPO}", "--title", title, "--notes", notes, "--target", "main"])
    return {os.path.basename(f): f"{GH_REPO}/releases/download/{tag}/{os.path.basename(f)}" for f in files}


def rfc2822(date_str):
    d = dt.datetime.strptime(date_str, "%Y-%m-%d").replace(hour=12, tzinfo=dt.timezone.utc)
    return email.utils.format_datetime(d)


def build_feed(eps):
    c = CHANNEL
    items = []
    for e in eps:
        desc_html = "".join(f"<p>{html.escape(p)}</p>" for p in e["description"].split("\n\n") if p.strip())
        links = f'<p>Original lecture (Arabic): <a href="{html.escape(e["source_url"])}">{html.escape(e["source_url"])}</a></p>'
        if e.get("pdf_url"):
            links += f'<p>Written translation (PDF): <a href="{html.escape(e["pdf_url"])}">{html.escape(e["pdf_url"])}</a></p>'
        full_html = desc_html + links
        plain = e["description"] + f"\n\nOriginal lecture (Arabic): {e['source_url']}" + (f"\nWritten translation (PDF): {e['pdf_url']}" if e.get("pdf_url") else "")
        items.append(f"""    <item>
      <title>{escape(e['title'])}</title>
      <description><![CDATA[{full_html}]]></description>
      <content:encoded><![CDATA[{full_html}]]></content:encoded>
      <itunes:summary>{escape(plain)}</itunes:summary>
      <link>{escape(e['source_url'])}</link>
      <guid isPermaLink="false">{escape(e['guid'])}</guid>
      <pubDate>{rfc2822(e['date'])}</pubDate>
      <enclosure url="{escape(e['mp3_url'])}" length="{e['length']}" type="audio/mpeg"/>
      <itunes:duration>{e['duration']}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:image href="{SITE}/cover.png"/>
    </item>""")
    last = rfc2822(eps[0]["date"]) if eps else email.utils.format_datetime(dt.datetime.now(dt.timezone.utc))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(c['title'])}</title>
    <link>{SITE}/</link>
    <atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/>
    <description>{escape(c['summary'])}</description>
    <language>en</language>
    <copyright>Original lectures belong to their speaker and channel ({YT}). Unofficial translation.</copyright>
    <lastBuildDate>{email.utils.format_datetime(dt.datetime.now(dt.timezone.utc))}</lastBuildDate>
    <pubDate>{last}</pubDate>
    <image>
      <url>{SITE}/cover.png</url>
      <title>{escape(c['title'])}</title>
      <link>{SITE}/</link>
    </image>
    <itunes:author>{escape(c['author'])}</itunes:author>
    <itunes:summary>{escape(c['summary'])}</itunes:summary>
    <itunes:owner>
      <itunes:name>{escape(c['owner_name'])}</itunes:name>
    </itunes:owner>
    <itunes:image href="{SITE}/cover.png"/>
    <itunes:category text="Religion &amp; Spirituality">
      <itunes:category text="Islam"/>
    </itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
{chr(10).join(items)}
  </channel>
</rss>
"""


def build_index(eps):
    c = CHANNEL
    rows = []
    for e in eps:
        pdf = f' · <a href="{html.escape(e["pdf_url"])}">PDF translation</a>' if e.get("pdf_url") else ""
        rows.append(f"""<li><h3>{html.escape(e['title'])}</h3>
<p class="meta">{html.escape(e['date'])} · {html.escape(e['duration'])}</p>
<audio controls preload="none" src="{html.escape(e['mp3_url'])}"></audio>
<p><a href="{html.escape(e['mp3_url'])}">Download MP3</a>{pdf} · <a href="{html.escape(e['source_url'])}">Original lecture (YouTube)</a></p>
<p>{html.escape(e['description'].split(chr(10)+chr(10))[0])}</p></li>""")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(c['title'])}</title>
<link rel="alternate" type="application/rss+xml" title="{html.escape(c['title'])}" href="feed.xml">
<style>body{{font-family:Georgia,serif;max-width:720px;margin:2rem auto;padding:0 1rem;color:#222;line-height:1.55}}
img{{width:180px;border-radius:6px}}audio{{width:100%}}ul{{list-style:none;padding:0}}li{{border-top:1px solid #ddd;padding:1rem 0}}.meta{{color:#777;margin:0}}code{{background:#f3f3f3;padding:2px 4px}}</style></head>
<body><img src="cover.png" alt="cover">
<h1>{html.escape(c['title'])}</h1>
<p>{html.escape(c['summary'])}</p>
<p><strong>Subscribe:</strong> add this feed URL in your podcast app: <code>{SITE}/feed.xml</code> · <a href="feed.xml">RSS feed</a></p>
<h2>Episodes</h2><ul>
{chr(10).join(rows)}
</ul></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mp3", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD (lecture upload date)")
    ap.add_argument("--description", required=True, help="text, or @path to a text file (paragraphs separated by blank lines)")
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--pdf")
    ap.add_argument("--slug")
    ap.add_argument("--duration", help="override itunes:duration (default: ffprobe)")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()

    desc = open(a.description[1:]).read().strip() if a.description.startswith("@") else a.description
    slug = a.slug or os.path.splitext(os.path.basename(a.mp3))[0] or slugify(a.title)
    tag = f"ep-{slug}"

    if not os.path.isdir(CLONE):
        run(["gh", "repo", "clone", f"{OWNER}/{REPO}", CLONE])
    run(["git", "-C", CLONE, "pull", "--ff-only"])

    files = [a.mp3] + ([a.pdf] if a.pdf else [])
    urls = upload_release(tag, a.title, files, f"{a.title}\n\nOriginal: {a.source_url}")

    ep = {
        "slug": slug,
        "guid": f"{REPO}:{slug}",
        "title": a.title,
        "date": a.date,
        "description": desc,
        "source_url": a.source_url,
        "mp3_url": urls[os.path.basename(a.mp3)],
        "length": os.path.getsize(a.mp3),
        "duration": a.duration or mp3_duration(a.mp3),
        "pdf_url": urls.get(os.path.basename(a.pdf)) if a.pdf else None,
    }
    jpath = os.path.join(CLONE, "episodes.json")
    eps = json.load(open(jpath)) if os.path.exists(jpath) else []
    eps = [e for e in eps if e["slug"] != slug] + [ep]
    eps.sort(key=lambda e: e["date"], reverse=True)
    json.dump(eps, open(jpath, "w"), indent=2, ensure_ascii=False)
    open(os.path.join(CLONE, "feed.xml"), "w").write(build_feed(eps))
    open(os.path.join(CLONE, "index.html"), "w").write(build_index(eps))

    run(["git", "-C", CLONE, "add", "episodes.json", "feed.xml", "index.html"])
    run(["git", "-C", CLONE, "commit", "-m", f"Add episode: {a.title}"])
    if not a.no_push:
        run(["git", "-C", CLONE, "push", "origin", "HEAD:main"])
    print(json.dumps(ep, indent=2))


if __name__ == "__main__":
    main()
