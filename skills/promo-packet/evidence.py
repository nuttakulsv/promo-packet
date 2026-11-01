#!/usr/bin/env python3
"""Collect a year of your GitHub work into one evidence file for a promotion packet.

    python3 evidence.py                          last 12 months, you (whoever `gh` is logged in as)
    python3 evidence.py --since 2026-01-01 --org acme
    python3 evidence.py --user someone --json evidence.json
    python3 evidence.py --test

Needs the GitHub CLI (`gh`), logged in. Read-only: it only runs searches. Prints Markdown:
merged PRs by repository and theme, the biggest and most discussed ones, design docs, the reviews
you gave and whose work you reviewed, and the issues you opened. Everything links back to GitHub.
"""
import argparse
import collections
import datetime as dt
import json
import re
import subprocess
import sys

PR_FIELDS = """number title url createdAt mergedAt additions deletions changedFiles body
        repository { nameWithOwner } author { login }
        labels(first: 10) { nodes { name } } comments { totalCount } reviews { totalCount }
        files(first: 60) { nodes { path } }"""
QUERIES = {
    "authored": """query($q: String!, $after: String) { search(query: $q, type: ISSUE, first: 50, after: $after) {
      issueCount pageInfo { hasNextPage endCursor } nodes { ... on PullRequest { %s } } } }""" % PR_FIELDS,
    "reviewed": """query($q: String!, $after: String, $login: String!) { search(query: $q, type: ISSUE, first: 50, after: $after) {
      issueCount pageInfo { hasNextPage endCursor } nodes { ... on PullRequest {
        number title url createdAt mergedAt additions deletions repository { nameWithOwner } author { login }
        reviews(author: $login, first: 20) { totalCount nodes { state submittedAt bodyText comments { totalCount } } } } } } }""",
    "issues": """query($q: String!, $after: String) { search(query: $q, type: ISSUE, first: 50, after: $after) {
      issueCount pageInfo { hasNextPage endCursor } nodes { ... on Issue {
        number title url createdAt closedAt state repository { nameWithOwner }
        comments { totalCount } reactions { totalCount } labels(first: 10) { nodes { name } } } } } }""",
}

FILE_KINDS = [(kind, re.compile(rx)) for kind, rx in [
    # a design folder or a numbered RFC/ADR, not every README tweak
    ("design and docs", r"(?i)(^|/)(docs?|rfcs?|adrs?|design|architecture)/.*\.(md|mdx|rst|adoc)$|(^|/)(rfc|adr)[-_]?\d+[^/]*\.(md|mdx|rst)$"),
    ("tests", r"(^|/)(tests?|__tests__|specs?|e2e)/|(_test|\.test|\.spec|_spec)\.\w+$|(^|/)test_[^/]+$"),
    ("ci and infrastructure", r"^\.github/|(^|/)(Dockerfile|docker-compose[^/]*|Jenkinsfile|\.gitlab-ci\.yml)$|\.(tf|hcl)$"
                              r"|(^|/)(k8s|helm|charts|deploy|infra|terraform|ansible)/"),
    ("database migrations", r"(^|/)(migrations?|migrate|alembic)/|\.sql$"),
]]
# Thai has no spaces between words, so these match anywhere in the title
THAI = {
    "Reliability and operations": "ล่ม|แจ้งเตือน|มอนิเตอร์|ระบบล้ม|กู้คืน|ลองใหม่",
    "Performance and cost": "เร็วขึ้น|ช้า|แคช|ประสิทธิภาพ|ลดต้นทุน|ลดค่าใช้จ่าย",
    "Security and privacy": "ความปลอดภัย|สิทธิ์|เข้ารหัส|ช่องโหว่|ข้อมูลส่วนบุคคล|pdpa",
    "Migrations and deprecations": "ย้าย|อัปเกรด|อัพเกรด|เลิกใช้|ระบบเก่า",
    "Developer experience": "เทสต์|ทดสอบ|เครื่องมือ|สคริปต์",
    "Architecture and design": "ออกแบบ|โครงสร้าง|สถาปัตยกรรม|รีแฟกเตอร์|แยกโมดูล",
    "Features": "เพิ่ม|รองรับ|ฟีเจอร์|ใหม่",
    "Fixes": "แก้|บั๊ก|ผิดพลาด",
}
THEMES = [(theme, re.compile(rx + "|" + THAI[theme], re.I)) for theme, rx in [
    ("Reliability and operations", r"\b(incident|outage|postmortem|runbook|on-?call|alert\w*|monitor\w*|metric\w*|slo|sli"
                                   r"|observability|tracing|logging|retry|retries|timeout|rate.?limit|backoff|failover|rollback)\b"),
    ("Performance and cost", r"\b(perf\w*|latency|faster|speed\w*|slow|cache|caching|optimi[sz]\w*|memory|cpu|cost|n\+1|index(es)?)\b"),
    ("Security and privacy", r"\b(security|secur\w+|cve|vuln\w*|auth\w*|permission\w*|rbac|encrypt\w*|secret\w*|pii|gdpr|xss|csrf|sso)\b"),
    ("Migrations and deprecations", r"\b(migrat\w+|deprecat\w+|upgrade\w*|sunset|legacy|remove old|cut ?over|v\d+ to v\d+)\b"),
    ("Developer experience", r"\b(ci|build|lint\w*|tooling|scripts?|dx|developer|onboarding|local dev|devcontainer|flaky|test infra)\b"),
    ("Architecture and design", r"\b(rfc|adr|design|architecture|refactor\w*|extract\w*|split|modulari[sz]\w*|interface|api)\b"),
    ("Features", r"^(feat|feature)\b|\b(add|adds|added|support|introduce|new|launch)\b"),
    ("Fixes", r"^fix\b|\b(fix|fixes|fixed|bug|regression|broken|crash)\b"),
]]


