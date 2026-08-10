# Blog Publishing Management

이 문서는 `docs/articles/`에 있는 블로그 게시글과 언어별 배포 상태를 관리합니다.
`blog-registry.yaml`과 각 글의 frontmatter에서 자동 생성되므로 직접 수정하지 않습니다.

마지막 업데이트: 2026-08-08

배포 현황 기준: 2026-08-07 사용자 제공 배포 목록 및 GitHub Pages 배포 검증

## 현황 요약

| 항목 | 수량 |
|---|---:|
| 한국어 문서 | 17 |
| 영어 문서 | 3 |
| 저장소에 원고가 없는 배포 글 | 0 |
| 한국어 버전 배포 완료 | 15 |
| 영어 버전 배포 완료 | 2 |

## 배포 상태 표시

| 표시 | 의미 |
|---|---|
| ✅ | 배포 완료 |
| ⬜ | 미배포 |
| ❓ | 배포 여부 확인 필요 |
| — | 해당 언어 버전 없음 |

## 게시글 및 배포 현황

| ID | 게시글 | 한국어 원고 | 영어 원고 | 한국어 배포 상태 | 영어 배포 상태 | 한국어 게시 URL | 영어 게시 URL | 최초 작성 시간 (KST) |
|---|---|---|---|:---:|:---:|---|---|---|
| `config-driven-voice-agent` | IVR을 넘어: 설정 기반 Voice AI Agent 설계하기 | [KO](ko/beyond-ivr-config-driven-voice-agent.md) | [EN](en/beyond-ivr-config-driven-voice-agent.md) | ✅ | ✅ | [KO](https://kofsitho87.github.io/my-tech-blog/blog/config-driven-voice-ai-beyond-ivr/) | — | 2026-04-21 11:30:57 |
| `livekit-hospital-voice-ai` | 전화받는 AI는 어떻게 만들어질까? | [KO](ko/livekit-agents-hospital-inbound-voice-ai.md) | [기본 EN](en/livekit-agents-hospital-inbound-voice-ai-en.md) · [Medium EN](en/livekit-agents-hospital-inbound-voice-ai-medium.md) | ✅ | ✅ | [KO](https://kofsitho87.github.io/my-tech-blog/blog/livekit-agents-hospital-inbound-voice-ai/) | [EN](https://kofsitho87.github.io/my-tech-blog/blog/how-we-built-ai-that-answers-hospital-phone-calls/) | 2026-05-05 18:52:10 |
| `livekit-warm-transfer` | AI에서 사람으로 안전하게 연결하기 | [KO](ko/self-hosted-livekit-single-room-warm-transfer.md) | — | ✅ | — | [KO](https://kofsitho87.github.io/my-tech-blog/blog/self-hosted-livekit-single-room-warm-transfer/) | — | 2026-05-13 21:29:23 |
| `wise-ai-never-miss-call` | 병원이 바쁜 순간에도 환자의 전화는 멈추지 않습니다 | [KO](ko/wise-ai-inbound-agent-never-miss-a-patient-call.md) | — | ✅ | — | [KO](https://kofsitho87.github.io/my-tech-blog/blog/wise-ai-inbound-agent-never-miss-a-patient-call/) | — | 2026-05-21 07:57:50 |
| `voice-ai-turn-detection` | AI는 환자가 말을 끝낸 순간을 어떻게 알까? | [KO](ko/voice-ai-turn-detection-and-interruption.md) | — | ✅ | — | [KO](https://kofsitho87.github.io/my-tech-blog/blog/voice-ai-turn-detection-and-interruption/) | — | 2026-05-29 08:21:56 |
| `voice-ai-latency` | AI 전화 상담원이 대답하기까지 | [KO](ko/voice-ai-stt-llm-tts-latency.md) | — | ✅ | — | [KO](https://kofsitho87.github.io/my-tech-blog/blog/voice-ai-stt-llm-tts-latency/) | — | 2026-06-06 08:51:33 |
| `voice-ai-post-call-analysis` | 통화 종료가 데이터의 시작이다 | [KO](ko/voice-ai-post-call-analysis-pipeline.md) | — | ✅ | — | [KO](https://kofsitho87.github.io/my-tech-blog/blog/voice-ai-post-call-analysis-pipeline/) | — | 2026-06-14 10:01:17 |
| `voice-ai-grounding-rag` | AI가 병원 정보를 지어내지 않게 하려면 | [KO](ko/voice-ai-grounding-rag-hospital-knowledge.md) | — | ✅ | — | [KO](https://kofsitho87.github.io/my-tech-blog/blog/voice-ai-grounding-rag-hospital-knowledge/) | — | 2026-06-22 10:40:58 |
| `voice-ai-testing` | 출시 전에 AI 상담원을 어떻게 테스트할까 | [KO](ko/how-to-test-voice-ai-before-launch.md) | — | ✅ | — | [KO](https://kofsitho87.github.io/my-tech-blog/blog/how-to-test-voice-ai-before-launch/) | — | 2026-06-30 11:29:52 |
| `voice-ai-resilience` | Voice AI는 장애가 나도 통화를 이어가야 한다 | [KO](ko/voice-ai-resilience-and-failure-recovery.md) | — | ✅ | — | [KO](https://kofsitho87.github.io/my-tech-blog/blog/voice-ai-resilience-and-failure-recovery/) | — | 2026-07-08 14:26:22 |
| `voice-ai-safe-appointment-intake` | AI가 실제 예약 요청을 접수하기까지 | [KO](ko/voice-ai-safe-appointment-intake.md) | — | ✅ | — | [KO](https://kofsitho87.github.io/my-tech-blog/blog/voice-ai-safe-appointment-intake/) | — | 2026-07-15 15:08:26 |
| `voice-ai-safe-tool-calling` | AI는 언제 도구를 사용하고, 언제 말로 답해야 할까? | [KO](ko/voice-ai-safe-tool-calling.md) | — | ✅ | — | [KO](https://kofsitho87.github.io/my-tech-blog/blog/voice-ai-safe-tool-calling/) | — | 2026-07-21 15:25:10 |
| `voice-ai-concurrent-call-scaling` | 전화가 동시에 몰리면 AI 상담원은 어떻게 버틸까? | [KO](ko/voice-ai-concurrent-call-scaling.md) | — | ✅ | — | [KO](https://kofsitho87.github.io/my-tech-blog/blog/voice-ai-concurrent-call-scaling/) | — | 2026-07-27 15:41:33 |
| `voice-ai-supervisor-agent-tasks` | AI 상담원은 왜 하나인데, 업무는 여러 Task로 나눌까? | [KO](ko/voice-ai-supervisor-agent-tasks.md) | — | ✅ | — | [KO](https://kofsitho87.github.io/my-tech-blog/blog/voice-ai-supervisor-agent-tasks/) | — | 2026-07-31 15:59:41 |
| `voice-ai-async-tools-reservation-lookup` | 예약 조회가 느릴 때 AI는 무엇을 말해야 할까? | [KO](ko/voice-ai-async-tools-reservation-lookup.md) | — | ✅ | — | [KO](https://kofsitho87.github.io/my-tech-blog/blog/voice-ai-async-tools-reservation-lookup/) | — | 2026-08-04 16:33:18 |
| `voice-ai-outbound-callee-lifecycle` | 전화가 연결되기 전에 Agent는 무엇을 기다려야 할까? | [KO](ko/voice-ai-outbound-callee-lifecycle.md) | — | ⬜ | — | — | — | 2026-08-07 23:18:17 |
| `voice-ai-amd-agent-handoff-race` | AI가 설정된 인사말 대신 마음대로 말한 이유 | [KO](ko/voice-ai-amd-agent-handoff-race.md) | — | ⬜ | — | — | — | 2026-08-08 00:32:02 |

## 관리 규칙

1. 새 글은 `ko/` 또는 `en/`에 저장하고 `article_id`를 포함한 필수 frontmatter를 추가합니다.
2. 새 게시글과 배포 상태는 `blog-registry.yaml`에 기록합니다.
3. 배포 상태는 파일 존재 여부로 추측하지 않고 사용자 확인 또는 검증 가능한 배포 근거로만 변경합니다.
4. 최초 작성 시간은 KST로 기록하고 이후 수정 시 변경하지 않습니다.
5. 공개 URL을 알게 되면 해당 언어의 registry `url`에 기록합니다.
6. 문서나 registry 변경 후 동기화 스크립트를 실행하고 `--check`로 검증합니다.
