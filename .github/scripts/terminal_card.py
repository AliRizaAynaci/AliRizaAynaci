#!/usr/bin/env python3
"""Generates metrics.terminal.svg: a small, hand-drawn terminal window
populated with live data pulled from the GitHub API. No third-party
rendering service is involved -- this script owns the whole SVG."""

import datetime
import json
import os
import sys
import urllib.request

USER = "AliRizaAynaci"
FEATURED_REPO = "gorl"
TOKEN = os.environ["GITHUB_TOKEN"]
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "metrics.terminal.svg")

API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"


def rest(path):
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": USER,
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def graphql(query):
    req = urllib.request.Request(
        GRAPHQL,
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": USER,
        },
    )
    with urllib.request.urlopen(req) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]


def fetch():
    user = rest(f"/users/{USER}")
    repo = rest(f"/repos/{USER}/{FEATURED_REPO}")

    created = datetime.datetime.strptime(user["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    now = datetime.datetime.utcnow()
    years = max(1, (now - created).days // 365)

    year_fields = "\n".join(
        f"""y{y}: contributionsCollection(
              from: "{y}-01-01T00:00:00Z"
              to: "{min(y + 1, now.year + 1)}-01-01T00:00:00Z"
            ) {{
              totalCommitContributions
              restrictedContributionsCount
              totalPullRequestReviewContributions
            }}"""
        for y in range(created.year, now.year + 1)
    )

    data = graphql(
        f"""
        query {{
          user(login: "{USER}") {{
            repositoriesContributedTo(contributionTypes: [COMMIT]) {{ totalCount }}
            pullRequests {{ totalCount }}
            issues {{ totalCount }}
            issueComments {{ totalCount }}
            {year_fields}
          }}
        }}
        """
    )["user"]

    commits = 0
    reviews = 0
    for y in range(created.year, now.year + 1):
        bucket = data[f"y{y}"]
        commits += bucket["totalCommitContributions"] + bucket["restrictedContributionsCount"]
        reviews += bucket["totalPullRequestReviewContributions"]

    return {
        "name": user.get("name") or USER,
        "uid": user["id"],
        "followers": user["followers"],
        "years": years,
        "contributed_repos": data["repositoriesContributedTo"]["totalCount"],
        "commits": commits,
        "reviews": reviews,
        "prs": data["pullRequests"]["totalCount"],
        "issues": data["issues"]["totalCount"],
        "issue_comments": data["issueComments"]["totalCount"],
        "repo_stars": repo["stargazers_count"],
    }


def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


PROMPT = f"{USER.lower()}@metrics"
GREEN = "#3fb950"
CYAN = "#58a6ff"
FG = "#c9d1d9"
DIM = "#6e7681"
BG = "#0d1117"
BORDER = "#30363d"


def line(text, color=FG, indent=0):
    return {"text": text, "color": color, "indent": indent}


def build_lines(d):
    bar = "#" * min(20, d["contributed_repos"])
    return [
        {"prompt": True, "cmd": "whoami"},
        line(f'{esc(d["name"])}  registered={d["years"]}y, uid={d["uid"]}, gid=0'),
        line(f'contributed to {d["contributed_repos"]} repositories {bar}', color=DIM, indent=1),
        line(f'followed by {d["followers"]} users', color=DIM, indent=1),
        line(""),
        {"prompt": True, "cmd": "git status"},
        line("Recent activity", color=GREEN),
        line(f'{d["commits"]} commits', indent=1),
        line(f'{d["reviews"]} pull requests reviewed', indent=1),
        line(f'{d["prs"]} pull requests opened', indent=1),
        line(f'{d["issues"]} issues opened', indent=1),
        line(f'{d["issue_comments"]} issue comments', indent=1),
        line(""),
        {"prompt": True, "cmd": f"cat {FEATURED_REPO}/STARS"},
        line(f'{FEATURED_REPO} ★ {d["repo_stars"]} stargazers · github.com/{USER}/{FEATURED_REPO}', color=CYAN),
    ]


def render(lines):
    width = 480
    pad_x = 18
    top_bar = 34
    line_h = 20
    pad_y = 16
    height = top_bar + pad_y * 2 + line_h * len(lines)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{top_bar}" rx="10" fill="#161b22"/>',
        f'<rect x="0.5" y="{top_bar - 10}" width="{width - 1}" height="10" fill="#161b22"/>',
        f'<line x1="0.5" y1="{top_bar}" x2="{width - 0.5}" y2="{top_bar}" stroke="{BORDER}"/>',
        '<circle cx="22" cy="17" r="6" fill="#ff5f56"/>',
        '<circle cx="42" cy="17" r="6" fill="#ffbd2e"/>',
        '<circle cx="62" cy="17" r="6" fill="#27c93f"/>',
        f'<text x="{width / 2}" y="21" text-anchor="middle" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="12" fill="{DIM}">{PROMPT}</text>',
        f'<g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="13" xml:space="preserve">',
    ]

    y = top_bar + pad_y + 12
    for item in lines:
        if item.get("prompt"):
            svg.append(
                f'<text x="{pad_x}" y="{y}">'
                f'<tspan fill="{GREEN}">{esc(PROMPT)}:~$ </tspan>'
                f'<tspan fill="{FG}">{esc(item["cmd"])}</tspan>'
                f'</text>'
            )
        else:
            x = pad_x + item["indent"] * 16
            svg.append(f'<text x="{x}" y="{y}" fill="{item["color"]}">{esc(item["text"])}</text>')
        y += line_h

    svg.append("</g>")
    svg.append("</svg>")
    return "\n".join(svg)


def main():
    data = fetch()
    svg = render(build_lines(data))
    out_path = os.path.abspath(OUT_PATH)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