def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"gh {' '.join(args[:2])} failed: {r.stderr.strip()[:400]}\n(Is `gh` installed and logged in? Try `gh auth status`.)")
    return r.stdout


def search(kind, q, limit, login=None):
    """All nodes for one search, following pages, up to limit."""
    nodes, after = [], None
    while len(nodes) < limit:
        args = ["api", "graphql", "-f", f"query={QUERIES[kind]}", "-f", f"q={q}"]
        if after:
            args += ["-f", f"after={after}"]
        if login:
            args += ["-f", f"login={login}"]
        data = json.loads(gh(*args))
        if data.get("errors"):
            raise SystemExit(f"GitHub returned an error: {data['errors'][0].get('message')}")
        page = data["data"]["search"]
        nodes += [n for n in page["nodes"] if n]
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    return nodes[:limit]


def collect(login, since, until, org, limit):
    scope = f" org:{org}" if org else ""
    window = f"{since}..{until}"
    return {
        "login": login, "since": since, "until": until, "org": org,
        "authored": search("authored", f"is:pr author:{login} is:merged merged:{window}{scope}", limit),
        "reviewed": search("reviewed", f"is:pr reviewed-by:{login} -author:{login} created:{window}{scope}", limit, login),
        "issues": search("issues", f"is:issue author:{login} created:{window}{scope}", limit),
    }


def file_kinds(pr):
    paths = [f["path"] for f in (pr.get("files") or {}).get("nodes") or []]
    return {kind for kind, rx in FILE_KINDS for p in paths if rx.search(p)}


def themes(pr):
    labels = " ".join(l["name"] for l in (pr.get("labels") or {}).get("nodes") or [])
    text = f"{pr.get('title', '')} {labels}"
    found = [t for t, rx in THEMES if rx.search(text)]
    if "design and docs" in file_kinds(pr) and "Architecture and design" not in found:
        found.append("Architecture and design")
    return found or ["Other"]


def link(n, with_repo=True):
    repo = n["repository"]["nameWithOwner"]
    return f"[{repo}#{n['number']}]({n['url']}) {n['title'].strip()[:90]}" if with_repo else f"[#{n['number']}]({n['url']}) {n['title'].strip()[:90]}"


def month(ts):
    return (ts or "")[:7]


