---
article_id: "config-driven-voice-agent"
title: "IVR을 넘어: 설정 기반 Voice AI Agent 설계하기"
description: "규칙 기반 IVR의 결정성과 LLM 대화의 유연성을 함께 가져가기 위해, SingleAgent가 선언형 flow_config를 해석하도록 설계한 병원 Voice AI 아키텍처를 설명합니다."
author: "Dan"
date: "2026-04-20"
language: "ko"
korean_version: "docs/articles/ko/beyond-ivr-config-driven-voice-agent.md"
english_version: "docs/articles/en/beyond-ivr-config-driven-voice-agent.md"
tags:
  - Voice AI
  - LLM Agent
  - Telephony
  - LiveKit Agents
  - Config-driven
  - Call Flow
  - DTMF
  - IVR
og_title: "IVR을 넘어: 설정 기반 Voice AI Agent 설계하기"
og_description: "결정적인 통화 제어와 자연스러운 LLM 대화를 선언형 flow_config로 결합한 병원 Voice AI 아키텍처"
og_image: "docs/articles/images/beyond-ivr-voice-agent-og.png"
hero_image: "docs/articles/images/beyond-ivr-voice-agent-hero.png"
twitter_card: "summary_large_image"
canonical: "/blog/config-driven-voice-ai-beyond-ivr/"
---

# IVR을 넘어: 설정 기반 Voice AI Agent 설계하기

![DTMF와 조건 분기로 제어되는 통화 흐름이 하나의 Voice AI 상담으로 합쳐지는 구조](../images/beyond-ivr-voice-agent-hero.png)

환자가 병원에 전화를 걸었습니다.

진료 예약을 하려는지, 기존 예약을 조회하려는지, 주차 정보를 묻는지, 상담원과 통화하려는지 아직 모릅니다. 전통적인 IVR이라면 “예약은 1번, 병원 안내는 2번”처럼 모든 경로를 미리 정합니다. LLM 상담원이라면 환자가 원하는 것을 자연어로 듣고 판단할 수 있습니다.

하지만 둘 중 하나만 선택하면 문제가 생깁니다.

IVR은 예측할 수 있지만 경직되어 있습니다. 메뉴에 없는 요청을 처리하기 어렵고, 병원별 운영시간이나 휴일 정책이 바뀔 때마다 로직을 수정해야 합니다. 반대로 LLM은 유연하지만 확률적으로 동작합니다. “1번을 누르면 반드시 예약으로 간다”, “운영시간이 아니면 상담원에게 연결하지 않는다”와 같은 규칙까지 모델의 판단에 맡기면 운영자가 기대하는 보장을 만들기 어렵습니다.

그래서 와이즈에이아이 인바운드 에이전트는 **통화의 큰 흐름은 선언형 설정으로 제어하고, 자연어 이해와 업무 수행은 LLM과 Tool·Task에 맡기는 구조**를 사용합니다.

핵심은 `flow_config`와 이를 실행하는 `SingleAgent`입니다.

> **Version note:** 이 글은 2026년 8월 7일의 저장소와 `livekit-agents>=1.6.8` 구성을 기준으로 영어 원고를 현재 구현에 맞게 재구성했습니다. 초기 설계의 `SupervisorAgent`와 여러 전문 Agent는 현재 하나의 `SingleAgent` 및 전문 Task 중심 구조로 발전했습니다.

## 목차

