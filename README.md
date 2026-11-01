# promo-packet

[ภาษาไทย](README.th.md) · From the maker of [staff-katas](https://github.com/nuttakulsv/staff-katas) and [engineering-ladder-th](https://github.com/nuttakulsv/engineering-ladder-th)

Promotion season. You have a blank doc titled "Staff promotion case" and a vague feeling you did a lot this year. You scroll through GitHub trying to remember what that PR in March was about. You write "Worked on CI improvements." You delete it.

promo-packet is a skill for your coding agent, plus a script, that turns a year of work into an honest, evidence-backed promotion packet:

1. **Collects the evidence.** `evidence.py` pulls your year from GitHub: merged PRs grouped by repository and theme, the biggest and the most discussed ones, design docs, CI and infrastructure work, every review you gave and whose work you reviewed, and the issues you opened. Everything links back.
2. **Interviews you** for what GitHub can't see: the problem behind each project, what you decided, who else was involved, the numbers, the incidents you led, the people you mentored.
3. **Drafts the packet**: outcomes first, every claim linked to evidence or marked `[number needed]`. It never invents a number.
4. **Plays the skeptical committee**: rates each rubric dimension strong, some or thin, says where a story shows your current level rather than the target, and suggests a plan for the gaps.

## What the evidence looks like

```
$ python3 evidence.py --since 2025-11-01 --org acme

# Evidence: @you, 2025-11-01 to 2026-11-01 (org: acme)

## At a glance
- 143 PRs merged across 9 repositories in 1 organisation(s)
- 211 reviews on 167 other people's PRs, by 23 different authors
- 18 issues opened (6 still open)

| Month | PRs merged | Reviews given |
| 2025-11 | 14 | 22 |
...

## Where the work went
| acme/checkout | 61 | +18,204 / -9,880 | 40 |
...
Repositories where you reviewed but didn't merge anything (influence outside your own code):
acme/mobile (31), acme/search (12)

## Themes
### Reliability and operations (17)
- [acme/checkout#1841](...) Add idempotency keys to capture retries
...

## Most discussed
- [acme/platform#88](...) RFC: one queue for all async jobs (54 comments and reviews)

## Reviews you gave
Whose work you reviewed most (likely people who can speak to your influence):
- @dana: 38 PRs
...

## Not in here
Fill these in yourself. They're often what decides a staff promotion: ...
```

## Install

Claude Code:

```
/plugin marketplace add nuttakulsv/promo-packet
/plugin install promo-packet@promo-packet
```

Codex, Cursor, or anything else that reads SKILL.md:

```
npx skills add nuttakulsv/promo-packet
```

Then: "help me write my staff promotion packet". It asks for your target level, your company's ladder (or uses the [bundled rubric](skills/promo-packet/rubric.md)), and the period.

The evidence script works on its own too. It needs `python3` and the [GitHub CLI](https://cli.github.com/), logged in:

```
curl -O https://raw.githubusercontent.com/nuttakulsv/promo-packet/main/skills/promo-packet/evidence.py
python3 evidence.py                               # last 12 months
python3 evidence.py --since 2026-01-01 --org acme --json evidence.json
```

## What's inside

- [`SKILL.md`](skills/promo-packet/SKILL.md): the process: collect, interview, draft, critique.
- [`evidence.py`](skills/promo-packet/evidence.py): GitHub search through `gh`, read-only, nothing leaves your machine except the searches themselves.
- [`rubric.md`](skills/promo-packet/rubric.md): a generic senior / staff / principal rubric with what counts as convincing evidence for each dimension, and what doesn't.
- [`packet-template.md`](skills/promo-packet/packet-template.md): the structure committees tend to like.

## Also good for

- **Self-reviews and performance reviews**: same flow, shorter.
- **A brag document**: run it monthly and keep the stories while you still remember them.
- **Managers**: run it for a report with `--user`, then let the agent interview you about what you saw.

## Things to know

- GitHub shows activity, not impact. The interview is where the packet actually gets written.
- Themes are guessed from titles, labels and file paths (English and Thai keywords). Check them.
- Line counts include generated files and lockfiles. They're context, never an achievement.
- If your work is in private repos, your `gh` login needs access to them. The output goes to your terminal, so be careful where you paste it.

## Further reading

- Will Larson, [Staff archetypes](https://staffeng.com/guides/staff-archetypes/)
- [Dropbox engineering career framework](https://dropbox.github.io/dbx-career-framework/)
- Julia Evans, [Get your work recognized: write a brag document](https://jvns.ca/blog/brag-documents/)

## Tests

```
python3 skills/promo-packet/evidence.py --test
```

## License

MIT
