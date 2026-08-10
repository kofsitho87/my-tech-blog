---
article_id: "config-driven-voice-agent"
title: "Config-Driven Voice AI Agent: Beyond IVR Call Flows"
description: "A config-driven voice AI architecture combining deterministic call flow control with LLM agents — built and tested in a real hospital call center."
author: "Dan"
date: "2026-04-20"
language: "en"
korean_version: "docs/articles/ko/beyond-ivr-config-driven-voice-agent.md"
english_version: "docs/articles/en/beyond-ivr-config-driven-voice-agent.md"
tags: ["voice AI", "LLM agents", "telephony", "call center", "LiveKit", "config-driven", "SupervisorAgent", "call flow", "DTMF", "IVR"]
og_title: "Config-Driven Voice AI Agent: Beyond IVR Call Flows"
og_description: "A config-driven voice AI architecture combining deterministic call flow control with LLM agents — built and tested in a real hospital call center."
og_image: "docs/articles/images/beyond-ivr-voice-agent-og.png"
hero_image: "docs/articles/images/beyond-ivr-voice-agent-hero.png"
twitter_card: "summary_large_image"
canonical_url: "/blog/config-driven-voice-ai-agent-beyond-ivr"
---

# Beyond IVR: Building a Config-Driven Voice AI Agent with Declarative Call Flows

*By Dan · April 20, 2026*

---

## 1. Introduction: The Problem with Two Extremes

Every hospital, clinic, and medical office faces the same daily challenge: the phone rings constantly. Appointment requests, cancellations, questions about office hours, insurance inquiries — and behind each call is a real person who wants a fast, accurate answer without navigating a maze.

For decades, the industry's answer was the **Interactive Voice Response (IVR)** system. Press 1 for appointments. Press 2 for billing. Press 0 to speak to an agent. Simple, predictable, cheap to run. But also:

- Rigid. Changing a single menu option means a developer ticket, a deployment, and a prayer nothing breaks.
- Frustrating. Callers who don't fit the predefined paths hit dead ends.
- Dumb. IVR has no understanding of context, no ability to adapt, and no memory of the caller.

The natural evolution — replacing IVR with a **pure large language model (LLM) voice agent** — solves the flexibility problem but introduces a new one: unpredictability. An LLM can handle nuanced conversation beautifully, but in a production telephony system you need guarantees:

- The greeting message must play *before* the caller can speak.
- The call must not transfer to a human agent unless specific conditions are met.
- A DTMF keypress of "1" must *always* route to bookings, never somewhere else.
- The call flow must be auditable and changeable by non-engineers.

A freeform LLM agent, by nature, can't make those guarantees. Every response is a generation, and generations vary.

### The Middle Ground