- [1. 결정해야 하는 것과 생성해도 되는 것을 분리한다](#1-결정해야-하는-것과-생성해도-되는-것을-분리한다)
- [2. dial_info에서 실행 가능한 통화 그래프까지](#2-dial_info에서-실행-가능한-통화-그래프까지)
- [3. 다섯 가지 노드가 통화의 문법이 된다](#3-다섯-가지-노드가-통화의-문법이-된다)
- [4. DTMF 선택은 어떻게 실제 업무로 이어지는가](#4-dtmf-선택은-어떻게-실제-업무로-이어지는가)
- [5. 하나의 Agent를 유지하는 이유](#5-하나의-agent를-유지하는-이유)
- [6. flow_config와 workflow_config는 무엇이 다른가](#6-flow_config와-workflow_config는-무엇이-다른가)
- [7. 실패 경로까지 설정과 코드의 계약에 포함한다](#7-실패-경로까지-설정과-코드의-계약에-포함한다)
- [8. 설정 기반 설계가 잘 맞는 경우](#8-설정-기반-설계가-잘-맞는-경우)
- [마치며](#마치며)

---

## 1. 결정해야 하는 것과 생성해도 되는 것을 분리한다

Voice AI에서 모든 문장을 고정할 필요는 없습니다. 환자의 표현은 다양하고, 예약 과정에서 이어지는 질문도 상황마다 달라집니다. 이런 부분은 LLM이 잘합니다.

반면 다음 항목은 자연스러운 문장보다 일관된 결과가 중요합니다.

- 운영시간 여부에 따른 분기
- DTMF 번호와 업무의 매핑
- 상담원 연결 번호와 연결 방식
- 통화 종료 조건과 종료 사유
- 예약 생성·조회·변경·취소 중 실행할 Tool

이 경계를 코드로 표현하면 다음과 같습니다.

| 책임 | 제어 주체 | 예시 |
|---|---|---|
| 통화의 순서와 분기 | `flow_config` | 운영시간 확인 → 인사말 → DTMF → 업무 진입 |
| 노드 실행과 안전한 전환 | `SingleAgent` | TTS 재생, DTMF 결과 해석, Tool 강제 호출, 종료 |
| 자연어 대화 | LLM | 환자 요청 이해, 추가 질문, FAQ 답변 |
| 한정된 전문 업무 | Tool·`AgentTask` | 예약 조회, 예약 생성, DTMF 정보 수집, 상담원 연결 |

LiveKit도 폐쇄형 업무 흐름에서는 다단계 절차 전체를 긴 프롬프트에 맡기기보다 결정적인 workflow를 코드와 구조로 표현해야 한다고 설명합니다. 2026년 7월의 LiveKit 가이드 역시 중요한 규칙은 모델 밖의 결정적 코드로 통제하고, Tool과 Task의 범위를 좁히는 방식을 권장합니다.

이 설계에서 LLM은 사라지지 않습니다. 다만 **LLM이 판단해야 할 문제의 범위를 줄입니다.**

## 2. `dial_info`에서 실행 가능한 통화 그래프까지

각 통화는 `dial_info`라는 JSON payload로 시작합니다. 여기에는 병원 정보, 환자 정보, 언어와 상담원 연결 설정, 업무별 세부 정책, 그리고 `flow_config`가 들어 있습니다.

~~~mermaid
flowchart LR
    D["dial_info JSON"] --> C["CallSessionData.from_dial_info()"]
    C --> F["FlowConfig<br/>entry_node_id + nodes"]
    C --> B["business_data"]
    C --> R["recipient_data"]
    C --> W["workflow_config"]
    F --> S["SingleAgent._process_node()"]
    S --> N["condition / greeting / agent / action / exit"]
    N --> T["LLM · Tool · AgentTask · Transfer"]
~~~

`CallSessionData.from_dial_info()`는 JSON의 각 노드를 `FlowNode`로 변환합니다. `SingleAgent`는 `entry_node_id`에 해당하는 노드부터 읽고, 노드 처리 결과로 받은 다음 ID를 다시 처리합니다.

흐름을 단순화하면 다음과 같습니다.

```python
async def _process_node(node_id: str) -> None:
    node = flow_config.get_node(node_id)

    if node.type == "condition":
        next_node_id = await handle_condition(node)
    elif node.type == "greeting":
        next_node_id = await handle_greeting(node)
    elif node.type == "agent":
        await handle_agent(node)
        return
    elif node.type == "action":
        next_node_id = await handle_action(node)
    elif node.type == "exit":
        await handle_exit(node)
        return

    if next_node_id:
        await _process_node(next_node_id)
```

이 코드는 복잡한 의사결정을 하지 않습니다. 설정에 적힌 그래프를 해석합니다. 각 handler가 TTS, DTMF 입력, Tool 호출, SIP 연결처럼 비동기 작업을 수행한 뒤 다음 노드만 반환하므로 흐름을 추적하기도 쉽습니다.

## 3. 다섯 가지 노드가 통화의 문법이 된다

현재 `FlowNode`가 지원하는 타입은 다섯 가지입니다.

| 노드 | 역할 | 주요 설정 |
|---|---|---|
| `condition` | 세션 데이터에 따른 조건 분기 | `field`, `branches`, `next` |
| `greeting` | 고정 안내 재생과 선택적 DTMF 수집 | `message`, `input_method`, `dtmf_options` |
| `agent` | 같은 `SingleAgent`에서 자연어 응답 또는 Tool 실행 시작 | `id` |
| `action` | 상담원 연결이나 로그 같은 side effect 수행 | `action_type`, `action_config` |
| `exit` | 종료 안내와 구조화된 종료 사유 기록 | `message`, `termination`, `events` |

### `condition`: 모델 없이 분기한다

```json
{
  "id": "check_work_hours",
  "type": "condition",
  "name": "운영시간 확인",
  "field": "business_data.is_work_time",
  "branches": {
    "true": "greeting_open",
    "false": "greeting_closed"
  }
}
```

`SingleAgent`는 `business_data`, `recipient_data`, `call_config_data` prefix에 해당하는 값을 읽고 소문자 문자열로 바꿔 `branches`에서 다음 노드를 찾습니다. 일치하는 값이 없으면 `branches["any"]`, 그다음 `node.next` 순으로 fallback합니다.

운영시간처럼 이미 시스템이 알고 있는 사실을 다시 LLM에게 질문하지 않는 것이 핵심입니다.

### `greeting`: 안내와 입력을 묶는다

```json
{
  "id": "greeting_main",
  "type": "greeting",
  "name": "메인 안내",
  "input_method": "dtmf",
  "message": "예약은 1번, 병원 정보는 2번, 직접 문의는 5번을 눌러 주세요.",
  "dtmf_options": {
    "1": {
      "next": "booking_agent",
      "user_request": "진료 예약 신청",
      "tool": "booking_create",
      "on_select_message": "진료 예약을 도와드리겠습니다."
    },
    "2": {
      "next": "info_agent",
      "user_request": "주차 정보 문의",
      "tool": "info_look_up"
    },
    "5": {
      "next": "direct_input",
      "on_select_message": "문의하실 내용을 말씀해 주세요."
    },
    "*": {
      "next": "greeting_main"
    }
  },
  "next": "greeting_main"
}
```

`GreetingDtmfTask`는 안내 재생과 DTMF 수신을 함께 관리합니다. 이미 메뉴를 아는 환자가 안내 도중 번호를 누르는 상황, 잘못된 번호, 다시 듣기, 무응답을 하나의 Task 경계에서 처리합니다. 기본 timeout은 5초이고 최대 무효 입력 횟수는 2회입니다.

`on_select_message`는 번호 선택 직후 다음 동작 전에 재생됩니다. `direct_input`은 합성된 사용자 요청을 만들지 않고 실제 환자의 다음 발화를 기다립니다. 환자가 메뉴에 없는 질문을 직접 말할 수 있는 탈출구입니다.

### `action`과 `exit`: 외부 효과를 명시한다

`action`은 `transfer`, `transfer_direct`, `log`를 처리합니다. `transfer_direct`는 노드에 적힌 번호와 `warm_transfer` 또는 `cold_transfer` 방식을 사용합니다. 번호가 없으면 무조건 실패시키지 않고 설정된 `next`로 이동할 수 있습니다.

`exit`는 종료 멘트를 끝까지 재생한 뒤 `CALL_TERMINATION` 이벤트에 actor와 reason을 남깁니다. 단순히 연결을 끊는 것과 “운영시간 외 안내가 끝나 시스템이 종료한 통화”를 데이터에서 구분할 수 있습니다.

## 4. DTMF 선택은 어떻게 실제 업무로 이어지는가

영어 원고의 초기 구조에서는 `booking_agent`, `info_agent`, `triage_coordinator`가 서로 다른 Agent였습니다. 현재 구현에서 이 이름들은 별도 Agent 클래스가 아니라 **설정의 라우팅 역할**입니다.

세션을 오래 유지하는 주체는 `SingleAgent` 하나입니다.

~~~mermaid
sequenceDiagram
    participant P as 환자
    participant D as GreetingDtmfTask
    participant S as SingleAgent
    participant L as LLM
    participant T as Tool / AgentTask

    S->>D: greeting + dtmf_options
    D->>P: 안내 TTS 재생
    P->>D: 1번 입력
    D-->>S: selected_key=1
    S->>S: user_request와 tool action_key 해석
    S->>L: 선택된 function을 강제한 generate_reply
    L->>T: create_new_appointment 호출
    T-->>S: 예약 업무 결과
    S-->>P: 같은 통화 Context에서 대화 계속
~~~

`dtmf_options.tool`은 곧바로 Python 함수 이름을 노출하지 않습니다. `booking_create` 같은 업무용 action key를 코드의 allowlist가 `create_new_appointment` 같은 실제 function tool로 매핑합니다.

```python
DTMF_TOOL_ACTION_KEY_TO_FUNCTION = {
    "booking_create": "create_new_appointment",
    "booking_inquiry": "get_my_appointment_list",
    "booking_cancel": "cancel_appointment",
    "booking_modify": "modify_appointment",
    "info_look_up": None,
}
```

예약처럼 반드시 특정 기능을 실행해야 하는 선택은 `tool_choice`로 해당 Tool 호출을 강제합니다. 반면 병원 정보는 전용 검색 Tool을 한 번 더 호출하지 않고, 세션 시작 시 주입된 FAQ를 근거로 `SingleAgent`가 답합니다. 설정에 등록되지 않은 action key는 경고 대상입니다.

여기서 중요한 점은 DTMF가 LLM에게 “아마 예약일 것”이라는 힌트를 주는 것이 아니라는 사실입니다. **키 입력이 업무를 결정하고, LLM은 결정된 업무 안에서 자연스러운 대화를 담당합니다.**

## 5. 하나의 Agent를 유지하는 이유

Agent를 업무마다 교체하면 각 Agent의 프롬프트와 Tool을 작게 유지할 수 있습니다. 하지만 통화 맥락 전달, Agent 수명주기, 오디오 입력 상태, 관찰 이벤트를 전환할 때마다 정리해야 합니다.

현재 구조는 다른 선택을 했습니다.

- `SingleAgent`가 통화 전체 Context를 유지합니다.
- 예약·환자 확인·상담원 연결 같은 한정된 업무는 Tool 또는 `AgentTask`에 위임합니다.
- Task가 끝나면 결과를 돌려받아 같은 Agent가 대화를 이어갑니다.
- `booking_agent`, `info_agent` 같은 flow node ID는 역할을 표시하지만 실제 세션 Agent를 교체하지 않습니다.

LiveKit의 2026년 3월 Supervisor Pattern 설명도 장기 실행 Agent가 세션을 유지하고, 짧은 Task가 한정된 목표를 수행한 뒤 typed result를 반환하는 구조를 구분합니다. 이 패턴은 turn detection과 interruption 처리를 포함한 같은 음성 세션을 유지하는 데 유리합니다.

모든 일을 하나의 거대한 프롬프트에 넣는다는 뜻은 아닙니다. 장기 Context는 `SingleAgent`가 갖되, 복잡한 예약 흐름은 `AgentTask`로 범위를 제한합니다. **하나의 Agent와 하나의 책임은 같은 말이 아닙니다.**

## 6. `flow_config`와 `workflow_config`는 무엇이 다른가

설정이 많아지면 모든 옵션을 `flow_config`에 넣고 싶어집니다. 하지만 통화 라우팅과 업무 내부 정책은 변경 이유가 다릅니다.

| 설정 | 질문 | 예시 |
|---|---|---|
| `flow_config` | 다음에는 어디로 가는가? | 운영시간 분기, DTMF 메뉴, 상담원 연결, 종료 |
| `workflow_config` | 선택된 업무 안에서 어떻게 처리하는가? | 당일 예약 허용, 의료진 선택 여부, 예약 조회 기간, 메시지 수집 방식 |

예를 들어 “1번을 누르면 예약 신청으로 이동한다”는 `flow_config`의 책임입니다. 예약 신청 중 의료진을 먼저 고르게 할지, 가능한 일정을 며칠까지 조회할지는 `workflow_config.booking`의 책임입니다.

이 구분이 없으면 메뉴 하나를 바꾸는 작업과 예약 정책을 바꾸는 작업이 같은 JSON 영역에 섞입니다. 설정을 선언형으로 만든 뒤에도 경계를 나누지 않으면 결국 또 하나의 거대한 프로그램이 됩니다.

## 7. 실패 경로까지 설정과 코드의 계약에 포함한다

설정 기반 시스템은 설정 파일이 존재한다고 안전해지지 않습니다. 오히려 코드와 설정 사이의 계약이 하나 더 생깁니다.

현재 구현은 다음 실패를 별도로 다룹니다.

### 진입 노드나 대상 노드가 없다

`flow_config`가 없으면 설정 오류 안내 후 `NO_FLOW_CONFIG` 사유로 종료합니다. 이동하려는 노드가 없으면 일반 오류 안내를 재생하고 `MISSING_FLOW_NODE`로 종료합니다. 흐름이 조용히 멈추는 것보다 환자와 분석 시스템 모두에게 명시적인 결과를 남깁니다.

### DTMF 입력이 없거나 잘못됐다

재시도 한도를 넘기면 무한히 메뉴를 반복하지 않습니다. 종료 안내를 재생하고 `MAX_INVALID_DTMF`를 기록합니다. 안내 중 환자가 먼저 끊은 경우에는 뒤늦은 timeout 멘트가 transcript에 남지 않도록 별도로 처리합니다.

### 상담원 연결 설정이 불완전하다

직접 연결 번호가 없으면 경고를 남기고 `next`가 있다면 대체 경로로 진행합니다. 운영에서는 이 fallback이 상담 메모 수집이나 종료 안내로 연결되어야 합니다.

### 설정 변경이 코드 배포를 대체하려면 검증 절차가 필요하다

JSON을 외부 metadata나 관리 API로 주입하면 병원별 메뉴를 코드 배포 없이 바꿀 수 있습니다. 그러나 이는 변경 위험이 사라진다는 뜻이 아닙니다. 최소한 다음 검증이 필요합니다.

- `entry_node_id`와 모든 `next` 대상의 존재 여부
- 도달할 수 없는 노드와 종료되지 않는 순환 경로
- `condition.field`의 허용 prefix
- DTMF action key allowlist
- 상담원 연결 번호와 transfer mode
- 운영시간·휴일 조건별 대표 통화 테스트

특히 로컬 `ENV=dev` 실행은 외부 job metadata 대신 샘플 `DIAL_INFO`를 사용하므로, 실제 metadata 기반 flow를 검증할 때는 환경 설정을 확인해야 합니다.

## 8. 설정 기반 설계가 잘 맞는 경우

이 패턴은 모든 Voice AI에 필요한 것은 아닙니다.

### 잘 맞는 경우

- 병원이나 고객사마다 메뉴와 운영시간 정책이 다릅니다.
- DTMF, 조건 분기, 자연어 대화, 상담원 연결을 한 통화에서 함께 사용합니다.
- 특정 선택이 반드시 특정 Tool로 이어져야 합니다.
- 운영자가 코드 배포 없이 메뉴와 연결 정책을 관리해야 합니다.
- 통화 후 어떤 분기와 종료 사유가 발생했는지 분석해야 합니다.

### 과한 경우

- 분기가 거의 없고 하나의 짧은 대화만 처리합니다.
- 모든 흐름을 코드로 배포해도 운영상 문제가 없습니다.
- 설정을 검토·버전 관리·검증할 운영 절차가 없습니다.
- 조건식과 반복이 복잡해져 JSON이 프로그래밍 언어처럼 변하기 시작했습니다.

마지막 경우에는 선언형 설정을 계속 확장하기보다 명시적인 state machine이나 코드 기반 workflow가 더 읽기 쉬울 수 있습니다.

## 마치며

IVR과 LLM은 대체 관계가 아닙니다.

IVR이 잘하는 것은 번호와 규칙에 따라 같은 결과를 내는 일입니다. LLM이 잘하는 것은 정해진 메뉴 밖의 표현을 이해하고 자연스럽게 대화를 이어가는 일입니다. 병원 전화에는 두 능력이 모두 필요합니다.

`flow_config`는 결정해야 하는 순서를 데이터로 표현하고, `SingleAgent`는 그 계약을 실행합니다. DTMF는 중요한 라우팅을 확정하고, Tool과 Task는 업무 범위를 좁히며, LLM은 그 경계 안에서 환자와 대화합니다.

이 구조의 핵심은 JSON 자체가 아닙니다.

> **확률적인 모델이 결정하지 않아도 되는 것은 결정적 코드와 설정으로 옮긴다.**

그 원칙을 지키면 Voice AI는 IVR보다 유연하면서도, 순수 LLM Agent보다 운영자가 이해하고 통제하기 쉬운 시스템이 됩니다.

---

## 참고 자료

- [LiveKit, “How to Implement the Supervisor Pattern for Voice AI” (2026-03-23)](https://livekit.com/blog/supervisor-pattern-voice-agents)
- [LiveKit, “Build a Voice Agent That Won't Go Off Script” (2026-07-16)](https://livekit.com/blog/keeping-your-agent-conversation-on-track)
- [LiveKit AgentSession documentation](https://docs.livekit.io/agents/logic/sessions/)

