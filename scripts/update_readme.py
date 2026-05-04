#!/usr/bin/env python3
"""Auto-update profile README.md with latest repo data from GitHub API."""

import json
import urllib.request
import os
import re

GITHUB_USER = "dechang64"
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "repos-config.json")
README_PATH = os.path.join(os.path.dirname(__file__), "..", "README.md")

START_MARKER = "<!-- AUTO-GENERATED-START -->"
END_MARKER = "<!-- AUTO-GENERATED-END -->"


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
    separator = "|------|------|"
    # Check if any row has lang or stars
    has_lang = any(repo_map.get(n, {}).get("language") for n in repo_names if n in repo_map)
    has_stars = any(repo_map.get(n, {}).get("stargazers_count", 0) > 0 for n in repo_names if n in repo_map)
    if has_lang:
        header += " 语言 |"
        separator += "------|"
    if has_stars:
        header += " ⭐ |"
        separator += "----|"

    return f"### {title}\n\n{header}\n{separator}\n" + "\n".join(rows)


def generate_uncategorized(repos, config):
    """Generate table for repos not in any category."""
    categorized = set()
    for names in config["categories"].values():
        categorized.update(names)
    categorized.update(config.get("exclude", []))

    uncategorized = [r for r in repos if r["name"] not in categorized]
    if not uncategorized:
        return ""

    desc_overrides = config.get("descriptions", {})
    rows = []
    for r in uncategorized:
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
    separator = "|------|------|"
    has_lang = any(r.get("language") for r in uncategorized)
    has_stars = any(r.get("stargazers_count", 0) > 0 for r in uncategorized)
    if has_lang:
        header += " 语言 |"
        separator += "------|"
    if has_stars:
        header += " ⭐ |"
        separator += "----|"

    return f"### 📦 其他项目\n\n{header}\n{separator}\n" + "\n".join(rows)


def main():
    repos = fetch_repos()
    repo_map = {r["name"]: r for r in repos}
    config = load_config()

    sections = []
    for cat_name, repo_names in config["categories"].items():
        section = generate_section(cat_name, repo_names, repo_map, config)
        if section:
            sections.append(section)

    uncategorized = generate_uncategorized(repos, config)
    if uncategorized:
        sections.append(uncategorized)

    generated = "\n\n---\n\n".join(sections)

    # Read existing README and replace between markers
    with open(README_PATH, "r") as f:
        readme = f.read()

    pattern = re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER)
    replacement = START_MARKER + "\n\n" + generated + "\n\n" + END_MARKER

    new_readme, count = re.subn(pattern, replacement, readme, flags=re.DOTALL)
    if count == 0:
        print("ERROR: Markers not found in README.md")
        return

    with open(README_PATH, "w") as f:
        f.write(new_readme)

    print(f"README updated — {len(repos)} repos, {len(sections)} categories")


if __name__ == "__main__":
    main()
