# Building a Call Voice AI Assistant with LiveKit Agents

> Sharing Our Experience Developing AI Call Agent

---

## Table of Contents

1. [Introduction](#1-introduction)
   - The Reality of Hospital Phone Operations
   - Problems We're Solving with Voice AI
   - What This Article Covers

2. [Tech Stack and Architecture](#2-tech-stack-and-architecture)
   - Why LiveKit Agents?
   - Overall System Architecture
   - Core Components
   - Call Lifecycle
   - Multi-language Support

3. [Multi-Agent Design Philosophy](#3-multi-agent-design-philosophy)
   - Limitations of a Single Agent
   - Role-Based Agent Separation Strategy
   - Agent Role Definitions
   - BaseAgent Common Functionality

4. [Implementing InfoAgent](#4-implementing-infoagent)
   - Hospital Information Search Requirements
   - Leveraging Qdrant Vector DB
   - Information Search Tool Design

5. [Implementing BookingAgent](#5-implementing-bookingagent)
   - Booking Flow Design
   - Booking Tools Overview
   - Multi-turn Conversation Handling: Using AgentTask

6. [Agent Routing (Transitions)](#6-agent-routing-transitions)
   - Role of TriageCoordinator
   - Context Passing Methods
   - Audio Input Control

7. [Real-World Challenges](#7-real-world-challenges)
   - Natural Language Date/Time Parsing
   - Handling User Silence
   - Counselor Connection Fallback
   - Answering Machine (ARS) Detection
   - Prompt System Structure

8. [Call Termination and Post-Processing](#8-call-termination-and-post-processing)
   - Handling Different Termination Scenarios
   - Post-Session Processing

9. [Conclusion](#9-conclusion)
   - Lessons Learned
   - Areas for Improvement
   - Next Article Preview

---

## 1. Introduction

### 1.1 The Reality of Hospital Phone Operations

Have you ever called a hospital?

```
"I've been on hold for 10 minutes just to confirm an appointment..."
"They don't answer during lunch break..."
"I just wanted to ask about office hours but it took forever to reach someone"
```

Hospitals face the same challenge. They receive hundreds of calls daily, but many are repetitive questions.

| Inquiry Type | Percentage | Characteristics |
|--------------|------------|-----------------|
| Appointment Check/Change | 40% | Simple CRUD, Automatable |
| Office Hours/Location | 25% | Standardized Info |
| Doctor/Department Inquiry | 20% | Search-based Response |
| Complex Consultation | 15% | Requires Human Agent |

We noticed that **85% of calls are simple tasks that AI can handle**.

### 1.2 Problems We're Solving with Voice AI

Our goal was to build a **24/7 AI phone assistant for hospitals**.

**Objectives:**
- AI directly handles appointment queries, creation, and changes
- Instant hospital information (hours, location, doctors)
- Complex inquiries routed to human agents
- Natural voice conversation in multiple languages

**Expected Benefits:**
- Patients: Immediate response without waiting
- Hospitals: Staff can focus on complex tasks
- 24/7: Basic inquiries handled even nights/weekends

### 1.3 What This Article Covers

This article shares our experience building a hospital voice AI using the LiveKit Agents framework.

**Topics Covered:**
- Multi-Agent architecture design (InfoAgent + BookingAgent)
- Hospital information search using Qdrant Vector DB
- Multi-turn booking conversations (AgentTask)
- Real-world problems and solutions

**Not Covered:**
- LiveKit server installation/setup (see official docs)
- SIP trunk detailed configuration
- Frontend implementation

Let's get started.

---

## 2. Tech Stack and Architecture

### 2.1 Why LiveKit Agents?

There are several options for building voice AI: Twilio, Vonage, direct WebRTC implementation, etc. Here's why we chose LiveKit Agents:

**LiveKit Agents Advantages:**

| Feature | Description |
|---------|-------------|
| **Real-time Bidirectional Communication** | WebRTC-based minimal latency |
| **Python Native** | Natural integration with AI/ML ecosystem |
| **Multi-Agent Support** | Framework-level support for agent transitions |
| **SIP Integration** | Compatible with existing phone networks |
| **OpenAI Realtime API Support** | Voice-to-voice processing reduces latency |

The built-in **Multi-Agent transition** capability was decisive. Separating and dynamically switching between Booking Agent and Info Agent was seamlessly possible.

### 2.2 Overall System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Outbound Trigger                             │
│                      (RabbitMQ Message)                              │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Agent Server                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    LiveKit Room Creation                     │   │
│  │                 SIP Outbound Call Initiation                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Multi-Agent System                              │
│                                                                      │
│   ┌─────────────────┐                                               │
│   │TriageCoordinator│ ◄─── Entry Point                              │
│   │ (Intent Routing) │      Routes based on user intent             │
│   └────────┬────────┘                                               │
│            │                                                         │
│    ┌───────┴───────┐                                                │
│    ▼               ▼                                                │
│ ┌──────────┐  ┌──────────┐                                          │
│ │ Booking  │  │   Info   │                                          │
│ │  Agent   │  │  Agent   │                                          │
│ │(Booking) │  │  (Info)  │                                          │
│ └────┬─────┘  └────┬─────┘                                          │
│      │             │                                                 │
└──────┼─────────────┼────────────────────────────────────────────────┘
       │             │
       ▼             ▼
┌────────────┐  ┌────────────┐
│ Booking    │  │  Qdrant    │
│   API      │  │ Vector DB  │
│(Appt CRUD) │  │(Hosp Info) │
└────────────┘  └────────────┘
```

### 2.3 Core Components

#### LiveKit Agents Framework

LiveKit Agents are implemented by inheriting the `Agent` class. System prompts go in `instructions`, and functions are registered in `tools`.

#### OpenAI Realtime API

The traditional approach was a `Speech → STT → LLM → TTS → Speech` pipeline. OpenAI Realtime API handles this in a single call, significantly reducing latency.

```
Traditional: Speech → [STT] → Text → [LLM] → Text → [TTS] → Speech
                     (200ms)        (500ms)        (200ms)

Realtime: Speech → [OpenAI Realtime] → Speech
                       (300ms~)
```

#### Qdrant Vector DB

Hospital information (doctors, departments, events) is stored in Qdrant Vector DB for semantic search. Topic-based metadata structure enables filtering by hospital and category.

#### LiveKit SIP

SIP trunks are used for actual phone network integration. LiveKit acts as a SIP gateway, enabling calls to/from regular phones.

### 2.4 Call Lifecycle

The complete lifecycle of an outbound call follows these state transitions:

```
IDLE → DIALING → RINGING → CONNECTED → ACTIVE → TERMINATED
  │       │         │          │         │          │
  │       │         │          │         │          └─→ ANALYZED
  │       │         │          │         │
  │       │         │          │         └─→ TRANSFERRED → TERMINATED
  │       │         │          │
  │       │         │          └─→ RECORDING_STARTED
  │       │         │
  │       │         └─→ NO_ANSWER → TERMINATED
  │       │
  │       └─→ BUSY → TERMINATED
  │
  └─→ ERROR → TERMINATED
```

**Key Stages:**

| Stage | Description | Trigger |
|-------|-------------|---------|
| **IDLE** | Waiting state | Job received |
| **DIALING** | Initiating call | SIP trunk call |
| **RINGING** | Phone ringing | Remote phone connected |
| **CONNECTED** | Connected | Remote party answered |
| **ACTIVE** | Conversation in progress | Greeting sent |
| **TERMINATED** | Ended | Call completed/failed |
| **ANALYZED** | Analysis complete | MQ message processed |

### 2.5 Multi-language Support

Multi-language support in voice AI isn't just text translation. Both Speech Recognition (STT) and Text-to-Speech (TTS) must support the target language.

**Supported Languages:**

| Language | Code | Notes |
|----------|------|-------|
| Korean | ko-KR | Default |
| English | en-US | - |
| Chinese | zh-CN | Simplified |
| Japanese | ja-JP | - |
| Spanish | es-ES | - |
| Vietnamese | vi-VN | - |

**Implementation:**
- Language code set in `CallConfigData` (e.g., "ko-KR")
- Language passed to LLM model parameters
- Prompt includes "use only this language" constraint

---

## 3. Multi-Agent Design Philosophy

### 3.1 Limitations of a Single Agent

Initially, we tried handling all functions with a single Agent.

**Problems:**
- Prompts exceeded 200 lines, causing the model to miss instructions
- With 14 tools, wrong tool calls became frequent
- Modifying booking logic risked affecting information responses, making maintenance difficult

### 3.2 Role-Based Agent Separation Strategy

The solution was **separating Agents by role**.

```
Before (Single Agent):
┌─────────────────────────────────┐
│         HospitalAgent           │
│  Prompt: 200 lines | Tools: 14  │
│  Role: Booking + Info + ...     │
└─────────────────────────────────┘

After (Multi-Agent):
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│TriageCoordinator│  │  BookingAgent   │  │    InfoAgent    │
│ Prompt: 40 lines│  │ Prompt: 50 lines│  │ Prompt: 40 lines│
│ Tools: 3        │  │ Tools: 5        │  │ Tools: 6        │
│ Role: Routing   │  │ Role: Booking   │  │ Role: Info      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

**Improvements After Separation:**

| Metric | Before | After |
|--------|--------|-------|
| Prompt Length | 200 lines | 40-50 lines each |
| Tools per Agent | 14 | 3-6 |
| Wrong Tool Call Rate | High | Significantly reduced |
| Maintainability | Low | High (independent modifications) |

### 3.3 Agent Role Definitions

#### TriageCoordinator (Intent Classification)

Listens to the user's first utterance and routes to the appropriate Agent.
- Booking-related → Transfer to BookingAgent
- Information inquiry → Transfer to InfoAgent
- Agent request → Handle human agent connection

#### BookingAgent (Booking Processing)

Handles appointment queries, creation, and modifications.
- Department selection
- Date/time selection
- Appointment creation

#### InfoAgent (Information Provision)

Handles hospital information search and guidance.
- Hospital introduction, hours
- Directions, parking
- Doctors, services, events

### 3.4 BaseAgent Common Functionality

Common functions needed by all three Agents were extracted into `BaseAgent`.

**Common Functions:**
- `on_enter()`: Context handling on Agent entry
- `_transfer_to_agent()`: Inter-Agent transition
- `transfer_call()`: Human agent connection
- `end_call_by_user_request()`: Call termination
- `hangup()`: Room deletion

By consolidating common functions in BaseAgent, each Agent can focus solely on its role.

---

## 4. Implementing InfoAgent

### 4.1 Hospital Information Search Requirements

Here are the information types InfoAgent must handle:

| Category | Example Question | Data Characteristics |
|----------|------------------|---------------------|
| **Hospital Intro** | "What kind of hospital is this?" | Static, Text |
| **Office Hours** | "Are you open on Saturdays?" | Static, Structured |
| **Directions** | "Is parking available?" | Static, Text |
| **Medical Staff** | "What's Dr. Kim's specialty?" | Search needed, Multiple |
| **Medical Services** | "How much are implants?" | Search needed, Multiple |
| **Events** | "Any current discounts?" | Dynamic, Date filtering needed |

**Key Requirements:**
1. **Semantic Search**: "Dr. Kim" → "Dr. Chulsu Kim" matching
2. **Filtering**: Separate data by topic and hospital
3. **Dynamic Data**: Event period checking

### 4.2 Leveraging Qdrant Vector DB

#### Topic-Based Data Structuring

All hospital information is stored in a single collection, classified by metadata.

**Topic Classification System:**

| topic | sub_topic | Description |
|-------|-----------|-------------|
| `INTRODUCTION` | `INFO`, `OPENING_HOURS`, `PROCEDURE`, `NOTICE` | Hospital intro |
| `VISIT_GUIDE` | `PARKING`, `PUBLIC_TRANSPORT`, `FACILITY_LOCATIONS` | Visit guide |
| `MEDICAL_STAFF` | - | Medical staff info |
| `MEDICAL_SERVICE` | - | Medical services |
| `EVENT` | - | Events/Promotions |

#### Metadata Filtering Strategy

Searches always filter by `client.id` and `topic` to return only accurate data.

### 4.3 Information Search Tool Design

Key tools used by InfoAgent:

| Tool | Function | Notes |
|------|----------|-------|
| `get_introduction` | Hospital intro, hours query | Sub-categorized by sub_topic |
| `get_visit_guide` | Directions, parking info | Filtered by transport type |
| `get_medical_staffs` | Medical staff search | Semantic search for fuzzy matching |
| `get_medical_services` | Medical service info | Includes pricing, procedures |
| `get_events` | Event/promotion search | Date filtering applied |

### 4.4 Key Design Points

**Important considerations for InfoAgent design:**

1. **Clear Role Definition**: Limited scope as "information guide"
2. **No Guessing**: Emphasize using only tool search results
3. **Transition Rules**: Transfer to BookingAgent for booking inquiries
4. **Response Examples**: Provide expected behavior patterns

---

## 5. Implementing BookingAgent

### 5.1 Booking Flow Design

Hospital booking seems simple but requires multiple steps.

```
User: "I'd like to make an appointment"
          │
          ▼
    ┌─────────────┐
    │ Select Dept │ ← get_medical_departments()
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ Confirm Date│ ← "next Tuesday" → "2024-12-17"
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ Select Time │ ← select_available_schedules()
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │Create Appt  │ ← add_new_appointment()
    └──────┬──────┘
           │
           ▼
    "Your appointment has been scheduled"
```

**Key Challenges:**
- Natural language date ("next Tuesday") → ISO date conversion
- Multi-turn conversation for information gathering (date → time → confirmation)
- Handle mid-flow exits or change requests

### 5.2 Booking Tools Overview

Key tools used by BookingAgent:

| Tool | Function | Notes |
|------|----------|-------|
| `get_my_appointment_list` | Query existing appointments | Filtered by patient info |
| `get_medical_departments` | Available departments list | Distinguishes new/returning patients |
| `select_available_schedules` | Date/time selection | Multi-turn via AgentTask |
| `add_new_appointment` | Create appointment | Collects DOB if not registered |

### 5.3 Multi-turn Conversation Handling: Using AgentTask

Appointment time selection requires multiple conversation turns. We implemented this using LiveKit's `AgentTask`.

#### What is AgentTask?

A regular `function_tool` executes once and ends, but `AgentTask` can have **its own conversation loop**.

#### ScheduleSelectionTask State Flow

```
collect_date → confirm_date → select_time → complete
```

1. **collect_date**: Ask for desired date
2. **confirm_date**: Confirm interpreted date ("Is December 17th correct?")
3. **select_time**: Present available times and get selection
4. **complete**: Selection complete, Task ends

### 5.4 Booking Flow Summary

| Step | Tool | Description |
|------|------|-------------|
| 1 | `get_medical_departments` | Department selection |
| 2 | `select_available_schedules` | Date/time selection (multi-turn Task) |
| 3 | `add_new_appointment` | Create appointment |

---

## 6. Agent Routing (Transitions)

### 6.1 Role of TriageCoordinator

TriageCoordinator acts as a **switchboard operator**. It receives the call, understands the purpose, and connects to the appropriate handler (Agent).

```
┌─────────────────────────────────────────────────────────┐
│                   TriageCoordinator                      │
│                                                          │
│  User: "I'd like to make an appointment"                │
│                │                                         │
│                ▼                                         │
│  ┌─────────────────────────┐                            │
│  │ Intent Classification    │                            │
│  │ - Booking keyword detect │                            │
│  │ - Call route_to_booking  │                            │
│  └───────────┬─────────────┘                            │
│              │                                           │
│              ▼                                           │
│  ┌─────────────────────────┐                            │
│  │ Transfer to BookingAgent│                            │
│  │ + Pass user utterance   │                            │
│  └─────────────────────────┘                            │
└─────────────────────────────────────────────────────────┘
```

**TriageCoordinator Routing Branches:**

| User Intent | Keyword Examples | Tool Called |
|-------------|------------------|-------------|
| Booking | "appointment", "schedule", "reschedule" | `route_to_booking` |
| Information | "hours", "doctor", "parking" | `route_to_info` |
| Human Agent | "representative", "person", "staff" | `transfer_call` |
| Answering Machine | (beep sound detected) | `detected_answering_machine` |

### 6.2 Context Passing Methods

When transitioning Agents, **the user's original utterance** must be passed to the next Agent. Otherwise, the next Agent has to ask from the beginning.

```
# Wrong: No context passing
User: "I'd like to book internal medicine"
Triage → Booking transition
Booking: "Which department would you like?" ← Asks again (bad UX)

# Correct: Context passing
User: "I'd like to book internal medicine"
Triage → Booking transition (user_request="I'd like to book internal medicine")
Booking: "I'll help with internal medicine. What date works for you?" ← Natural
```

### 6.3 Audio Input Control (set_audio_enabled)

If users keep talking during Agent transitions, confusion occurs. To prevent this, **audio input is temporarily blocked during transitions**.

**Why is this needed?**

```
Without audio control:
User: "I want to book internal medicine next week"
       ├── Triage hears "book" and starts transition
       ├── "internal medicine next week" stays with Triage
       └── Booking doesn't receive it → Has to ask again

With audio control:
User: "I want to book"
       ├── Triage: calls route_to_booking
       ├── set_audio_enabled(False) → Block input
       ├── Agent transition complete
       ├── set_audio_enabled(True) → Resume input
       └── User: "internal medicine" → Booking receives normally
```

---

## 7. Real-World Challenges

### 7.1 Natural Language Date/Time Parsing

Users don't say dates like "2024-12-20".

**Actual User Utterances:**
- "Next Tuesday"
- "End of this month"
- "Day before Christmas"
- "Tomorrow morning"
- "The 12th" (month omitted)

#### Solution Strategy

Rule-based parsing has limitations, so we **use LLM to convert natural language to ISO dates**.

Passing today's date along with the user's expression allows the LLM to convert "next Tuesday" to "2024-12-17" format.

Korean time expressions ("9 AM", "3:30 PM") are also handled with separate parsing logic.

### 7.2 Handling User Silence

Surprisingly many cases where people answer but say nothing.

**Silence Scenarios:**
- Answered but surroundings too noisy to hear
- Answered but doing something else
- Answering machine picked up

#### Solution Strategy: Using user_state_changed Event

LiveKit notifies user state changes via events.

- Start confirmation task when `away` state detected
- Cancel task if user speaks
- End call after 2 silent attempts

### 7.3 Counselor Connection Fallback

AI can't handle everything. Cases requiring human agent connection:

- User explicitly requests ("Connect me to a representative")
- Complex inquiries AI can't handle
- Emergency situations

#### Solution Strategy

Behavior varies based on configuration:

- **AI Booking Mode**: BookingAgent directly handles booking
- **Agent Connection Mode**: Attempt SIP transfer
- **No Transfer Number Set**: Collect message only and end

### 7.4 Answering Machine (ARS) Detection

Outbound calls sometimes connect to answering machines. The AI shouldn't keep trying to converse.

**Detection Conditions (all 3 must be met):**

| Condition | Description | Example |
|-----------|-------------|---------|
| **Automated Greeting** | Recorded announcement | "This is voicemail service" |
| **Button Input Prompt** | IVR menu prompt | "Press 1", "Leave a message after the beep" |
| **Prompt Repetition/Loop** | No human intervention | Same message repeated 2+ times |

**Why all 3 conditions required?**

```
Checking only 1 condition → High false positives
  e.g., "Hello" auto-greeting ≠ Answering machine

Checking all 3 conditions → High accuracy
  e.g., Auto greeting + Button prompt + Repetition = Definite answering machine
```

Detection triggers call termination and logs the detection event to history.

### 7.5 Prompt System Structure

Voice AI quality heavily depends on prompt design. We use YAML-formatted structured prompts.

**Prompt Sections:**

| Section | Role | Example |
|---------|------|---------|
| **Role** | Role definition | "Hospital appointment AI assistant" |
| **Personality & Tone** | Character/tone settings | "Friendly and professional, 2-3 sentences max" |
| **Instructions** | Core guidelines | "No guessing, use only tool results" |
| **Tools** | Tool usage guide | "Booking: departments → operators → dates" |
| **Conversation Flow** | Conversation flow | "Greeting → Main conversation → Closing" |
| **Safety & Escalation** | Safety rules | "Transfer immediately on agent request" |

**Conversation Flow Rules:**

```
1. Greeting (max 2 attempts)
   └─ Turn 1: Initial greeting
   └─ Turn 2: Hospital name + purpose (brief)
   └─ Turn 2+: No more greeting attempts

2. Main Conversation
   └─ Handle user requests
   └─ Tool calls

3. Closing
   └─ Summary + Farewell
```

**Safety & Escalation Rules:**

| Situation | Action | Confirmation Needed |
|-----------|--------|---------------------|
| Explicit agent request | Transfer immediately | ❌ |
| Appointment change/cancel | Confirm then transfer | ✅ |
| Complaints/profanity | Confirm then transfer | ✅ |
| Information collection failure | Confirm then transfer | ✅ |

---

## 8. Call Termination and Post-Processing

### 8.1 Handling Different Termination Scenarios

Call termination occurs through various paths. Each scenario needs appropriate handling.

| Scenario | Trigger | Handling |
|----------|---------|----------|
| **User Request** | "Hang up", "End call" | Thank and terminate |
| **System Termination** | No response, error, task complete | Notify and terminate |
| **Agent Transfer** | SIP transfer success | Keep Room (AI exits) |
| **Disconnection** | User hangs up first | Immediate cleanup |

### 8.2 Post-Session Processing

Several post-processing tasks are needed after call termination.

**Post-Processing Tasks:**

1. **Stop Recording**: Stop Egress and save file
2. **Call Complete Notification**: Publish MQ message (aiu-agent-call-complete)
3. **Conversation Analysis Request**: Publish MQ message (aiu-agent-call-start-analysis)
4. **Transcript Save**: Save locally for debugging in local environment

**Data Sent to Analysis Service:**
- Call session info (room_name, recipient, business, time info)
- Full conversation history (role, content)

---

## 9. Conclusion

### 9.1 Lessons Learned

#### The Power of Multi-Agent

After experiencing chaos with a single Agent handling everything—200-line prompts, 14 tools—we truly felt the **importance of role separation**.

```
Before: One all-purpose Agent → Complex, unstable, hard to maintain
After: Role-specific Agents → Simple, stable, independent modifications possible
```

#### Importance of Framework Selection

LiveKit Agents provided framework-level support for Multi-Agent transitions, voice processing, and SIP integration, speeding up development. Direct WebRTC handling or implementing Agent transition logic ourselves would have taken much longer.

#### Real Users Behave Unexpectedly

- Natural language date expressions like "next Tuesday"
- Cases of silence after answering
- Suddenly switching to different questions mid-conversation

Rule-based approaches have limits, making LLM utilization essential.

### 9.2 Areas for Improvement

#### Conversation Flow Enhancement

Currently using step-by-step questions, but want better handling when users provide lots of information at once.

```
Current: "Date?" → "December 17th" → "Time?" → "10 AM"
Goal: "Book for December 17th at 10 AM please" → Process at once
```

#### Monitoring Dashboard

Need a real-time dashboard showing call success rate, average processing time, frequently asked questions, etc.

### 9.3 Next Article Preview

The next article will cover more advanced topics:

- **AgentTask Deep Dive**: Implementing complex multi-turn conversation patterns
- **Performance Optimization**: Reducing latency, prompt tuning
- **Call Analysis Pipeline**: Conversation analysis and insight extraction

---

## Final Thoughts

Building this hospital voice AI taught us that **"a single phone call" is more complex than it seems**.

Beyond simply answering questions:
- Understanding user intent
- Multi-turn information gathering
- Exception handling (silence, answering machines)
- Human agent connection fallback
- Post-call processing

Handling all of this naturally is what makes a true "AI assistant."

Thanks to LiveKit Agents, we could implement these complex requirements relatively quickly. We hope this helps those considering voice AI.

Questions and feedback are always welcome!

---

## Meta Information

| Item | Content |
|------|---------|
| Estimated Reading Time | 12-15 minutes |
| Difficulty | Intermediate (Python, basic Voice AI knowledge required) |
| Target Audience | AI/LLM developers, Voice AI beginners, Healthcare IT developers |
| Keywords | LiveKit, Voice AI, Multi-Agent, Hospital Booking, Qdrant, Multi-language |
