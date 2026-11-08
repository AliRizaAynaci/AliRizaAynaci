#!/usr/bin/env python3
"""Render self-contained GitHub activity SVG from authenticated public GraphQL data.

Uses only Python's standard library and GitHub Actions' built-in GITHUB_TOKEN.
"""
import argparse
import datetime as dt
import html
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

USERNAME = 'AliRizaAynaci'
OUT = Path(__file__).resolve().parents[1] / 'assets' / 'activity.svg'
W, H = 920, 488

QUERY = '''
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: [OWNER], privacy: PUBLIC) {
      totalCount
      nodes {
        name
        isFork
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
  }
}
'''

COLORS = {
    'Go': '#2CC5E9', 'Java': '#FFAE43', 'JavaScript': '#F4DC62',
    'Python': '#5E9FE2', 'TypeScript': '#4D85EE', 'C++': '#D778A5',
    'C': '#9096C9', 'C#': '#A77CF2', 'Kotlin': '#B06DEF', 'Rust': '#F18E65',
    'HTML': '#E56E49', 'CSS': '#6F82F5', 'Dart': '#39B8D8',
    'Shell': '#7FCA7B', 'Others': '#65748E',
}


def load_user_data():
    token = os.environ.get('GITHUB_TOKEN', '').strip()
    if not token:
        raise RuntimeError('GITHUB_TOKEN is missing. Run this from GitHub Actions or provide an authenticated token.')
    req = urllib.request.Request(
        'https://api.github.com/graphql',
        data=json.dumps({'query': QUERY, 'variables': {'login': USERNAME}}).encode(),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json',
                 'Accept': 'application/vnd.github+json', 'User-Agent': 'github-readme-activity-v1'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors='replace')[:500]
        raise RuntimeError(f'GitHub API failed ({exc.code}): {body}') from exc
    if data.get('errors'):
        raise RuntimeError('GitHub GraphQL errors: ' + json.dumps(data['errors'])[:700])
    user = data.get('data', {}).get('user')
    if not user:
        raise RuntimeError('GitHub GraphQL returned no user data')
    return user


def sample_data():
    """A clearly labeled local preview fixture. Never use in production workflow."""
    today = dt.date.today()
    start = today - dt.timedelta(days=(today.weekday() + 1) % 7 + 7 * 51)
    weeks = []
    for week in range(52):
        days = []
        for day in range(7):
            date = start + dt.timedelta(days=week * 7 + day)
            value = (week * 19 + day * 11 + (week * day * 3)) % 13
            count = 0 if value < 4 else (1 if value < 7 else (3 if value < 10 else 7))
            if date > today:
                count = 0
            days.append({'date': date.isoformat(), 'contributionCount': count})
        weeks.append({'contributionDays': days})
    repos = []
    for j in range(42):
        lang = [['Go', 35000], ['Java', 18000], ['JavaScript', 9000], ['C++', 4200], ['Python', 1500]][j % 5]
        repos.append({'name': f'demo-repo-{j}', 'isFork': False, 'stargazerCount': (j * 17) % 9,
                      'languages': {'edges': [{'size': lang[1], 'node': {'name': lang[0]}}]}})
    return {'repositories': {'totalCount': 42, 'nodes': repos},
            'contributionsCollection': {'contributionCalendar': {'totalContributions': 714, 'weeks': weeks}}}


def t(value, x, y, size=18, color='#F0F6FC', weight=500, anchor=None, spacing=None):
    extra = (f' text-anchor="{anchor}"' if anchor else '')
    extra += (f' letter-spacing="{spacing}"' if spacing else '')
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'font-family="Arial,Helvetica,sans-serif" fill="{color}"{extra}>'
            f'{html.escape(str(value))}</text>')


def r(x, y, w, h, fill, radius=0, stroke=None, opacity=None):
    extra = f' stroke="{stroke}"' if stroke else ''
    extra += f' opacity="{opacity}"' if opacity is not None else ''
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'rx="{radius}" fill="{fill}"{extra}/>')


