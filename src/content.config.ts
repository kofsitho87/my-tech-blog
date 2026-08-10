import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

// Controlled vocabulary for coverage analysis. Free-form tags drift in casing
// and wording, which makes "what have we already covered?" unanswerable, so this
// list is intentionally small and closed. Add a term only when an article
// genuinely does not fit any existing one.
export const TOPICS = [
	'agent-architecture',
	'telephony-sip',
	'turn-detection',
	'latency',
	'tool-calling',
	'booking',
	'rag-grounding',
	'warm-transfer',
	'call-analysis',
	'reliability',
	'concurrency-scaling',
	'testing-eval',
	'outbound-lifecycle',
	'observability',
	'product-overview',
] as const;

const blog = defineCollection({
	// Load Markdown and MDX files in the `src/content/blog/` directory.
	loader: glob({ base: './src/content/blog', pattern: '**/*.{md,mdx}' }),
	// Type-check frontmatter using a schema
	schema: ({ image }) =>
		z.object({
			title: z.string(),
			description: z.string(),
			// Transform string to Date object
			pubDate: z.coerce.date(),
			updatedDate: z.coerce.date().optional(),
			heroImage: z.optional(image()),

			// Stable identity shared by every language version of an article.
			articleId: z.string(),
			lang: z.enum(['ko', 'en']),

			// Publication state. Drafts are excluded from the post list, the RSS
			// feed, and static path generation, so this flag cannot drift from
			// what is actually on the site.
			draft: z.boolean().default(false),

			// Which codebase grounds the article. Non-engineering posts use null.
			sourceRepo: z.enum(['inbound', 'outbound']).nullable().default(null),
			topics: z.array(z.enum(TOPICS)).default([]),

			// Cross-posted elsewhere; not derivable from the slug.
			mediumUrl: z.string().url().optional(),
		}),
});

export const collections = { blog };
