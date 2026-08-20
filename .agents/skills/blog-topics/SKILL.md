---
name: blog-topics
description: Find what the blog has already covered and recommend what to write next by comparing published articles in my-tech-blog with engineering material in product repositories. Use when asked what to blog about, which topics remain uncovered, whether a topic has already been written about, or for blog coverage and gap analysis.
---

# Blog Topics

Answer two questions: **what has already been written**, and **what in the
repository is worth writing about that has not been**.

Treat my-tech-blog as the source of existing coverage and the product repository
being scanned as the source of candidate engineering stories.

## Require repository evidence

Recommend only topics backed by material that actually exists in a product
repository: an incident document, design note, merged change, or real constraint
in the code. Every recommendation must name the file or commit it came from. Drop
any recommendation that cannot be grounded this way.

## Workflow

### 1. Run the coverage report

```bash
python3 .agents/skills/blog-topics/scripts/coverage.py
```

The report prints published articles by topic, uncovered vocabulary terms,
articles grounded in each repository, documents under `docs/`, and recent
commits. Draw conclusions from the report; the script deliberately does not.

Choose the scan scope based on the working directory:

| Run from | Scans |
|---|---|
| A known product repository | That repository only |
| The blog repository or elsewhere | Both configured product repositories |
| Any directory with a path argument | The repository at that path |

When reporting results, state which repositories were scanned.

### 2. Read candidate material

Do not recommend from filenames alone. Open promising documents and inspect
relevant commits or code to confirm there is a real story: a failure with a
cause, a design decision with a tradeoff, or a constraint that forced an
unobvious solution.

Prioritize:

- postmortems and incident notes, especially dated filenames or names containing
  `race`, `investigation`, or `postmortem`;
- design documents where an approach was rejected;
- `AGENTS.md` or `CLAUDE.md` lessons-learned sections that point to incidents;
- commits that fix subtle problems rather than merely adding features.

### 3. Compare candidates with coverage

Assign one verdict to each candidate:

| Verdict | Meaning |
|---|---|
| **uncovered** | No article touches it. Prefer these recommendations. |
| **adjacent** | A related article exists but stops short of this. State the missing angle. |
| **covered** | An article already covers it. Name that article and do not recommend a duplicate. |
| **thin** | An article exists but predates significant changes. Recommend a revision, not a new article. |

Treat an empty term in the topic vocabulary only as a hint. Never manufacture an
article solely to fill a vocabulary gap.

### 4. Report ranked recommendations

Rank candidates by reader value. For each recommendation, provide:

- a working title framed as a concrete question or tension;
- **evidence** with repository-relative file paths and relevant commit hashes;
- the coverage verdict and, for **adjacent**, the exact gap it fills;
- the proposed `topics` value from the controlled vocabulary;
- one sentence describing what the reader will learn.

End with topics deliberately excluded and why, especially promising-looking
ideas that lacked sufficient evidence. This prevents the same dead ends from
being explored repeatedly.

Recommend only. Do not draft the article unless the user separately asks for it.