def summarize(data):
    login, prs, reviewed, issues = data["login"], data["authored"], data["reviewed"], data["issues"]
    my_reviews = [(pr, r) for pr in reviewed for r in (pr.get("reviews") or {}).get("nodes") or []]
    repos = collections.Counter(p["repository"]["nameWithOwner"] for p in prs)
    orgs = {r.split("/")[0] for r in repos}
    review_repos = collections.Counter(p["repository"]["nameWithOwner"] for p in reviewed)
    authors = collections.Counter((p.get("author") or {}).get("login") or "ghost" for p in reviewed)
    adds, dels = sum(p.get("additions") or 0 for p in prs), sum(p.get("deletions") or 0 for p in prs)

    out = [f"# Evidence: @{login}, {data['since']} to {data['until']}" + (f" (org: {data['org']})" if data.get("org") else ""), "",
           f"Collected from GitHub on {dt.date.today().isoformat()}. This only covers what GitHub can see. Design docs elsewhere,",
           "incidents you led, mentoring, hiring and cross-team alignment won't show up unless they left a trace here.", "",
           "## At a glance", "",
           f"- {len(prs)} PRs merged across {len(repos)} repositories in {len(orgs)} organisation(s)",
           f"- +{adds:,} / -{dels:,} lines (includes generated files and lockfiles, so treat as rough)",
           f"- {len(my_reviews)} reviews on {len(reviewed)} other people's PRs, by {len(authors)} different authors",
           f"- {len(issues)} issues opened ({sum(i.get('state') == 'OPEN' for i in issues)} still open)", ""]

    months = sorted({month(p.get("mergedAt")) for p in prs} | {month(r.get("submittedAt")) for _, r in my_reviews} - {""})
    if months:
        merged_by = collections.Counter(month(p.get("mergedAt")) for p in prs)
        reviews_by = collections.Counter(month(r.get("submittedAt")) for _, r in my_reviews)
        out += ["| Month | PRs merged | Reviews given |", "|---|---|---|"]
        out += [f"| {m} | {merged_by[m]} | {reviews_by[m]} |" for m in months] + [""]

    if repos:
        out += ["## Where the work went", "", "| Repository | PRs merged | Lines +/- | Reviews given |", "|---|---|---|---|"]
        for repo in sorted(set(repos) | set(review_repos), key=lambda r: (-repos[r], -review_repos[r])):
            a = sum(p.get("additions") or 0 for p in prs if p["repository"]["nameWithOwner"] == repo)
            d = sum(p.get("deletions") or 0 for p in prs if p["repository"]["nameWithOwner"] == repo)
            out.append(f"| {repo} | {repos[repo]} | +{a:,} / -{d:,} | {review_repos[repo]} |")
        only_review = sorted(set(review_repos) - set(repos))
        if only_review:
            out += ["", "Repositories where you reviewed but didn't merge anything (influence outside your own code): "
                    + ", ".join(f"{r} ({review_repos[r]})" for r in only_review)]
        out.append("")

    by_theme = collections.defaultdict(list)
    for p in prs:
        for t in themes(p):
            by_theme[t].append(p)
    if by_theme:
        out += ["## Themes", "", "Guessed from titles, labels and files. Check them: one PR can sit in several.", ""]
        order = [t for t, _ in THEMES] + ["Other"]
        for t in sorted(by_theme, key=order.index):
            items = sorted(by_theme[t], key=lambda p: -((p.get("additions") or 0) + (p.get("deletions") or 0)))
            out += [f"### {t} ({len(items)})", ""] + [f"- {link(p)}" for p in items[:8]]
            out += ([f"- ...and {len(items) - 8} more"] if len(items) > 8 else []) + [""]

    if prs:
        size = lambda p: (p.get("additions") or 0) + (p.get("deletions") or 0)  # noqa: E731
        out += ["## Biggest changes", ""]
        out += [f"- {link(p)} (+{p.get('additions', 0):,}/-{p.get('deletions', 0):,}, {p.get('changedFiles', 0)} files, "
                f"merged {(p.get('mergedAt') or '')[:10]})" for p in sorted(prs, key=size, reverse=True)[:10]] + [""]
        talk = lambda p: (p.get("comments") or {}).get("totalCount", 0) + (p.get("reviews") or {}).get("totalCount", 0)  # noqa: E731
        discussed = [p for p in sorted(prs, key=talk, reverse=True)[:10] if talk(p)]
        if discussed:
            out += ["## Most discussed", "", "Often the ones that needed alignment, not just code.", ""]
            out += [f"- {link(p)} ({talk(p)} comments and reviews)" for p in discussed] + [""]
        docs = [p for p in prs if "design and docs" in file_kinds(p)]
        if docs:
            out += ["## PRs with design docs or documentation", ""] + [f"- {link(p)}" for p in docs[:15]] + [""]
        infra = [p for p in prs if "ci and infrastructure" in file_kinds(p)]
        if infra:
            out += ["## PRs touching CI or infrastructure", ""] + [f"- {link(p)}" for p in infra[:10]] + [""]

    if reviewed:
        out += ["## Reviews you gave", "", "Whose work you reviewed most (likely people who can speak to your influence):", ""]
        out += [f"- @{a}: {n} PRs" for a, n in authors.most_common(10)] + [""]
        states = collections.Counter(r.get("state") for _, r in my_reviews)
        out += ["Review outcomes: " + ", ".join(f"{s.lower().replace('_', ' ')} {n}" for s, n in states.most_common()), ""]
        weight = lambda pr_r: len(pr_r[1].get("bodyText") or "") + 200 * (pr_r[1].get("comments") or {}).get("totalCount", 0)  # noqa: E731
        deep = [x for x in sorted(my_reviews, key=weight, reverse=True)[:10] if weight(x) >= 400]
        if deep:
            out += ["Your most substantial reviews:", ""]
            out += [f"- {link(pr)} ({(r.get('comments') or {}).get('totalCount', 0)} comments) "
                    + (f"\"{' '.join((r.get('bodyText') or '').split())[:140]}\"" if r.get("bodyText") else "") for pr, r in deep] + [""]

    if issues:
        out += ["## Issues you opened", ""]
        out += [f"- {link(i)} ({i.get('state', '').lower()}, {(i.get('comments') or {}).get('totalCount', 0)} comments)"
                for i in sorted(issues, key=lambda i: -(i.get("comments") or {}).get("totalCount", 0))[:15]] + [""]

    out += ["## Not in here", "",
            "Fill these in yourself. They're often what decides a staff promotion:", "",
            "- Incidents you led or helped resolve, and what changed afterwards",
            "- Design docs, RFCs and decisions written outside GitHub",
            "- People you mentored, onboarded or interviewed",
            "- Cross-team work: projects you aligned, conflicts you resolved, things you stopped",
            "- Impact numbers: latency, cost, revenue, tickets, time saved (from dashboards, not from memory)", ""]
    return "\n".join(out)


