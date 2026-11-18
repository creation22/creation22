"""Redraw assets/banner.svg from live github data.

    GITHUB_TOKEN=$(gh auth token) python assets/banner.py

The numbers in the banner are baked in when it is generated, so rerun this
when they start to look old.
"""

import datetime as dt
import json
import os
import urllib.request

USER = "creation22"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "banner.svg")

SANS = "'Segoe UI',Inter,-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,'SF Mono',SFMono-Regular,'Cascadia Mono',Menlo,Consolas,monospace"
TAGLINES = ["build more.", "break more.", "fix more."]

QUERY = """
query($user: String!, $from: DateTime!, $to: DateTime!, $prevFrom: DateTime!, $prevTo: DateTime!) {
  user(login: $user) {
    now: contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
    prev: contributionsCollection(from: $prevFrom, to: $prevTo) {
      contributionCalendar { totalContributions }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      nodes { createdAt }
    }
  }
}
"""


def fetch():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("set GITHUB_TOKEN first")
    to = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)

    def iso(days_ago):
        return (to - dt.timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")

    variables = {
        "user": USER,
        "from": iso(364),
        "to": to.isoformat().replace("+00:00", "Z"),
        "prevFrom": iso(728),
        "prevTo": iso(365),
    }
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": "bearer " + token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.load(response)
    if "errors" in payload:
        raise SystemExit(payload["errors"])
    return payload["data"]["user"]


def stats(user):
    calendar = user["now"]["contributionCalendar"]
    days = [d for w in calendar["weeks"] for d in w["contributionDays"]]
    weeks = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in calendar["weeks"]]

    run = longest = 0
    for day in days:
        run = run + 1 if day["contributionCount"] else 0
        longest = max(longest, run)

    busiest = max(days, key=lambda d: d["contributionCount"])
    previous = user["prev"]["contributionCalendar"]["totalContributions"] or 1
    this_year = str(dt.date.today().year)
    started = sum(1 for r in user["repositories"]["nodes"] if r["createdAt"][:4] == this_year)

    return {
        "total": calendar["totalContributions"],
        "weeks": weeks,
        "multiple": calendar["totalContributions"] / previous,
        "streak": longest,
        "busiest": busiest["contributionCount"],
        "new_repos": started,
    }


