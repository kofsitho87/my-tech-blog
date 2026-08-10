# Building a Voice AI Call Analysis Pipeline

> Sharing our experience developing a post-call conversation analysis system

---

## Table of Contents

1. [Introduction](#1-introduction)
   - Connection to Previous Post
   - Why Call Analysis is Needed
   - What This Post Covers

2. [System Architecture](#2-system-architecture)
   - Overall Pipeline Structure
   - Asynchronous Processing
   - Core Components

3. [Speech Transcription Correction (Step 0)](#3-speech-transcription-correction-step-0)
   - Limitations of Real-time STT
   - Gemini-based Correction System
   - Ghost Message Handling
   - Prompt Design

4. [Conversation Analysis (Step 1)](#4-conversation-analysis-step-1)
   - Metadata Extraction Goals
   - Structured Output with trustcall
   - Applying Hard Rules
   - Challenges in Prompt Design

5. [Conversation Summary (Step 2)](#5-conversation-summary-step-2)
   - Summary Format Design
   - Patient-Centric Summaries

6. [Real-World Challenges](#6-real-world-challenges)
   - Audio File Availability
   - STT Hallucination
   - DTMF Message Handling
   - Business Hours Distinction

7. [Business Logic Integration](#7-business-logic-integration)
   - Booking Mode Branching
   - Analysis Result Utilization

8. [Conclusion](#8-conclusion)
   - Lessons Learned
   - Future Improvements

---

## 1. Introduction

### 1.1 Connection to Previous Post

In our [previous post](./livekit-hospital-voice-agent-en.md), we shared our experience building a hospital Voice AI system using LiveKit Agents. We covered multi-agent architecture, appointment handling, and information retrieval.

This post discusses what happens **after a call ends**. Once a call concludes, we need to answer the question: "What happened during this call?" We need to determine whether an appointment was completed, if the patient responded positively, whether agent transfer was needed, and how to summarize the conversation.

### 1.2 Why Call Analysis is Needed

After a Voice AI call ends, various post-processing tasks are required.

**Problem 1: Real-time STT Errors**

Processing in real-time means speech recognition quality isn't perfect. For example, when a patient says "I'd like to book for tomorrow at 10 AM," the STT might produce mixed-language errors like "I'd like to book for tomorrow at ten AM" with inconsistent formatting.

**Problem 2: Understanding Call Outcomes**

When hundreds of calls occur, it's difficult to manually review what happened in each one.

| Call | Result | Follow-up Action |
| ---- | ---- | ---- |
| A | Appointment completed | None |
| B | Agent requested (connection failed) | Callback needed |
| C | Disconnected during greeting | Retry consideration |
| D | Positive response | Reminder completed |

**Problem 3: Need for Summaries**

For agents to take follow-up actions, they need to quickly understand the call content.

### 1.3 What This Post Covers

This post covers:

- **Speech transcription correction**: Correcting STT errors with Gemini
- **Conversation analysis**: Extracting metadata with LLM
- **Conversation summary**: Automatic patient-centric summaries
- **Pipeline implementation**: RabbitMQ-based asynchronous processing

What we won't cover:

- RabbitMQ installation and configuration (refer to official docs)
- Basic LLM API usage
- Frontend dashboard implementation

Note: specific internal resource names (queues, service names, and log event keys) are anonymized in this post.

---

## 2. System Architecture

### 2.1 Overall Pipeline Structure

The entire system is divided into two parts: Voice Agent System and Conversation Analysis Pipeline.

**Voice Agent System** handles calls through LiveKit Agent Sessions and records conversations. When a session ends, it publishes a message to a call-analysis start queue (e.g., `call-analysis-start`) via RabbitMQ.

**Conversation Analysis Pipeline** receives messages and performs 3-step processing:

1. **Step 0 - Transcriber**: Speech transcription correction using Gemini 2.5 Pro
2. **Step 1 - Analyzer**: Conversation metadata extraction using Claude Sonnet 4.5 or GPT-4.1
3. **Step 2 - Summarizer**: Conversation summary generation using GPT-4.1

Once processing is complete, results are published to a backend API (DB storage) and an event bus (real-time event propagation).

### 2.2 Asynchronous Processing

Call analysis is processed **asynchronously**.

With synchronous processing, you would need to wait about 30 seconds after a call ends for analysis to complete before processing the next call, which is inefficient. With asynchronous processing, a message is published to MQ immediately after the call ends, and the next call can be processed right away. Analysis is handled by a separate service.

**Benefits of asynchronous processing:**

- Voice Agent focuses only on call handling
- Analysis service can scale independently
- Analysis failures don't affect call service

### 2.3 Core Components

| Component | Role | Model Used |
| ---- | ---- | ---- |
| **Transcriber** | STT error correction, timestamp measurement | Gemini 2.5 Pro |
| **Analyzer** | Conversation metadata extraction | Claude Sonnet 4.5 / GPT-4.1 |
| **Summarizer** | Conversation summary generation | GPT-4.1 |
| **MQ Consumer** | Message reception and flow management | - |
| **MQ Producer** | Analysis result publishing | - |

---

## 3. Speech Transcription Correction (Step 0)

### 3.1 Limitations of Real-time STT

Real-time speech processing using OpenAI Realtime API is fast but not perfect.

**Common issues:**

| Issue Type | Example | Frequency |
| ---- | ---- | ---- |
| **Ghost Message** | Silence recognized as "yes yes yes" | High |
| **Mixed language errors** | "10 o'clock" → "ten o'clock" | Medium |
| **Order reversal** | User response order errors | Low |
| **Omission** | Short responses not recognized | Medium |

**What is a Ghost Message?**

A fake message that STT recognized even though the patient didn't actually speak. For example, the actual audio contains patient silence or just background noise, but the STT result records a non-existent utterance like "Yes, I understand."

### 3.2 Gemini-based Correction System

The solution is to **re-listen to the original audio**.

Taking Original STT Conversation (text) and Audio File (actual recording) as input, Gemini 2.5 Pro (multimodal LLM) processes them and outputs Corrected Conversation (corrected text) and start_time (start time of each utterance).

**Why Gemini?**

Gemini 2.5 Pro is a multimodal model that can directly understand audio files. It can review audio and text together for correction.

**Processing steps:**

1. Download audio file (wait until available from CDN)
2. Encode audio as Base64
3. Load prompt (different prompts for different models)
4. Send to Gemini with audio
5. Receive results as structured output

### 3.3 Ghost Message Handling

Criteria for identifying Ghost Messages:

**Ghost Message deletion conditions:**

- The utterance is not audible in the audio
- Only silence or noise exists
- Contextually unnecessary utterance

**Ghost Message retention conditions (exceptions):**

- DTMF messages (keypad input, no audio is normal)
- Uncertain cases (hard to hear but might exist)
- Assistant/Developer messages (Ground Truth)

**Why DTMF handling is important:**

DTMF (Dual-Tone Multi-Frequency) is a telephone keypad input signal. For example, when a patient enters the last digits of their ID number, it's recorded as "DTMF: 000102".

DTMF is not voice, so it's normal for it not to be in the audio file. It should not be mistaken for a Ghost Message and deleted.

### 3.4 Prompt Design

Key directives for transcription correction prompts:

**1. Message Filtering & Reordering**

- Remove Ghost Messages: Delete if not in audio
- Keep ALL DTMF Messages: Never delete DTMF
- Reorder Sequences: Reorder according to actual audio sequence

**2. Editing Scope**

- Modifiable: Only user message content can be modified
- Immutable: Assistant, developer messages must never be modified

**3. Metadata Handling**

- role: Preserve original
- interrupted: Preserve original
- start_time: Measure only for user, null for others

**start_time measurement guide:**

- **Definition**: Exact moment when the first syllable of user utterance begins (in seconds)
- **Exclusions**: Silence, breathing, background noise
- **Procedure**: Check previous assistant utterance end time → Measure gap between assistant end and user start → Compare with previous timestamp to verify order
- **Format**: Float (e.g., 21.5, 37.8)
- **Constraint**: Later messages must have larger start_time

---

## 4. Conversation Analysis (Step 1)

### 4.1 Metadata Extraction Goals

The following information is automatically extracted from conversations:

**Agent transfer related:**

| Field | Description | True Condition |
| ---- | ---- | ---- |
| `transfer_call_request` | Agent transfer successful | transfer operation success log exists (e.g., `[TRANSFER_OPERATION: RESULT=SUCCESS]`) |
| `agent_consultation_request` | Agent transfer needed (incomplete) | Transfer attempted but failed/incomplete |

**Call termination related:**

| Field | Description | True Condition |
| ---- | ---- | ---- |
| `end_call_due_to_delay` | Ended due to response delay | System auto-terminated |
| `end_call_by_user_after_greeting` | Ended after greeting | Disconnected right after greeting completed |
| `end_call_by_user_during_greeting` | Ended during greeting | Disconnected during greeting |
| `end_call_by_user_rejection` | Ended after rejection | Patient expressed rejection then terminated |

**Reservation related:**

| Field | Description | True Condition |
| ---- | ---- | ---- |
| `reservation_creation_complete` | Reservation created | reservation create success log exists (e.g., `[RESERVATION_CREATE: RESULT=SUCCESS]`) |
| `reservation_creation_incomplete` | Reservation incomplete | Started but not completed |
| `reservation_inquiry_complete` | Reservation lookup complete | reservation lookup success log exists (e.g., `[RESERVATION_LOOKUP: RESULT=SUCCESS]`) |
| `reservation_cancellation_request` | Cancellation requested | Patient expressed cancellation intent |
| `reservation_change_request` | Change requested | Patient expressed change intent |

**Response related:**

| Field | Description | True Condition |
| ---- | ---- | ---- |
| `positive_response` | Positive response | "Yes, I'll be there" to appointment confirmation |
| `unclear_response` | Unclear response | Response doesn't fit context |
| `information_inquiry` | Information lookup complete | information lookup success log exists (e.g., `[INFO_LOOKUP: RESULT=SUCCESS]`) |

### 4.2 Structured Output with trustcall

#### What is trustcall?

[trustcall](https://github.com/hinthornw/trustcall) is a library developed by William Hinthorn from the LangChain team, created to extract **reliable structured output** from LLMs.

When asking LLMs to generate or modify complex JSON schemas, they often fail or produce unexpected results. trustcall solves this problem through **JSON Patch operations**. Instead of regenerating the entire JSON, it asks the LLM to patch only the parts that need modification, achieving more stable and cost-effective results.

#### Core Benefits of trustcall

| Benefit | Description |
| ---- | ---- |
| **Fast and cheap generation** | Cost savings through patch operations instead of full schema regeneration |
| **Complex schema support** | Stable processing of nested Pydantic models |
| **Automatic retry on validation errors** | Automatic patching to fix validation failures |
| **Prevent information loss** | Prevents unwanted deletions when updating existing data |

#### Basic Usage

To use trustcall, first install it via pip: `pip install trustcall`

The usage process is divided into three main steps:

**Step 1: Define Schema**

Define the data structure you want to extract by inheriting from Pydantic's BaseModel. Each field includes a type along with a detailed description using Field's description parameter. This description plays a crucial role in helping the LLM understand what information to extract.

For example, to extract a user profile, add a description "User's name" to the `user_name` field and "List of user's interests" to the `interests` field.

**Step 2: Create Extractor**

Use the `create_extractor` function to connect the LLM with the schema. Key parameters include:

- `llm`: LLM instance to use (e.g., ChatOpenAI, ChatAnthropic)
- `tools`: List of Pydantic models to use for extraction
- `tool_choice`: Tool name to use (same as model class name)
- `enable_inserts`: When set to True, supports both new record creation and existing record updates

**Step 3: Execute Extraction**

Pass messages to the created extractor's `invoke` method to receive structured results. Input is a dictionary with conversation content in the `messages` key. Results are returned as a list of Pydantic model instances in the `responses` key.

#### Application in Our Project

For conversation analysis, we defined a Pydantic model called `ConversationMetadataForLLM` to define the metadata schema to extract from calls. Each field (e.g., `positive_response`, `reservation_creation_complete`) has a detailed description to guide the LLM in making accurate judgments.

For example, the `agent_consultation_request` field represents "A state where agent consultation is still needed because AI couldn't resolve the issue," with True conditions including failed/incomplete agent transfer attempts in developer logs (e.g., `[TRANSFER_OPERATION: RESULT=REQUESTED/FAILED/ERROR]`) or when the assistant promises follow-up actions like "I'll pass this to an agent."

#### trustcall vs with_structured_output

Differences between trustcall and LangChain's basic `with_structured_output` method:

| Aspect | with_structured_output | trustcall |
| ---- | ---- | ---- |
| Complex schemas | High failure probability | Stable processing |
| On validation error | Simple retry | Partial fix via patch |
| Existing data update | Full regeneration | Patch only changes |
| Cost | Full token regeneration | Savings by generating only patches |

Especially for schemas like ours with 15+ boolean fields and complex conditions, trustcall provides much more stable results.

#### References

- [trustcall GitHub Repository](https://github.com/hinthornw/trustcall)
- [LangChain Official Twitter Introduction](https://x.com/LangChainAI/status/1905663204593992096)
- [trustcall Tutorial (Dragon Forest)](https://dragonforest.in/trustcall-for-data-extraction-langgraph-tutorial/)

### 4.3 Applying Hard Rules

When LLM judgment alone is insufficient, **rule-based corrections** are applied.

**Hard Rule 1: information_inquiry**

Set to True only when information lookup success logs exist. Even if the LLM judges True based only on conversation content, if a corresponding success log (e.g., `[INFO_LOOKUP: RESULT=SUCCESS]`) doesn't exist in actual logs, it's corrected to False.

**Hard Rule 2: transfer_call_request**

Set to True only when transfer success logs exist. Even if "Please connect me to an agent" was said in the conversation, the actual connection success must be determined by logs.

**Hard Rule 3: Enforce Mutual Exclusivity**

If `transfer_call_request=True`, set `agent_consultation_request=False`. If successfully connected to an agent, then "agent transfer needed" status is not applicable.

**Why are Hard Rules needed?**

Problems occur when using only LLM. For example, if the conversation content is "Please connect me to an agent" → AI: "I'll connect you," the LLM might judge `transfer_call_request = True`. But in reality, it only attempted connection, and success must be verified through logs.

If logs only show a transfer request (e.g., `[TRANSFER_OPERATION: RESULT=REQUESTED]`) without success, Hard Rules correct it to `transfer_call_request = False`, `agent_consultation_request = True`.

### 4.4 Challenges in Prompt Design

The most difficult part of analysis prompts is **interpretation accounting for STT errors**.

**Basic principle:**

Due to audio quality and STT limitations, user messages may contain content that doesn't fit the conversation context or is unclear. When user messages don't fit the context, prioritize analyzing the assistant message's response patterns.

**AI response pattern analysis criteria:**

- When AI interprets positively with "Thank you for confirming"
- When AI proceeds to next steps like appointment confirmation or change completion
- When call termination reason is normal completion

**Exception situations (AI response pattern analysis not applied):**

- When AI requests re-confirmation with "Could you say that again?"
- When AI executes error handling protocol

**Application example:**

Even if the user responded unclearly with "What?" but the assistant interpreted positively and proceeded with "Thank you for confirming. Here's your appointment for December 17th at 10 AM," judge `positive_response = True` (AI response pattern-based judgment).

---

## 5. Conversation Summary (Step 2)

### 5.1 Summary Format Design

Summaries consist of two fields:

- **title**: One-line summary title
- **content**: Concise summary body

Example output has title as "Appointment Confirmation - Patient Attendance Confirmed" and content as "- December 17th 10 AM Orthopedics appointment notification / - Patient attendance confirmed / - Parking information provided."

### 5.2 Patient-Centric Summaries

The key to summaries is focusing on **patient's actions/reactions**.

**Requirements:**

- title: Summarize outbound purpose + patient's final status/requests in one line
- content: Describe only key points concisely. Exclude unnecessary small talk, include only content needed for follow-up actions (rebooking, consultation needed, etc.)

**Good summary vs bad summary:**

A bad summary lists the process: "AI greeted. Patient responded. AI confirmed again. Patient confirmed. Call ended."

A good summary is result-focused: title is "Appointment Reminder - Attendance Confirmed" and content is "December 17th 10 AM Orthopedics appointment confirmed / Patient clearly confirmed attendance / Normal termination without additional inquiries."

---

## 6. Real-World Challenges

### 6.1 Audio File Availability

When starting analysis immediately after a call ends, the recording file may not yet be uploaded to CDN.

After call termination, the recording file is uploaded to S3 (1-2 seconds) and CloudFront cache propagates (2-5 seconds) before the file becomes accessible. However, since MQ messages are published immediately, a 404 Error can occur when the analysis service receives the message but the file doesn't exist yet.

**Solution: Polling with Retry**

We implemented logic to wait until the audio file is available on CDN. It checks file existence with HEAD requests and retries after a set time if not found.

| Parameter | Value | Reason |
| ---- | ---- | ---- |
| `max_retries` | 15 | Maximum 45 seconds wait (sufficient margin) |
| `retry_interval` | 3 seconds | Considering CDN propagation time |
| `timeout` | 5 seconds | HEAD requests should be fast |

### 6.2 STT Hallucination

The problem of STT recognizing speech that doesn't exist.

In real situations, while a patient is silent for 3 seconds, STT might recognize "Yes yes yes I understand." This is because background noise is mistaken for voice, or the model overfits to frequently occurring patterns and expects them.

**Solution: Audio-based verification**

Prompt instructions direct to "delete if the utterance is not heard in the audio." However, in uncertain cases (might exist but hard to hear), the original is preserved.

### 6.3 DTMF Message Handling

DTMF is a keypad input signal, not voice.

When a patient enters the last digits of their ID as 0-0-0-1-0-2, the conversation log records 6 messages like "DTMF: 0", "DTMF: 0", "DTMF: 0", "DTMF: 1", "DTMF: 0", "DTMF: 2".

**Problem: Mistaken for Ghost Message**

The "DTMF: 0" utterance isn't heard in the audio (of course, it's keypad input). If judged as Ghost Message and deleted, important information is lost.

**Solution: DTMF Exception Handling**

We explicitly added instructions to the prompt: "DTMF messages are keypad input signals, NOT voice. No audio exists for DTMF — do NOT treat as ghost messages. Preserve EVERY DTMF message exactly as-is. Do NOT deduplicate, merge, or delete any DTMF messages. Set start_time to null for DTMF messages."

### 6.4 Business Hours Distinction

When an agent transfer was requested but not connected, **business hours inside/outside** must be distinguished.

Inside business hours non-connection requires immediate callback, while outside business hours non-connection is handled the next business day.

When publishing analysis results, if `agent_consultation_request` is True, a business-hours flag field is set based on work-time status (inside vs. outside business hours).

---

## 7. Business Logic Integration

### 7.1 Booking Mode Branching

Different hospitals have different appointment handling methods:

| Mode | Description | Behavior |
| ---- | ---- | ---- |
| `ai` | AI direct booking | Booking component calls reservation API |
| `human` | Agent transfer | Phone transferred to agent |

**Special handling for human mode:**

When in appointment request (agent transfer) mode, agent contact exists, and reservation creation is incomplete (not a cancellation/change request), set the human-handling reservation request flag to True.

**Why is this branching needed?**

In human mode, when a patient says "I want to make an appointment," the AI responds "I'll connect you to an agent." If agent connection was attempted but failed, the analysis result sets `reservation_creation_incomplete = True` (started but not completed) and a human-handling reservation request flag to True (agent should handle this). The backend then adds this to the "Agent callback needed" list.

### 7.2 Analysis Result Utilization

Analysis results are used for various purposes:

**1. Dashboard Statistics**

Today's call analysis results generate statistics like: Total calls 150, Appointments completed 45 (30%), Positive responses 82 (55%), Agent needed 23 (15%, 15 during business hours/8 outside), Disconnected during greeting 12 (8%).

**2. Agent Work Queue**

Automatically generates callback needed list. For example: "010-1234-5678 - Appointment change request (during business hours)", "010-2345-6789 - Agent connection failed (during business hours)", "010-3456-7890 - Unclear response (confirmation needed)".

**3. Quality Improvement Feedback**

If "Disconnected during greeting" rate is high, review whether the greeting is too long, voice tone adjustment is needed, or call timing optimization is required.

---

## 8. Conclusion

### 8.1 Lessons Learned

**1. STT Quality Can Be Improved Through Post-processing**

Accepting the limitations of real-time STT and taking an approach of re-listening to audio afterward for correction was effective. Real-time processing is fast but can be inaccurate, and post-correction is accurate but takes time. Both are needed. Process calls in real-time, correct afterward.

**2. LLM + Hard Rules Combination**

LLM alone cannot accurately handle all cases. When clear criteria exist (log-based judgment), rule-based correction is more stable.

LLM's strengths are context understanding and flexible judgment; weaknesses are occasional errors and inconsistency. Hard Rules' strengths are 100% consistency and predictability; weakness is lack of flexibility. The combination is best.

**3. Benefits of Asynchronous Pipeline**

Operating the analysis service independently means analysis failures don't affect call service, analysis logic changes can be deployed separately, and independent scaling is possible based on load.

### 8.2 Future Improvements

**1. Real-time Analysis**

What if we provided insights **during the call** rather than after it ends? We could provide patient sentiment analysis (suggest agent transfer if negative), intent prediction (seems to want to change appointment), real-time guidance (this patient has previous cancellation history).

**2. Multilingual Transcription Quality Improvement**

Currently Korean-focused, but transcription quality improvement is needed when handling foreign language patients.

**3. Feedback Loop**

A loop is needed to verify if analysis results were correct and improve models/prompts when wrong. The cycle: Analysis result → Agent verification → Feedback collection → Prompt improvement → Better analysis.

---

## Meta Information

| Item | Content |
| ---- | ---- |
| Estimated reading time | 15-20 minutes |
| Difficulty | Intermediate (Python, basic LLM knowledge required) |
| Target audience | AI/LLM developers, Voice AI developers, Healthcare IT developers |
| Keywords | Voice AI, Conversation Analysis, STT Correction, LLM, RabbitMQ, Gemini, trustcall |
| Previous post | [Building a Hospital Voice AI with LiveKit Agents](./livekit-hospital-voice-agent-en.md) |
