// Place any global data in this file.
// You can import this data from anywhere in your site by using the `import` keyword.

export const SITE_TITLE = 'kofsitho87.log';
export const SITE_DESCRIPTION = '배운 것을 기록하고, 만든 것을 나누는 개발 노트';
export const GITHUB_URL = 'https://github.com/kofsitho87';

export function pathWithBase(path = '') {
	const base = import.meta.env.BASE_URL.replace(/\/$/, '');
	return `${base}/${path.replace(/^\//, '')}`;
}