def main(argv):
    today = dt.date.today()
    p = argparse.ArgumentParser(description="Collect your GitHub work into one evidence file.")
    p.add_argument("--user", help="GitHub login (default: whoever gh is logged in as)")
    p.add_argument("--since", default=(today - dt.timedelta(days=365)).isoformat(), help="YYYY-MM-DD (default: a year ago)")
    p.add_argument("--until", default=today.isoformat(), help="YYYY-MM-DD (default: today)")
    p.add_argument("--org", help="only this GitHub organisation")
    p.add_argument("--max", type=int, default=500, help="max items per search (default 500)")
    p.add_argument("--json", metavar="FILE", help="also save the raw data here")
    a = p.parse_args(argv)
    for d in (a.since, a.until):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            raise SystemExit(f"dates look like 2026-01-31, got {d!r}")
    if a.org and not re.fullmatch(r"[\w.-]+", a.org):
        raise SystemExit(f"that doesn't look like an organisation name: {a.org!r}")
    login = a.user or gh("api", "user", "--jq", ".login").strip()
    if not re.fullmatch(r"[\w-]+", login):
        raise SystemExit(f"that doesn't look like a GitHub login: {login!r}")
    print(f"Collecting GitHub activity for @{login}, {a.since} to {a.until} ...", file=sys.stderr)
    data = collect(login, a.since, a.until, a.org, a.max)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(data, fh, indent=1)
    print(summarize(data))