def render(user, demo=False):
    repos = user['repositories']
    nodes = repos.get('nodes', [])
    calendar = user['contributionsCollection']['contributionCalendar']
    weeks = calendar['weeks'][-52:]
    contributions = calendar['totalContributions']
    stars = sum(int(repo.get('stargazerCount', 0)) for repo in nodes if not repo.get('isFork'))
    public_count = repos['totalCount']

    language_totals = {}
    for repo in nodes:
        if repo.get('isFork'):
            continue
        for edge in repo.get('languages', {}).get('edges', []):
            name = edge['node']['name']
            language_totals[name] = language_totals.get(name, 0) + edge['size']
    ordered = sorted(language_totals.items(), key=lambda kv: kv[1], reverse=True)
    top_languages = ordered[:4]
    others = sum(v for _, v in ordered[4:])
    if others:
        top_languages.append(('Others', others))
    total_bytes = sum(v for _, v in ordered)

    updated = dt.datetime.now(dt.timezone.utc).strftime('%d %b %Y, %H:%M UTC')
    parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="920" height="488" viewBox="0 0 920 488" role="img" aria-label="GitHub Activity Dashboard">
    <defs>
      <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1">
        <stop stop-color="#111C2C"/><stop offset="1" stop-color="#0C131E"/>
      </linearGradient>
      <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
        <stop stop-color="#2C86EE"/><stop offset="1" stop-color="#26C4D8"/>
      </linearGradient>
      <clipPath id="bar"><rect x="39" y="417" width="842" height="11" rx="5.5"/></clipPath>
    </defs>''',
             r(1,1,918,486,'url(#panel)',15,'#334154'),
             r(30,28,4,30,'url(#accent)',2),
             t('GitHub Activity',50,52,23,'#F1F5FC',750),
             t('AUTO-UPDATED  ·  PUBLIC ACTIVITY',888,48,10.5,'#7E95B3',700,'end',1.1)]
    if demo:
        parts.append(t('DESIGN PREVIEW · SAMPLE DATA',888,64,10,'#FFB65E',700,'end'))

    stats = [('CONTRIBUTIONS',f'{contributions:,}','LAST 12 MONTHS','#43B9FF'),
             ('PUBLIC REPOSITORIES',f'{public_count:,}','OWNED PUBLIC REPOS','#7B9EFF'),
             ('STARS RECEIVED',f'{stars:,}','ON NON-FORK REPOS','#FFC86B')]
    for i,(label,value,sub,color) in enumerate(stats):
        x=29+i*292
        parts.extend([
            r(x,79,278,105,'#141F2F',12,'#304259'),
            r(x+16,95,4,70,color,2),
            t(label,x+30,105,13,'#9BB1CC',700,spacing='.8'),
            t(value,x+30,146,35,'#F7FAFF',750),
            t(sub,x+32,168,12,'#7794B5',600,spacing='.6')])

    parts += [t('Contribution Heatmap',35,220,19,'#E7EFFC',750),
              t('LAST 52 WEEKS',887,219,11,'#84A6D1',700,'end',1.1),
              r(28,232,864,149,'#111927',12,'#2D4057')]

    # A complete week starts on Sunday, and rows correspond to Sunday-Saturday.
    start_x, start_y, step, sq = 51,268,15.45,11.5
    palette = ['#1A2A3D','#173F54','#146A76','#18A5AB','#2ED9BE']
    day_labels = [('S',0),('M',1),('T',2),('W',3),('T',4),('F',5),('S',6)]
    for letter,day in day_labels:
        if day in (1,3,5):
            parts.append(t(letter,36,start_y+day*13.7+9,10,'#7A91AC',650,'middle'))

    last_month=None
    for wi, week in enumerate(weeks):
        days=week['contributionDays']
        if days:
            d = dt.date.fromisoformat(days[0]['date'])
            if d.month != last_month:
                parts.append(t(d.strftime('%b'),start_x+wi*step,252,10,'#8E9FB9',600))
                last_month=d.month
        for di, day in enumerate(days[:7]):
            n = day['contributionCount']
            level = 0 if n == 0 else 1 if n < 2 else 2 if n < 4 else 3 if n < 8 else 4
            parts.append(r(f'{start_x+wi*step:.1f}',f'{start_y+di*13.7:.1f}',sq,sq,palette[level],2))

    parts += [t('Less',692,371,10,'#8095B1',500)]
    for i,c in enumerate(palette):
        parts.append(r(726+i*17,362,12,12,c,2))
    parts += [t('More',820,371,10,'#8095B1',500),
              t('Languages',35,402,19,'#E9F0F9',750),
              t('BASED ON PUBLIC REPOSITORY CODE SIZE',886,401,9.5,'#7E95B3',650,'end',0.7),
              r(39,417,842,11,'#1B2B3D',5.5)]

    if total_bytes:
        x=39.0
        for name,amount in top_languages:
            width=842 * amount / total_bytes
            color=COLORS.get(name, '#8290C5')
            parts.append(f'<g clip-path="url(#bar)">{r(f"{x:.2f}",417,f"{width:.2f}",11,color)}</g>')
            x+=width
        # Keep the legend readable; show each language and its share, with one row.
        for idx,(name,amount) in enumerate(top_languages[:5]):
            x=40+idx*172
            parts += [r(x,446,10,10,COLORS.get(name,'#8290C5'),5),
                      t(f'{name} {amount/total_bytes:.0%}',x+17,455,13,'#CDD9E9',600)]
    else:
        parts.append(t('No public repository language data',43,453,12,'#9BB1CC'))

    parts += [t('Updated '+updated,884,478,10,'#7286A2',500,'end'), '</svg>']
    return '\n'.join(parts)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--preview',action='store_true',help='render sample data ONLY for local design preview')
    p.add_argument('--output',type=Path,default=OUT)
    opts=p.parse_args()
    user=sample_data() if opts.preview else load_user_data()
    svg=render(user,demo=opts.preview)
    import xml.etree.ElementTree as ET
    ET.fromstring(svg)  # check SVG validity before overwriting the previous good output
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(svg,encoding='utf-8')
    print(f'Generated {opts.output} ({len(svg):,} characters)')

if __name__ == '__main__':
    main()
