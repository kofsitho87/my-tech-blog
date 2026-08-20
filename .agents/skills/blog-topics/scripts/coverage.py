"""Report blog coverage against product repository documentation and commits.

Usage:
    python3 coverage.py [product-repo-path]
"""

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


BLOG = Path("/Users/heewungsong/Desktop/Dan/my-tech-blog/src/content/blog")
CONFIG = Path("/Users/heewungsong/Desktop/Dan/my-tech-blog/src/content.config.ts")

REPOS = {
    "inbound": Path(
        "/Users/heewungsong/Desktop/Wise-Ai/Outbound-Agent-Project/inbound-agent"
    ),
    "outbound": Path(
        "/Users/heewungsong/Desktop/Wise-Ai/Outbound-Agent-Project/outbound-agent"
    ),
}

FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def frontmatter(path):
    match = FM.match(path.read_text(encoding="utf-8"))
    if not match:
        return None
    parsed = {}
    for line in match.group(1).splitlines():
        key_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$", line)
        if not key_match:
            continue
        key, value = key_match.group(1), key_match.group(2).strip()
        if value.startswith("[") and value.endswith("]"):
            value = [
                item.strip().strip("'\"")
                for item in value[1:-1].split(",")
                if item.strip()
            ]
        else:
            value = value.strip("'\"")
        parsed[key] = value
    return parsed


def vocabulary():
    config = CONFIG.read_text(encoding="utf-8")
    match = re.search(r"export const TOPICS = \[(.*?)\] as const", config, re.S)
    if not match:
        raise RuntimeError(f"Could not find TOPICS in {CONFIG}")
    return [
        line.strip().strip("',\"")
        for line in match.group(1).splitlines()
        if line.strip().startswith("'")
    ]


def published():
    articles = []
    for path in sorted(BLOG.glob("*.md*")):
        metadata = frontmatter(path)
        if metadata:
            metadata["slug"] = path.stem
            articles.append(metadata)
    return articles


def doc_title(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[:40]
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
        match = re.match(r"^title:\s*(.+)$", stripped)
        if match:
            return match.group(1).strip().strip("'\"")
    return "—"


def git(repo, *args):
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        return result.stdout if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def scan(repo, posts):
    label = next((key for key, path in REPOS.items() if path == repo), None)

    print()
    print("=" * 78)
    suffix = f"  [sourceRepo: {label}]" if label else "  [not a known product repo]"
    print(f"CANDIDATE MATERIAL  {repo}{suffix}")
    print("=" * 78)

    if label:
        matching = [article for article in posts if article.get("sourceRepo") == label]
        print(f"\nArticles already grounded in this repo ({len(matching)}):")
        for article in sorted(matching, key=lambda item: item.get("pubDate", "")):
            print(
                f"  {article.get('pubDate', '?')}  "
                f"{article['slug']:50} {article.get('topics')}"
            )

    docs = repo / "docs"
    if docs.is_dir():
        found = sorted(
            path for path in docs.rglob("*.md") if ".omc" not in path.parts
        )
        print(f"\nDocuments under docs/ ({len(found)}):")
        for path in found:
            relative = str(path.relative_to(repo))
            print(f"  {relative:58} {doc_title(path)[:70]}")

    log = git(repo, "log", "--no-merges", "-40", "--date=short", "--format=%ad  %s")
    if log:
        print("\nRecent commits (40):")
        for line in log.strip().splitlines():
            print(f"  {line[:100]}")


def main():
    if len(sys.argv) > 1:
        targets = [Path(sys.argv[1]).resolve()]
    else:
        cwd = Path.cwd().resolve()
        targets = [cwd] if cwd in REPOS.values() else list(REPOS.values())

    posts = published()
    topics = vocabulary()

    print("=" * 78)
    print(f"BLOG COVERAGE  ({len(posts)} articles)")
    print("=" * 78)

    by_topic = defaultdict(list)
    for article in posts:
        for topic in article.get("topics") or []:
            by_topic[topic].append(article)

    for topic in topics:
        articles = by_topic.get(topic, [])
        mark = "  " if articles else "??"
        print(f"{mark} {topic:22} {len(articles)}")
        for article in sorted(articles, key=lambda item: item.get("pubDate", "")):
            print(
                f"       {article.get('pubDate', '?')}  "
                f"[{article.get('lang', '?')}] {article['slug']}"
            )
    print("\n?? = no article carries this topic yet")

    drafts = [
        article
        for article in posts
        if str(article.get("draft", "")).lower() == "true"
    ]
    if drafts:
        print(f"\nDRAFTS ({len(drafts)}): " + ", ".join(a["slug"] for a in drafts))

    for repo in targets:
        scan(repo, posts)


if __name__ == "__main__":
    main()