def test():
    def pr(n, repo, title, add, dele, merged, files=(), comments=0, reviews=0, author="me", labels=()):
        return {"number": n, "title": title, "url": f"https://github.com/{repo}/pull/{n}", "mergedAt": merged,
                "additions": add, "deletions": dele, "changedFiles": len(files) or 1, "repository": {"nameWithOwner": repo},
                "author": {"login": author}, "labels": {"nodes": [{"name": l} for l in labels]},
                "comments": {"totalCount": comments}, "reviews": {"totalCount": reviews}, "files": {"nodes": [{"path": f} for f in files]}}

    data = {"login": "me", "since": "2025-11-01", "until": "2026-11-01", "org": None,
            "authored": [pr(1, "acme/api", "Add retries with backoff to the payment client", 120, 10, "2026-01-10T00:00:00Z",
                            ["src/pay.ts", "src/pay.test.ts"]),
                         pr(2, "acme/api", "RFC: split the monolith's billing module", 400, 0, "2026-02-01T00:00:00Z",
                            ["docs/rfcs/012-billing.md"], comments=31, reviews=6),
                         pr(3, "acme/infra", "Cut CI time from 25 to 9 minutes", 80, 300, "2026-02-20T00:00:00Z",
                            [".github/workflows/ci.yml"], labels=["dx"]),
                         pr(4, "acme/web", "Tidy up", 3, 3, "2026-03-01T00:00:00Z", ["src/a.ts"]),
                         pr(5, "acme/web", "แก้ยอดรวมตะกร้าไม่ตรง", 4, 2, "2026-03-02T00:00:00Z", ["src/cart.ts"])],
            "reviewed": [{**pr(9, "acme/mobile", "New checkout screen", 900, 100, None, author="dana"),
                          "reviews": {"totalCount": 2, "nodes": [
                              {"state": "CHANGES_REQUESTED", "submittedAt": "2026-02-02T00:00:00Z",
                               "bodyText": "The retry here can double charge. " * 20, "comments": {"totalCount": 6}},
                              {"state": "APPROVED", "submittedAt": "2026-02-03T00:00:00Z", "bodyText": "", "comments": {"totalCount": 0}}]}},
                         {**pr(10, "acme/api", "Fix typo", 1, 1, None, author="dana"),
                          "reviews": {"totalCount": 1, "nodes": [{"state": "APPROVED", "submittedAt": "2026-03-05T00:00:00Z",
                                                                   "bodyText": "", "comments": {"totalCount": 0}}]}}],
            "issues": [{"number": 7, "title": "Payments double charge on timeout", "url": "https://github.com/acme/api/issues/7",
                        "state": "CLOSED", "repository": {"nameWithOwner": "acme/api"}, "comments": {"totalCount": 12}}]}
    md = summarize(data)
    for want in ["5 PRs merged across 3 repositories in 1 organisation", "3 reviews on 2 other people's PRs, by 1 different authors",
                 "| 2026-02 | 2 | 2 |", "| acme/api | 2 | +520 / -10 | 1 |", "reviewed but didn't merge anything", "acme/mobile (1)",
                 "### Reliability and operations (1)", "### Architecture and design (1)", "### Developer experience (1)",
                 "### Other (1)", "(37 comments and reviews)", "### Fixes (1)", "## PRs with design docs", "## PRs touching CI",
                 "- @dana: 2 PRs", "changes requested 1", "Your most substantial reviews", "(6 comments)",
                 "[acme/api#7](https://github.com/acme/api/issues/7)", "## Not in here"]:
        assert want in md, (want, md)
    assert "Tidy up" in md.split("### Other (1)")[1].split("###")[0]
    empty = summarize({"login": "me", "since": "a", "until": "b", "org": None, "authored": [], "reviewed": [], "issues": []})
    assert "0 PRs merged" in empty and "## Not in here" in empty
    print("ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        test()
    else:
        main(sys.argv[1:])
