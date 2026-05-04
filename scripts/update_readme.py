#!/usr/bin/env python3
"""Auto-update profile README.md with latest repo data from GitHub API."""

import json
import urllib.request
import os
import re

GITHUB_USER = "dechang64"
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "repos-config.json")
README_PATH = os.path.join(os.path.dirname(__file__), "..", "README.md")

REPO_START = "<!-- AUTO-GENERATED-START -->"
REPO_END = "<!-- AUTO-GENERATED-END -->"
STATS_START = "<!-- STATS-AUTO-START -->"
STATS_END = "<!-- STATS-AUTO-END -->"

STATS_PRIMARY_URL = (
    "https://github-readme-stats.vercel.app/api"
    f"?username={GITHUB_USER}&show_icons=true&theme=tokyonight&hide_border=true&count_private=true"
)
STATS_LANGS_URL = (
    "https://github-readme-stats.vercel.app/api/top-langs/"
    f"?username={GITHUB_USER}&layout=compact&theme=tokyonight&hide_border=true&langs_count=8"
)
STATS_STREAK_URL = (
    f"https://streak-stats.demolab.com?user={GITHUB_USER}&theme=tokyonight&hide_border=true"
)
STATS_SKILLS_ICONS = (
    "https://skillicons.dev/icons?i=rust,python,pytorch,docker,git,linux,"
    "grpc,react,streamlit,sqlite&theme=dark"
)


def fetch_repos():
    """Fetch all non-fork repos via GitHub API."""
    url = f"https://api.github.com/users/{GITHUB_USER}/repos?per_page=100&type=owner&sort=updated"
    req = urllib.request.Request(url, headers={"User-Agent": "update-profile-bot"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"token {token}")
    with urllib.request.urlopen(req) as resp:
        return [r for r in json.loads(resp.read()) if not r["fork"]]


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def star_badge(count):
    if count == 0:
        return ""
    return f" ⭐{count}"


def check_url(url, timeout=5):
    """Return True if URL returns HTTP 200."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "stats-check"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status == 200
    except Exception:
        return False


def generate_stats():
    """Detect which stats service is available and generate markdown."""
    if check_url(STATS_PRIMARY_URL):
        return (
            f'<img src="{STATS_PRIMARY_URL}" width="48%"/>\n'
            f'<img src="{STATS_LANGS_URL}" width="48%"/>'
        )
    # Fallback: streak + skill icons
    return (
        f'<img src="{STATS_STREAK_URL}" width="48%"/>\n'
        f'<img src="{STATS_SKILLS_ICONS}" width="48%"/>'
    )


def generate_section(title, repo_names, repo_map, config):
    """Generate a markdown table for one category."""
    desc_overrides = config.get("descriptions", {})
    rows = []
    for name in repo_names:
        if name not in repo_map:
            continue
        r = repo_map[name]
        desc = desc_overrides.get(name) or r.get("description") or ""
        lang = r.get("language") or ""
        badge = star_badge(r.get("stargazers_count", 0))
        link = f"[**{name}**](https://github.com/{GITHUB_USER}/{name})"
        cols = [link, desc]
        if lang:
            cols.append(f"`{lang}`")
        if badge:
            cols.append(badge)
        rows.append("| " + " | ".join(cols) + " |")

    if not rows:
        return ""

    header = "| 项目 | 简介 |"
    sep = "|------|------|"
    has_lang = any(repo_map.get(n, {}).get("language") for n in repo_names if n in repo_map)
    has_stars = any(repo_map.get(n, {}).get("stargazers_count", 0) > 0 for n in repo_names if n in repo_map)
    if has_lang:
        header += " 语言 |"
        sep += "------|"
    if has_stars:
        header += " ⭐ |"
        sep += "----|"

    return f"### {title}\n\n{header}\n{sep}\n" + "\n".join(rows)


def generate_uncategorized(repos, config):
    """Generate table for repos not in any category."""
    categorized = set()
    for names in config["categories"].values():
        categorized.update(names)
    categorized.update(config.get("exclude", []))
    uncat = [r for r in repos if r["name"] not in categorized]
    if not uncat:
        return ""

    desc_overrides = config.get("descriptions", {})
    rows = []
    for r in uncat:
        desc = desc_overrides.get(r["name"]) or r.get("description") or ""
        lang = r.get("language") or ""
        badge = star_badge(r.get("stargazers_count", 0))
        link = f"[**{r['name']}**](https://github.com/{GITHUB_USER}/{r['name']})"
        cols = [link, desc]
        if lang:
            cols.append(f"`{lang}`")
        if badge:
            cols.append(badge)
        rows.append("| " + " | ".join(cols) + " |")

    header = "| 项目 | 简介 |"
    sep = "|------|------|"
    has_lang = any(r.get("language") for r in uncat)
    has_stars = any(r.get("stargazers_count", 0) > 0 for r in uncat)
    if has_lang:
        header += " 语言 |"
        sep += "------|"
    if has_stars:
        header += " ⭐ |"
        sep += "----|"

    return f"### 📦 其他项目\n\n{header}\n{sep}\n" + "\n".join(rows)


def replace_section(text, start, end, content):
    """Replace content between markers."""
    pattern = re.escape(start) + r".*?" + re.escape(end)
    replacement = start + "\n" + content + "\n" + end
    new_text, count = re.subn(pattern, replacement, text, flags=re.DOTALL)
    if count == 0:
        print(f"WARNING: Markers {start}...{end} not found")
        return text, False
    return new_text, True


def main():
    repos = fetch_repos()
    repo_map = {r["name"]: r for r in repos}
    config = load_config()

    # Generate repo sections
    sections = []
    for cat_name, repo_names in config["categories"].items():
        section = generate_section(cat_name, repo_names, repo_map, config)
        if section:
            sections.append(section)

    uncategorized = generate_uncategorized(repos, config)
    if uncategorized:
        sections.append(uncategorized)

    repo_content = "\n\n---\n\n".join(sections)

    # Generate stats
    stats_content = generate_stats()

    # Read and update README
    with open(README_PATH, "r") as f:
        readme = f.read()

    readme, ok1 = replace_section(readme, REPO_START, REPO_END, repo_content)
    readme, ok2 = replace_section(readme, STATS_START, STATS_END, stats_content)

    if not ok1 or not ok2:
        print("ERROR: Some markers not found in README.md")
        return

    with open(README_PATH, "w") as f:
        f.write(readme)

    print(f"README updated — {len(repos)} repos, {len(sections)} categories, stats generated")


if __name__ == "__main__":
    main()
