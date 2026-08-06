# kofsitho87.log

Astro와 GitHub Pages로 만든 개인 기술 블로그입니다.

## 로컬 실행

```bash
npm install
npm run dev
```

## 새 글 작성

`src/content/blog/`에 Markdown 또는 MDX 파일을 추가합니다.

```md
---
title: '글 제목'
description: '글 설명'
pubDate: '2026-08-06'
---

본문을 작성하세요.
```

## 배포

`main` 브랜치에 push하면 GitHub Actions가 자동으로 빌드하고 GitHub Pages에 배포합니다.

- 예정 주소: https://kofsitho87.github.io/my-tech-blog/
- GitHub 설정: `Settings → Pages → Source → GitHub Actions`