What we needed was something in between: a system that uses AI agents for the parts that require intelligence (understanding a patient's request, looking up available appointment slots, answering complex questions) but uses **deterministic, declarative configuration** to control the overall call flow.

The result is a JSON-based `flow_config` that acts as a call flow blueprint, interpreted at runtime by a `SupervisorAgent` — a state machine that traverses the flow graph node by node, delegating to AI agents only at the right moments.

This post walks through how it works, why we designed it this way, and what we learned building it for a real hospital call center system.

---

> **TL;DR**
> - **The problem:** IVR is too rigid; pure LLM agents are too unpredictable for production telephony.
> - **The solution:** A `flow_config` JSON blueprint + `SupervisorAgent` runtime that handles deterministic routing, while delegating open-ended conversation to specialized LLM agents.
> - **Three core components:** `FlowNode` (5 node types), `SupervisorAgent` (graph traversal engine), and AI agents (BookingAgent, InfoAgent, TriageCoordinator).
> - **Two interaction modes:** DTMF keypress routing (deterministic, auditable) and free voice routing (natural, LLM-driven).
> - **Best fit for:** Healthcare, support, and scheduling systems with multiple routing branches, mixed deterministic + AI steps, and audit trail requirements.

---

## 2. Architecture Overview

The system is organized around three concern areas, each with a distinct responsibility:

```
┌─────────────────────────────────────────────────────────────────┐
│  CONCERN AREA 1: CALL INITIATION                                │
│                                                                 │
│   dial_info (JSON payload)                                      │
│        │                                                        │
│        ▼                                                        │
│   CallSessionData.from_dial_info()                             │
│        │                                                        │
│        ├── business_data    hospital info, operating hours      │
│        ├── recipient_data   caller's name, phone, chart no.     │
│        ├── call_config_data language, transfer settings         │
│        ├── flow_config      ◄── the call flow blueprint         │
│        └── agents_data      refs to all available AI agents     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  CONCERN AREA 2: FLOW CONTROL  (SupervisorAgent)                │
│                                                                 │
│   on_enter()                                                    │
│       └──► _process_node(entry_node_id)                        │
│                   │                                             │
│           ┌───────▼────────┐                                   │
│           │  get_node(id)  │  ◄── looks up FlowConfig          │
│           └───────┬────────┘                                   │
│                   │                                             │
│       ┌───────────▼──────────────────────────────────────────┐ │
│       │              Node Type Dispatch                      │ │
│       ├──────────────────────────────────────────────────────┤ │
│       │ condition → evaluate field, pick branch             │ │
│       │ greeting  → play TTS announcement;                  │ │
│       │             optionally wait for DTMF keypress       │ │
│       │ action    → warm/cold transfer to human, or log     │ │
│       │ exit      → play closing message, shutdown          │ │
│       │ agent     → delegate to AI agent ───────────────────┼─┼──►
│       └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                                                   │
┌──────────────────────────────────────────────────────────────────┘
│  CONCERN AREA 3: AI AGENTS  (specialized, conversational)
│
│  These are the three specialized agents in this system:
│
│   ┌──────────────────────┐   ┌──────────────────────┐
│   │  TriageCoordinator   │   │    BookingAgent       │
│   │  interprets caller's │   │  creates, modifies,   │
│   │  free-speech intent  │   │  cancels appointments │
│   │  and routes to the   │   └──────────────────────┘
│   │  right specialist    │
│   └──────────────────────┘   ┌──────────────────────┐
│                               │      InfoAgent        │
│                               │  answers questions    │
│                               │  about the hospital   │
│                               └──────────────────────┘
└──────────────────────────────────────────────────────────────────
```

> **Note on telephony actions:** Warm/cold transfers are not a separate architectural layer — they are execution details handled *inside* action nodes by the `SupervisorAgent`. They appear in the diagram above under "FLOW CONTROL."

### The Key Insight

Notice the separation of responsibilities:

| Concern Area | Responsibility | Who controls it |
|---|---|---|
| `flow_config` JSON | *What* happens, in *what order* | Product / ops team |
| `SupervisorAgent` | *How* each node is executed | Engineering |
| AI Agents | *What to say* in open conversation | LLM |

This separation means the call flow can be changed — add a menu option, adjust routing by business hours — without touching agent code. In practice, a management UI or template layer often sits above the raw JSON, but the interface contract remains this config structure. When an AI agent does take over, it operates within a guardrail: the `SupervisorAgent` has already made all the sensitive routing decisions before delegating.

---

### What Does `dial_info` Look Like?

Every call session starts with a JSON payload — `dial_info` — delivered when the call is accepted. Here's an abbreviated example:

```json
{
  "call_config_data": {
    "language": "ko-KR",
    "voice": "marin",
    "transfer_to": "01000000000",
    "transfer_mode": "warm_transfer"
  },
  "business_data": {
    "site_id": "example-clinic",
    "client_name": "Example Hospital",
    "is_work_time": true
  },
  "recipient_data": {
    "phone": "01012345678",
    "user_name": "John Doe",
    "birth_date": "1990-01-01",
    "chart_no": "000001"
  },
  "flow_config": {
    "entry_node_id": "greeting",
    "nodes": [ ... ]
  },
  "agents_config": { ... }
}
```

`CallSessionData.from_dial_info()` parses this into typed dataclasses. The `flow_config` field — the call flow blueprint — is what `SupervisorAgent` reads at runtime. We'll see the full `flow_config` in Section 5.

---

## 3. The FlowNode: Five Building Blocks of a Call

A `flow_config` is a directed graph of **nodes**. Each node has a `type` that determines what happens when the `SupervisorAgent` visits it. There are five types, and together they cover every scenario a call flow needs.

```
FlowNode
├── id          unique identifier (also used as routing target)
├── type        condition | greeting | action | agent | exit
├── name        human-readable label
└── ...         type-specific fields
```

---

### 1. `condition` — Branching on Data

A condition node reads a field from the session data and picks the next node based on its value. No audio, no LLM — pure deterministic branching.

```json
{
  "id": "check_work_hours",
  "type": "condition",
  "name": "Check operating hours",
  "field": "business_data.is_work_time",
  "branches": {
    "true":  "greeting_open",
    "false": "greeting_closed"
  }
}
```

**Pseudocode:**
```
value = get_field("business_data.is_work_time")  // → "true"
next  = branches[value] ?? branches["any"] ?? node.next
go to next
```

Fields are resolved by prefix: `business_data.*`, `recipient_data.*`, or `call_config_data.*`. Values are coerced to lowercase strings before lookup, so `True` and `"true"` both match `"true"`.

---

### 2. `greeting` — Announcement + Optional DTMF

A greeting node plays a TTS message. It can then wait for a DTMF keypress and route based on which key was pressed — or simply move on to the next node if no input is needed.

```json
{
  "id": "main_menu",
  "type": "greeting",
  "name": "Main menu",
  "input_method": "dtmf",
  "message": "Press 1 for appointments. Press 2 for hospital information.",
  "dtmf_options": {
    "1": { "next": "booking_agent", "user_request": "Book appointment" },
    "2": { "next": "info_agent",    "user_request": "Hospital info" },
    "*": { "next": "main_menu" }
  },
  "next": "main_menu"
}
```

**Pseudocode:**
```
play TTS(message)
if input_method == "dtmf":
    // GreetingDtmfTask handles internal retries (up to max_invalid_attempts=2)
    // and replays the message on each invalid input.
    // SupervisorAgent only sees the final outcome:
    result = GreetingDtmfTask.run(timeout=5s, max_invalid=2)

    if result.selected_key in dtmf_options:
        // Valid key confirmed after internal retry loop
        save user_request to session (if present)
        go to dtmf_options[result.selected_key].next

    elif result.timed_out:
        // All retry attempts exhausted, or silence throughout
        say "No valid input received. Ending call."
        shutdown()

    else:
        // Key pressed but not in dtmf_options (edge case); use fallback
        go to node.next
else:
    go to node.next            // voice mode: just play message, move on
```

The `user_request` field is particularly useful: it pre-seeds the AI agent with what the caller selected, so the agent doesn't need to ask "How can I help you?" from scratch.

---

### 3. `action` — Telephony Side Effects

An action node performs an operation with a real-world side effect. Depending on the `action_type`, it either continues to the next node (e.g. `log`) or terminates the flow entirely (e.g. `transfer`, `transfer_direct`).

```json
{
  "id": "transfer_to_staff",
  "type": "action",
  "name": "Connect to human agent",
  "action_type": "transfer_direct",
  "action_config": {
    "phone_number": "01000000000",
    "transfer_mode": "warm_transfer"
  }
}
```

| `action_type` | What it does |
|---|---|
| `transfer` | Uses the global `call_config_data.transfer_to` number |
| `transfer_direct` | Uses `action_config.phone_number` directly |
| `log` | Records a message to the session log, continues to `next` |

For `transfer_direct`, the `transfer_mode` determines behavior:

```
warm_transfer → brief the human agent first, then connect caller
cold_transfer → connect caller directly, no briefing
```

After a transfer action completes, the flow ends (`return None`). There is no "next node" — the call is now in human hands.

---

### 4. `agent` — Delegate to an AI Agent

An agent node hands control from the `SupervisorAgent` to one of the specialized conversational AI agents. Within the flow-config runtime, this is a one-way transition: once delegated, the `SupervisorAgent` exits and the specialist agent drives the conversation. The flow graph is not revisited — though the underlying session infrastructure does retain a `prev_agent` reference and a shared transfer helper, neither is used to return to the graph in the current design.

```json
{
  "id": "booking_agent",
  "type": "agent",
  "name": "Booking agent"
}
```

**Pseudocode:**
```
next_agent = agents_data.agents[node.id]   // look up by node id
session.update_agent(next_agent)           // swap the active agent for the session
return                                     // SupervisorAgent exits
```

The `node.id` must match exactly a key registered in `agents_data.agents` at session startup. This is the coupling point between the flow config and the agent registry — adding a new agent type requires both a new agent implementation *and* registering it in `agents_data.agents` under the same key as `node.id`.

---

### 5. `exit` — Graceful Termination

An exit node plays a closing message and shuts down the session. It's the clean end state — used when the caller explicitly wants to hang up, or when a flow path has no useful continuation.

```json
{
  "id": "end_call",
  "type": "exit",
  "name": "End call",
  "message": "Thank you for calling. Have a great day."
}
```

**Pseudocode:**
```
if message:
    play TTS(message)
    wait for playout
log "[CALL_TERMINATION: ACTOR=USER, REASON=<exit_reason>]"  // e.g. EXPLICIT_REQUEST
session.shutdown()
```

---

### How Nodes Connect

Each node declares its `next` field — the default node to visit after it completes. Condition nodes override this with their `branches` map; greeting nodes with DTMF override with `dtmf_options`. Agent and exit nodes never continue — they are terminal.

```
entry_node_id
      │
      ▼
  [condition] ──true──►  [greeting] ──"1"──►  [agent]   (terminal)
       │                     │
     false                  "*"
       │                     │
       ▼                     └──► (replay same greeting)
  [greeting] ──► [exit]    (terminal)
```

---

## 4. SupervisorAgent: The Runtime Graph Traversal Engine

The `SupervisorAgent` is the interpreter that brings a `flow_config` to life. Its job is simple to state: read a node, execute it, find the next node, repeat. But the implementation has a few design decisions worth understanding.

---

### Async Recursive Traversal

The traversal is implemented as an async recursive function — not a loop. Each node handler returns the ID of the next node (or `None` to stop), and `_process_node` calls itself with that ID.

```
_process_node(node_id):
    node = flow_config.get_node(node_id)
    if not node:
        handle_missing_node(); return

    next_node_id = dispatch(node)   // condition / greeting / action / agent / exit

    if next_node_id:
        await _process_node(next_node_id)   // recurse
```

**Why recursion instead of a loop?**

Each node handler is `async` and may `await` real I/O — TTS playout, DTMF input, a transfer call. A recursive call makes it natural for each handler to `return` cleanly after its async work completes, without needing explicit loop state or coroutine management. The depth is bounded by the flow graph itself (typically 3–10 nodes), so stack overflow is not a concern.

---

### Audio Input Control

One of the trickier aspects of a live voice system is controlling *when* the caller's audio is actually processed. If the caller speaks while the greeting TTS is still playing, it can interrupt the announcement and trigger unintended agent behavior.

The `SupervisorAgent` manages this with explicit audio gating:

```
on_enter():
    session.input.set_audio_enabled(False)   // disable mic while Supervisor runs
    ...
    _process_node(entry_node_id)             // traverse the flow

_handle_agent_node():
    session.update_agent(next_agent)         // hand off to AI agent
    // AI agent's on_enter() re-enables audio after its opening TTS completes
```

```
Timeline:

  call starts
      │
      ▼
  [audio INPUT: OFF] ──► greeting TTS plays ──► DTMF captured
                                                     │
                                                     ▼
                                             agent node reached
                                                     │
                                                     ▼
                                         [audio INPUT: ON] ◄── AI agent takes over
```

This means the `SupervisorAgent` phase is entirely one-directional: the system speaks, the caller presses keys or waits. Free speech only becomes possible once an AI agent is active.

---

### Session State Through the Traversal

All nodes in the graph share the same `CallSessionData` object. This is how context built up early in the call — caller identity, selected DTMF option, operating hours — is available to AI agents later without any explicit passing.

```
CallSessionData (shared across all nodes and agents)
    │
    ├── business_data       read by condition nodes
    ├── recipient_data      read by condition nodes, logged at session start
    ├── call_config_data    read by action nodes (transfer settings)
    ├── flow_config         read by SupervisorAgent only
    └── agents_data
            ├── agents      { "booking_agent": <BookingAgent>, ... }
            ├── prev_agent  set when SupervisorAgent hands off
            └── user_request  ◄── set by greeting node (DTMF selection)
```

The `user_request` field is a notable example: when a caller presses "1" for *Book appointment*, the greeting node writes `"Book appointment"` into `agents_data.user_request`. The `BookingAgent` reads this on entry and skips the "How can I help you?" opener — it already knows.

---

### Observability: Structured Session Log

Throughout the traversal, the `SupervisorAgent` writes structured tags into the session's developer history. These are not spoken aloud — they're internal markers that make the call auditable after the fact.

```
[RECIPIENT_DATA: USER_NAME=John Doe, PHONE=01012345678, ...]
[GREETING: STATUS=STARTED]
[GREETING: STATUS=COMPLETED]
[GREETING_DTMF_TASK: SELECTED_KEY=1]
[CALL_TERMINATION: ACTOR=USER, REASON=EXPLICIT_REQUEST]
```

This log is invaluable for debugging. When a call goes wrong — a transfer that didn't fire, a greeting that cut off — you can reconstruct exactly which node was active and what state the session was in at that moment.

---

## 5. A Real-World Example: Hospital Appointment Line

This section traces a complete, production-like call flow for a hospital appointment line. This is the DTMF variant — callers navigate using keypresses.

---

### The Full `flow_config`

```json
{
  "entry_node_id": "greeting_main",
  "nodes": [
    {
      "id": "greeting_main",
      "type": "greeting",
      "name": "Main menu",
      "input_method": "dtmf",
      "message": "Hello! Press 1 to book an appointment, 2 to check an existing booking, 3 to cancel, 4 to modify, 5 for hospital information, 6 to speak with a staff member, or press * to hear this again.",
      "dtmf_options": {
        "1": { "next": "booking_agent",   "user_request": "Book appointment" },
        "2": { "next": "booking_agent",   "user_request": "Check booking" },
        "3": { "next": "booking_agent",   "user_request": "Cancel appointment" },
        "4": { "next": "booking_agent",   "user_request": "Modify appointment" },
        "5": { "next": "greeting_info" },
        "6": { "next": "transfer_staff" },
        "*": { "next": "greeting_main" }
      },
      "next": "greeting_main"
    },
    {
      "id": "greeting_info",
      "type": "greeting",
      "name": "Hospital information submenu",
      "input_method": "dtmf",
      "message": "Press 1 for opening hours, press 2 for directions, press 3 to end the call, or press * to go back.",
      "dtmf_options": {
        "1": { "next": "info_agent",  "user_request": "Opening hours" },
        "2": { "next": "info_agent",  "user_request": "Directions to hospital" },
        "3": { "next": "end_call" },
        "*": { "next": "greeting_main" }
      },
      "next": "greeting_info"
    },
    { "id": "booking_agent",   "type": "agent",  "name": "Booking agent" },
    { "id": "info_agent",      "type": "agent",  "name": "Info agent" },
    {
      "id": "transfer_staff",
      "type": "action",
      "name": "Transfer to human staff",
      "action_type": "transfer",
      "action_config": { "phone_number": "01000000000" }
    },
    {
      "id": "end_call",
      "type": "exit",
      "name": "End call",
      "message": "Thank you for calling. Have a great day."
    }
  ]
}
```

---

### The Flow Graph

```
                    ┌────────────────┐
       ┌──────────► │ greeting_main  │ ◄─────────────────┐
       │ (*)        └───────┬────────┘                   │
       │                    │                             │ (*)
       │         1,2,3,4 ───┤─── 5 ─────────► ┌──────────────────┐
       │                    │                   │  greeting_info   │
       │                    │ 6                 └──┬───────────────┘
       │                    │                      │ 1,2     │ 3
       │                    ▼                      ▼         ▼
       │           ┌─────────────────┐    ┌──────────────┐  ┌──────────┐
       │           │ transfer_staff  │    │  info_agent  │  │ end_call │
       │           │  (action: warm  │    │  (AI agent)  │  │  (exit)  │
       │           │   transfer)     │    └──────────────┘  └──────────┘
       │           └─────────────────┘
       │
       │    1,2,3,4 ──►  ┌────────────────┐
       │                  │ booking_agent  │
       └──────────────────│  (AI agent)   │
                          └────────────────┘
```

---

### Three Caller Journeys

#### Journey A: Book an appointment (press 1)

```
[call starts]
  SupervisorAgent.on_enter()
    → audio input disabled
    → _process_node("greeting_main")
        → play TTS: "Hello! Press 1 to book..."
        → wait for DTMF keypress
        → caller presses 1
        → save user_request = "Book appointment"
        → _process_node("booking_agent")
            → session.update_agent(BookingAgent)
            → SupervisorAgent exits

  BookingAgent.on_enter()
    → audio input re-enabled
    → reads user_request = "Book appointment"
    → greets caller: "I can help you with booking. What date works for you?"
    → conversation continues...
```

Session log at this point:
```
[RECIPIENT_DATA: USER_NAME=John Doe, PHONE=01012345678, ...]
[GREETING: STATUS=STARTED]
[GREETING: STATUS=COMPLETED]
[GREETING_DTMF_TASK: SELECTED_KEY=1]
```

---

#### Journey B: Speak to a human (press 6)

```
[call starts]
  SupervisorAgent.on_enter()
    → _process_node("greeting_main")
        → play TTS: "Hello! Press 1 to book..."
        → caller presses 6
        → _process_node("transfer_staff")
            → action_type = "transfer"
            → _handle_warm_transfer_call(transfer_to="01000000000")
                → brief the human staff member first
                → connect caller
            → return None  ← flow ends here
```

The `SupervisorAgent` never reaches another node after a transfer. The call is in human hands.

---

#### Journey C: Check hospital info, then end call (press 5 → 3)

```
[call starts]
  _process_node("greeting_main")
    → caller presses 5
    → _process_node("greeting_info")
        → play TTS: "Press 1 for opening hours..."
        → caller presses 3
        → _process_node("end_call")
            → play TTS: "Thank you for calling. Have a great day."
            → session.shutdown()
```

Three nodes, zero AI agents involved. The entire interaction is deterministic and config-driven.

---

## 6. Two Flavors: DTMF vs. Free Voice

The same `SupervisorAgent` and `flow_config` engine supports two fundamentally different caller interaction modes. The choice is made per greeting node via `input_method`.

---

### DTMF Mode

The caller navigates by pressing keys. The `SupervisorAgent` waits for a keypress after playing the TTS announcement and routes accordingly. Routing decisions are driven by keypress — the underlying `GreetingDtmfTask` also handles spoken digit input as a fallback, but no LLM reasoning is involved in the routing itself.

**flow_config shape:**
```
entry: greeting_main (dtmf)
           │
    key 1 ─┼─ key 2 ─┼─ key * (replay)
           │          │
     booking_agent  booking_agent
     (AI agent)     (AI agent)
```

**When no valid key is received:**
After `max_invalid_attempts` (default: 2) are exhausted or the timeout expires, the `SupervisorAgent` plays an error message and terminates the call — it does not silently fall back to `node.next`. This is intentional: an unresponsive caller is better handled by ending the call cleanly than by looping indefinitely.

**Best suited for:**
- Environments where audio quality is unpredictable (mobile, VoIP with packet loss)
- High call volumes requiring fast, unambiguous routing
- Regulated industries where routing decisions must be auditable and deterministic
- Callers who are less comfortable with voice-activated systems

---

### Free Voice Mode

The caller speaks naturally. The greeting plays a short welcome message, then immediately hands off to a `TriageCoordinator` AI agent. The coordinator interprets the caller's free-form intent and delegates to the appropriate specialist.

**flow_config shape** *(illustrative — a minimal deployment may use just the greeting node)*:
```json
{
  "entry_node_id": "greeting",
  "nodes": [
    {
      "id": "greeting",
      "type": "greeting",
      "input_method": "voice",
      "message": "Hello, how can I help you today?",
      "next": "triage_coordinator"
    },
    { "id": "triage_coordinator", "type": "agent", "name": "Triage coordinator" }
  ]
}
```

**What the flow looks like at runtime:**
```
greeting (voice)
    │
    └──► play TTS: "Hello, how can I help you today?"
              │
              ▼
         triage_coordinator (AI agent)
              │
    ┌─────────┴──────────┐
    ▼                    ▼
booking_agent       info_agent
(if intent is       (if intent is
 appointment)        information)
```

The `TriageCoordinator` has no fixed menu — it interprets whatever the caller says and routes dynamically. This means a caller who says "I need to cancel my appointment for next Tuesday" goes directly to `BookingAgent` with context intact, without pressing any keys.

**Best suited for:**
- Callers who are unfamiliar with or frustrated by key-press menus
- Use cases where the caller's intent is varied and hard to enumerate up front
- High-quality audio environments (office phones, good mobile signal)

---

### Side-by-Side Comparison

| | DTMF | Free Voice |
|---|---|---|
| Routing mechanism | Keypress → `dtmf_options` lookup | LLM intent classification |
| Determinism | Fully deterministic | Probabilistic (depends on STT + LLM) |
| Audio quality sensitivity | Low — no speech recognition needed | High — poor audio degrades intent accuracy |
| Caller experience | Familiar, fast for known menus | Natural, no memorization required |
| Config complexity | More nodes, explicit branching | Fewer nodes, routing delegated to AI |
| Auditability | `SELECTED_KEY=N` in session log | LLM routing decision (less explicit than key-based routing) |

---

### Mixing Both

The two modes are not mutually exclusive. A single `flow_config` can use DTMF for top-level routing (clear, auditable) and free voice for deeper interactions once the caller is connected to a specialist agent. This is often the right default: use deterministic routing where the stakes are high, and LLM flexibility where nuance matters.

---

## 7. Lessons Learned & Trade-offs

Building and operating this system in a real hospital environment taught us a few things that don't show up in architecture diagrams.

---

### What Worked Well

**Declarative config separated concerns cleanly.**
The biggest win was that product changes — new menu options, rerouting during holidays, adding a transfer number — became config edits, not code changes. When the config is injected externally (e.g., via call metadata or an API), this also means those changes can be deployed without a code release. The engineering team was out of the loop for most operational adjustments. This was the original goal, and it delivered.

**Node isolation made individual behaviors easy to reason about.**
Each node type has one job. A condition node never plays audio. A greeting node never makes routing decisions on its own. An exit node never transfers calls. This made testing and debugging straightforward: when something went wrong in a greeting, the search space was limited to exactly one handler.

**`user_request` pre-seeding eliminated friction at the AI handoff.**
Without it, every caller who pressed "1 for appointments" would still hear "How can I help you?" from the `BookingAgent`. With it, the agent opens with "I can help you book an appointment — what date works for you?" The caller never feels like they started over.

**Agent reuse across modes.**
The same agent implementation can be reused across both DTMF and free-voice modes, because both paths converge at the same agent node. The agent doesn't know or care how the caller got there.

---

### What Was Tricky

**Audio timing is surprisingly hard to get right.**
The sequence — disable mic → play TTS → enable DTMF listener → wait for keypress → re-enable mic for AI agent — has to be choreographed carefully. If audio input is re-enabled too early, a caller's voice can interrupt the greeting and trigger the LLM before the DTMF phase even starts. If it's re-enabled too late, the agent's opening line plays into silence. We spent significant time tuning the handoff between `SupervisorAgent.on_enter()` and the AI agent's own `on_enter()`.

**DTMF keypresses can arrive mid-TTS.**
A caller who already knows the menu will press "1" before the announcement finishes. The `GreetingDtmfTask` handles this by listening for SIP DTMF events in parallel with TTS playback and calling `session.interrupt()` immediately on a valid keypress. Getting this right required careful event ordering and completion state tracking.

**The node.id / agent registry coupling is a silent failure mode.**
If a `flow_config` references `"booking_agent"` as an agent node but the session starts with the key registered as `"BookingAgent"`, the `SupervisorAgent` logs a warning and returns — the flow stalls with only a warning in logs. This is a runtime error that no static validation catches, and it remains a sharp edge worth guarding against with consistent naming conventions.

**The one-way agent transition required clear ownership rules.**
Once the `SupervisorAgent` hands off, it's done. If a `BookingAgent` completes its task and the caller then asks about hospital hours, the `BookingAgent` has to handle that itself or transfer to `InfoAgent` through its own mechanism — there's no "return to menu" path. This is a deliberate constraint, but it means each AI agent needs to handle a broader range of follow-up requests than you might initially expect.

---

### Trade-offs We'd Make Again

| Decision | Why we kept it |
|---|---|
| Async recursion over a loop | Each node handler is naturally `async` with real I/O awaits — recursion keeps the code clean without explicit state machines |
| Shared `CallSessionData` | Passing context through a shared object is simpler than explicit parameter threading across every node; the tradeoff is that any node can mutate shared state |
| Audio gating in `SupervisorAgent` | Simple, explicit, and auditable — even if it requires careful coordination with each AI agent's `on_enter()` |
| JSON flow config over code | Config is reviewable by non-engineers, deployable without a code release, and diff-able in version control |

---

## 8. When to Use This Pattern

The config-driven `SupervisorAgent` architecture is not the right fit for every voice AI system. Here's a practical guide.

---

### Good Fit ✓

**You have multiple distinct routing branches.**
If callers need to reach different specialists (booking, billing, info, transfers), and the routing logic depends on known data (business hours, caller type, keypress), the flow-config graph makes that structure explicit and manageable. Flat single-agent systems don't need it.

**Some steps must be deterministic and some require AI.**
The pattern shines when the two are interleaved: play a fixed greeting, route by keypress (deterministic), then hand off to an LLM agent for the nuanced part. If every step is either fully deterministic or fully LLM-driven, simpler approaches work.

**Non-engineers need to change the flow.**
If your product or operations team needs to add a menu option, swap a transfer number, or adjust routing during holidays — without a code deployment — this pattern gives them a config interface. This only holds if your deployment model injects config externally (e.g., via API or job metadata).

**You need an audit trail for routing decisions.**
Regulated industries, quality assurance, or customer dispute resolution all benefit from knowing exactly which node was visited and what the caller selected. The structured session log provides this out of the box.

**Your system is telephony or voice-first.**
The design assumptions — TTS playout, DTMF events, audio input gating, SIP transfers — are telephony-specific. The pattern applies naturally to inbound call systems; it's less relevant for text chat or non-realtime pipelines.

---

### Poor Fit ✗

**A single AI agent handles everything.**
If one LLM agent can handle the full range of caller intents without branching, the `SupervisorAgent` and flow graph add complexity for no benefit. Just start with the agent directly.

**The flow changes so frequently that JSON configs are still too rigid.**
If routing logic requires conditional expressions, loops, or programmatic generation, a config-driven approach eventually hits its ceiling. In that case, a fully code-driven state machine may be more appropriate.

**Your team has no operational process for managing configs.**
Config-as-data is only an advantage if there's a system for reviewing, versioning, and deploying it. Without that, you get the complexity of two systems (code + config) without the operational benefit.

---

### Quick Checklist

| Question | If yes → | If no → |
|---|---|---|
| Multiple routing branches? | Fits well | May be overkill |
| Mix of deterministic + AI steps? | Fits well | Single-mode is simpler |
| Non-engineers need to edit flow? | Strong fit | Less relevant |
| Audit trail required? | Strong fit | Less relevant |
| Telephony / voice-first? | Designed for this | Adapt with care |
| Single agent, no branching? | Overkill | Use directly |

---

## 9. The Pattern in Production

The core tension in production voice AI is simple: LLMs are flexible but unpredictable; rule-based systems are predictable but rigid. The `flow_config` + `SupervisorAgent` pattern is one answer to that tension — not by picking a side, but by giving each approach the parts of the problem it's actually suited for.

The `SupervisorAgent` handles what needs to be deterministic: the order of operations, the routing branches, the audio gate, the handoff to the right specialist. The AI agents handle what needs intelligence: understanding what the caller wants, responding naturally, looking up data, taking action. Neither side does the other's job.

The result is a system where:
- A product manager can add a menu option in a JSON file
- An engineer can add a new specialist agent without touching the call flow
- An ops team can reconstruct exactly what happened in any call from the session log
- A caller gets the right agent immediately, without being asked twice what they need

This isn't a new idea — separating flow control from conversational logic has parallels in dialogue systems research going back decades. What's new is the context: real-time voice, LLM-powered agents, and the expectation that it all works reliably in a production environment where a dropped call or misrouted patient is a real cost.

If you're building voice AI for anything with meaningful routing complexity — healthcare, support, scheduling, finance — this pattern is worth considering before defaulting to a single all-purpose agent. The configuration overhead is real, but so is the operational clarity you get in return.

---

*Thanks for reading. The full source for the `SupervisorAgent` and `flow_config` schema is part of a larger inbound voice agent system built on [LiveKit Agents](https://docs.livekit.io/agents/).*