def render(s):
    SX, SY, SW, SH = 578.0, 108.0, 372.0, 84.0
    values = s["weeks"]
    top = max(values) or 1
    points = [
        (round(SX + SW * i / (len(values) - 1), 1), round(SY + SH - SH * (v / top), 1))
        for i, v in enumerate(values)
    ]
    line = " ".join("{0},{1}".format(x, y) for x, y in points)
    area = "{0},{1} ".format(SX, SY + SH) + line + " {0},{1}".format(SX + SW, SY + SH)
    end_x, end_y = points[-1]
    length = int(
        sum(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in zip(points, points[1:])) + 20
    )

    # each tagline owns a 2s slot of a 6s loop; the first is visible with no
    # animation at all, so renderers that ignore SMIL still show something.
    cycle = []
    for i, word in enumerate(TAGLINES):
        begin = i * 2
        caret_x = round(52 + 16.25 * len(word) + 6, 1)
        on = 1 if i == 0 else 0
        cycle.append(
            '<text x="52" y="152" font-family="{mono}" font-size="27" font-weight="600" fill="#fb923c" opacity="{on}">{word}'
            '<animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.025;0.283;0.305;1" dur="6s" begin="{begin}s" repeatCount="indefinite"/>'
            '<animate attributeName="y" values="160;152;152;152" keyTimes="0;0.03;0.283;1" dur="6s" begin="{begin}s" repeatCount="indefinite"/></text>\n'
            '  <rect x="{caret_x}" y="131" width="2.5" height="25" fill="#fb923c" opacity="{on}">'
            '<animate attributeName="opacity" values="0;1;0;1;0;1;0;0" keyTimes="0;0.03;0.08;0.13;0.18;0.23;0.3;1" dur="6s" begin="{begin}s" repeatCount="indefinite"/></rect>'.format(
                mono=MONO, on=on, word=word, begin=begin, caret_x=caret_x
            )
        )

    grid = "".join(
        '<line x1="{0}" y1="0" x2="{0}" y2="250" stroke="#ffffff" stroke-opacity="0.025"/>'.format(x)
        for x in range(40, 1000, 40)
    ) + "".join(
        '<line x1="0" y1="{0}" x2="1000" y2="{0}" stroke="#ffffff" stroke-opacity="0.025"/>'.format(y)
        for y in range(40, 250, 40)
    )

    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 250" width="1000" height="250" role="img" aria-label="srajan gupta - build more, break more, fix more - {total:,} contributions in the last 52 weeks">
  <defs>
    <linearGradient id="spark" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#9a3412"/>
      <stop offset="55%" stop-color="#ea580c"/>
      <stop offset="100%" stop-color="#fb923c"/>
    </linearGradient>
    <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ea580c" stop-opacity="0.34"/>
      <stop offset="100%" stop-color="#ea580c" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#c2410c"/>
      <stop offset="100%" stop-color="#c2410c" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="card"><rect x="1" y="1" width="998" height="248" rx="18"/></clipPath>
  </defs>

  <rect x="1" y="1" width="998" height="248" rx="18" fill="#09090b"/>
  <g clip-path="url(#card)" opacity="0.5">{grid}</g>
  <rect x="1" y="1" width="998" height="248" rx="18" fill="none" stroke="#27272a"/>
  <rect x="1" y="1" width="998" height="3" rx="1.5" fill="url(#rule)" clip-path="url(#card)"/>

  <text x="52" y="94" font-family="{sans}" font-size="52" font-weight="700" fill="#fafafa" letter-spacing="-1.4">srajan gupta</text>
  {cycle}
  <text x="52" y="195" font-family="{sans}" font-size="16" fill="#8b949e">4th year cse · prayagraj · full-stack at uncensored · chess ~1700</text>

  <line x1="520" y1="48" x2="520" y2="202" stroke="#27272a"/>

  <text x="578" y="62" font-family="{mono}" font-size="12.5" fill="#8b949e" letter-spacing="1.4">CONTRIBUTIONS · LAST 52 WEEKS</text>
  <text x="578" y="100" font-family="{sans}" font-size="34" font-weight="700" fill="#fafafa">{total:,}</text>
  <text x="{multiple_x}" y="100" font-family="{sans}" font-size="14" fill="#8b949e">&#8599; {multiple:.1f}&#215; last year</text>

  <polygon points="{area}" fill="url(#fill)" opacity="1">
    <animate attributeName="opacity" values="0;0;1" keyTimes="0;0.55;1" dur="3s" fill="freeze"/>
  </polygon>
  <polyline points="{line}" fill="none" stroke="url(#spark)" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round" stroke-dasharray="{length}" stroke-dashoffset="0">
    <animate attributeName="stroke-dashoffset" dur="2.6s" begin="0.3s" fill="freeze" calcMode="spline" keySplines="0.22 1 0.36 1" keyTimes="0;1" values="{length};0"/>
  </polyline>
  <circle cx="{end_x}" cy="{end_y}" r="4" fill="#fb923c" opacity="1">
    <animate attributeName="r" values="4;7;4" dur="2.2s" begin="3.2s" repeatCount="indefinite"/>
  </circle>
  <circle cx="{end_x}" cy="{end_y}" r="4" fill="none" stroke="#fb923c" opacity="0">
    <animate attributeName="r" values="4;16" dur="2.2s" begin="3.2s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.7;0" dur="2.2s" begin="3.2s" repeatCount="indefinite"/>
  </circle>

  <text x="578" y="213" font-family="{mono}" font-size="12" fill="#6b7280">{streak}-day streak · best day {busiest} commits · {new_repos} new repos</text>
</svg>
""".format(
        sans=SANS,
        mono=MONO,
        grid=grid,
        cycle="\n  ".join(cycle),
        total=s["total"],
        multiple=s["multiple"],
        multiple_x=672 if s["total"] >= 1000 else 648,
        area=area,
        line=line,
        length=length,
        end_x=end_x,
        end_y=end_y,
        streak=s["streak"],
        busiest=s["busiest"],
        new_repos=s["new_repos"],
    )


if __name__ == "__main__":
    data = stats(fetch())
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(render(data))
    print(
        "wrote {0}: {1:,} contributions, {2}-day streak, best day {3}, {4} new repos".format(
            OUT, data["total"], data["streak"], data["busiest"], data["new_repos"]
        )
    )
