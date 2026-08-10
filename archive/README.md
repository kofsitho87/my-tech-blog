# Archive

Drafts that were never published, kept for provenance. Nothing here is part of
the Astro build — `src/content/blog/` is the only source of published articles.

These files predate the single-source migration, when article originals lived in
the product repositories (`inbound-agent/docs/articles/`,
`outbound-agent/docs/blog/`). They are stored as-is; frontmatter has not been
migrated to the current schema.

## `outbound-drafts/`

Early drafts from `outbound-agent/docs/blog/`, written against the original
`InfoAgent` + `BookingAgent` structure. No frontmatter. Both topics were later
rewritten from scratch and published as inbound articles, so these were never
used:

| File | Superseded by |
|---|---|
| `livekit-hospital-voice-agent.md` / `-en.md` | `livekit-agents-hospital-inbound-voice-ai` |
| `call-analysis-pipeline-ko.md` / `-en.md` | `voice-ai-post-call-analysis-pipeline` |

Prose overlap with the published articles is negligible (10–40 shared lines out
of 544–781).

## `en-drafts/`

English drafts from `inbound-agent/docs/articles/en/` with no published
counterpart.

- `livekit-agents-hospital-inbound-voice-ai-en.md` — the blog-targeted English
  version. What actually shipped as
  `how-we-built-ai-that-answers-hospital-phone-calls` was the Medium adaptation
  (230/230 lines identical), so this draft was orphaned.
- `beyond-ivr-config-driven-voice-agent.md` — English version of the beyond-IVR
  article. Never published in any channel.
- `livekit-agents-hospital-inbound-voice-ai-medium.md` — the Medium adaptation.
  Kept because it, not the `-en` draft, is what the published English post was
  built from.

## `ko-drafts/`

- `beyond-ivr-config-driven-voice-agent.md` — the original Korean beyond-IVR
  article. The published `config-driven-voice-ai-beyond-ivr` shares its title but
  almost nothing else (0.104 prose similarity): it is a full rewrite with a
  different register and structure. Kept because this is a distinct piece of
  writing, not a stale copy.

## Legacy management files

`blog-registry.legacy.yaml` and `BLOG_MANAGEMENT.legacy.md` were the hand-maintained
publication registry and its generated index. Their state is now carried by
frontmatter (`articleId`, `lang`, `draft`) plus the slug. The registry is kept
only for its `created_at` timestamps, which have no counterpart in the new schema.

Note that the registry had already drifted from reality before the migration: it
recorded `voice-ai-outbound-callee-lifecycle` and `voice-ai-amd-agent-handoff-race`
as unpublished while both were live on the site. That drift is the reason the new
schema uses a `draft` flag the build actually honors.
