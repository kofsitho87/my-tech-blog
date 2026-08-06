---
title: '기술 블로그를 시작합니다'
description: 'Astro와 GitHub Pages로 만든 첫 번째 개발 기록'
pubDate: '2026-08-06'
---

안녕하세요. **kofsitho87.log**의 첫 번째 글입니다.

배운 내용을 오래 기억하는 가장 좋은 방법은 내 언어로 다시 설명하는 것이라고 생각합니다. 이 블로그에는 프로젝트를 만들며 만난 문제와 해결 과정, 새롭게 알게 된 기술을 차곡차곡 기록하려고 합니다.

## 이 블로그의 기술 구성

이 블로그는 정적 사이트 생성기인 [Astro](https://astro.build/)로 만들었습니다. 글은 Markdown으로 작성하고, `main` 브랜치에 코드를 올리면 GitHub Actions가 자동으로 빌드해 GitHub Pages에 배포합니다.

```bash
npm run dev     # 로컬 개발 서버
npm run build   # 배포용 정적 파일 생성
```

## 다음 기록

완성된 결과만 보여주기보다 무엇을 시도했고 왜 그렇게 결정했는지를 남기겠습니다. 작은 메모가 쌓여 누군가에게 쓸모 있는 지도가 되기를 바랍니다.

새 글은 `src/content/blog/` 폴더에 Markdown 파일을 추가하면 됩니다.
