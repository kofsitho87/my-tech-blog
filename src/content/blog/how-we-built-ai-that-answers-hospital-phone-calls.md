---
title: 'How We Built an AI That Answers Hospital Phone Calls'
description: 'A practical look at LiveKit, SIP, STT–LLM–TTS, tool calling, and the real-time engineering problems that exist beyond the language model.'
pubDate: '2026-05-06'
heroImage: '../../assets/blog/livekit-hospital-voice-ai-hero.png'
articleId: 'livekit-hospital-voice-ai'
lang: 'en'
draft: false
sourceRepo: 'inbound'
topics: ['product-overview', 'agent-architecture']
---

A patient finishes speaking.

From that moment, the system has only a brief window to decide whether the caller is truly done, transcribe the audio, understand the request, retrieve real information, generate a response, and begin playing speech.

If the silence lasts too long, the caller may think the line has dropped. If the AI responds too early, it interrupts the patient. If it says an appointment is available without checking the booking system, the conversation may sound convincing while producing the wrong real-world result.

This is what makes phone-based AI different from a chatbot.

For a voice agent, audio is not merely another input and output format. **Latency, silence, interruption, call state, and shutdown behavior are all part of the user experience.**

Our team is building an inbound voice AI that answers calls to hospitals and can:

- Play greetings and recording disclosures
- Route requests through speech or DTMF keypad input
- Check appointment availability and create bookings
- Look up, reschedule, or cancel existing appointments
- Answer approved questions about hospital hours and services
- Transfer callers to a human agent when necessary
- Send recordings and conversation events to a post-call analysis pipeline

The real-time communications foundation is [LiveKit](https://docs.livekit.io/intro/about/). The framework that lets the AI listen, reason, act, and speak inside that environment is [LiveKit Agents](https://docs.livekit.io/agents/).

The language model matters, but it is only one component of the system.

---

## The Mental Model: Room, Participant, and Track

LiveKit is an open-source real-time communications framework and cloud platform. Under the hood, it handles problems such as WebRTC media transport, routing, session management, and adaptation to changing network conditions.

The easiest comparison is a video conference, but the same model can power telephone services and real-time AI assistants.

Three concepts make the architecture easier to understand:

- A **Room** is one real-time session. In our system, one patient call becomes one Room.
- A **Participant** is a person or program connected to that Room. The patient, the AI agent, and a human representative can all be Participants.
- A **Track** is a stream published or received by a Participant. The patient's voice and the AI's synthesized speech are audio Tracks.

This model is useful because the caller and the AI do not need entirely separate abstractions. They are simply participants exchanging audio inside the same real-time space.

```text
LiveKit Room — one hospital call

Patient (SIP Participant)
          ⇅ audio
Voice AI (Agent Participant)
          ↘ transfer when needed
       Human agent (SIP Participant)
```

A normal HTTP interaction ends after a request and a response. A call is continuous. Audio keeps flowing, while participants join, leave, publish media, stop speaking, interrupt, or disconnect.

LiveKit gives us a structured way to manage that changing state.

---

## LiveKit Connects the Call. LiveKit Agents Runs the AI.

The names are similar, but their responsibilities are different.

LiveKit provides the communication layer:

- Rooms and Participants
- Real-time audio, video, and data transport
- WebRTC connectivity and network adaptation
- SIP telephony integration
- Media Track publication and subscription
- Recording and session events

LiveKit Agents provides the AI application layer:

- Agent and session lifecycle
- STT, LLM, and TTS integration
- Turn and endpoint detection
- Interruption handling and audio playout
- Tool calls and conversation state
- Per-call agent jobs

One way to think about it is this:

> **LiveKit is the call room. LiveKit Agents is the AI representative working inside it.**

A Python or Node.js agent joins a Room as a Participant. It receives the caller's audio, processes it through AI models, and publishes synthesized speech back into the same Room.

That sounds straightforward. The details are not.

---

## How a Regular Phone Call Reaches the AI

Patients do not open a browser or install a special application. They call the hospital's regular phone number.

The bridge between the telephone network and LiveKit is **SIP**, or Session Initiation Protocol. A call from the public switched telephone network reaches a LiveKit SIP endpoint through a carrier or SIP trunk provider.

The connection sequence looks like this:

```text
1. The patient calls the hospital number.
2. The carrier or SIP provider sends a SIP INVITE to LiveKit.
3. A dispatch rule creates or assigns a Room.
4. LiveKit requests a job from the agent server.
5. The server starts an AgentSession for that call.
6. The voice AI joins the Room and begins the greeting.
```

An inbound trunk defines which calls LiveKit should accept. A dispatch rule decides which Room and agent should handle each call. The connected caller appears in the Room as a `SIP Participant`.

This abstraction keeps the business logic from becoming tightly coupled to the access channel. Whether someone arrives through the telephone network or a microphone in a web application, the agent can focus on the audio and state available inside the Room.

LiveKit's [SIP primer](https://docs.livekit.io/reference/telephony/sip-primer/) and [guide to accepting calls](https://docs.livekit.io/telephony/accepting-calls/) explain the telephony layer in more detail.

---

## How the AI Listens, Thinks, Acts, and Speaks

It is tempting to imagine a single model that hears speech and immediately responds with speech. Real-time speech-to-speech models can work that way, but our current system uses a modular **STT–LLM–TTS pipeline**.

```text
Patient audio
    ↓
VAD and turn detection — Has the caller finished?
    ↓
STT — Speech becomes text
    ↓
LLM — Understand the request and choose the next action
    ↓
Tools and Tasks — Booking, FAQ, or transfer
    ↓
TTS — Text becomes speech
    ↓
Audio plays to the patient
```

### STT: Turning Telephone Audio into Text

The speech-to-text model receives the patient's audio as a live stream. Telephone audio is difficult: it can contain background noise, quiet speech, compression artifacts, names, hospital departments, and physician names.

Accuracy matters, but so do streaming performance and language-specific quality.

### LLM: Understanding the Request

The LLM uses the transcript, conversation history, and hospital configuration to decide what should happen next.

In production, its role is not limited to writing a helpful sentence. If the patient wants an appointment, the system must use a booking tool. If the caller asks about hospital information, the response must stay within approved data. If the request needs human judgment, the agent must enter a transfer workflow.

### Tools and Tasks: Where Language Becomes Real Work

There is a critical difference between saying “I booked that for you” and successfully creating an appointment in the hospital's system.

Tools and Tasks connect the model's intent to operations that can be verified.

A booking flow might:

1. Collect the department, physician, date, and time constraints.
2. Query the booking API for slots that are actually available.
3. Present only valid options.
4. Ask for final confirmation.
5. Create the appointment.
6. Record the API result as a conversation event.

The API result—not the model's confidence—determines whether the booking succeeded.

### TTS: Producing Speech That Works on a Call

The text-to-speech model turns generated responses and predefined prompts into audio.

Naturalness is only one requirement. We also care about:

- How quickly the first audio begins
- Whether dates, times, and numbers are pronounced correctly
- Whether playback stops when the caller interrupts
- Whether critical disclosures and confirmations play completely

A modular pipeline lets us choose each model independently and trace errors or latency to a specific stage. The tradeoff is accumulated delay, which makes streaming and preemptive generation important.

---

## The Runtime Architecture

LiveKit connects the patient and the AI. The application layer above it executes each hospital's call flow and business rules.

Our runtime centers on three components:

- `AgentServer` waits for dispatch requests and starts one job per call.
- `AgentSession` combines STT, LLM, TTS, VAD, turn detection, and interruption settings into one live conversation.
- `SingleAgent` follows the hospital's `flow_config` and runs the Tools and Tasks for booking, FAQ responses, and human transfer.

The full path looks like this:

```text
Patient call
    ↓
SIP / LiveKit Telephony
    ↓
LiveKit Room
    ↓
AgentServer — per-call job
    ↓
AgentSession — STT, LLM, TTS, and turn handling
    ↓
SingleAgent — executes flow_config
    ├── Greeting and DTMF
    ├── Booking Tools and Tasks → Booking API
    ├── Hospital FAQ → Approved hospital information
    └── Human transfer → Human agent

LiveKit Room → Recording through Egress → S3
AgentSession → Conversation and tool events → Kafka → Post-call analysis
```

The real-time path focuses on the current conversation. Recording, classification, summarization, and quality analytics can continue asynchronously after the call.

That separation protects response time. Expensive analysis does not need to block a patient waiting on the phone.

---

## Why the Call Flow Is Configuration-Driven

Hospitals do not all answer calls in the same way.

One hospital may begin with “Press 1 for appointments.” Another may want the caller to speak immediately. Transfer policies can change outside business hours. Appointment, information, and escalation rules vary by site.

Hard-coding every variation would require a deployment whenever a hospital changes its policy. We therefore define the high-level call flow in `flow_config`.

The configuration can include nodes such as:

- `greeting` to play an announcement and optionally collect DTMF input
- `condition` to choose a path using business hours or session state
- `agent` to enter an open-ended conversational section
- `action` to transfer a call or record an event
- `exit` to play a closing message and shut down safely

This creates a useful division of responsibility:

> **Configuration controls what happens and in what order. The LLM and agent determine how to understand and respond to natural language.**

DTMF and conversational AI also work better together than either does alone. Keypad input is useful when exact digits or deterministic menu choices matter. Natural language is better for a request such as, “I'd like an orthopedics appointment next Monday afternoon.”

The goal is not to replace every phone interaction with free-form AI. It is to use deterministic controls where certainty matters and language models where flexibility matters.

---

## The Hardest Problems Often Exist Outside the LLM

A strong language model does not automatically create a good phone service. Much of the difficult engineering work happens at conversation boundaries and in asynchronous state management.

### Knowing When the Caller Has Finished

Voice activity detection can tell whether sound is present. It cannot always tell whether a thought is complete.

Consider a patient saying:

> “Next week... one moment... Wednesday.”

If the system treats the middle pause as the end of the turn, the AI starts answering too early.

Turn detection and endpointing combine speech activity, context, and timing. The system must avoid interrupting the caller without leaving an awkward silence after every sentence.

### Handling Interruptions Without Reacting to Every Noise

People interrupt naturally:

> “No, not the morning—the afternoon.”

The agent should stop its current response and process the correction. But if every cough, acknowledgment, or background sound interrupts playback, the AI becomes unusable.

We need policies for minimum speech duration, minimum word count, and false-interruption recovery. Critical messages, including recording disclosures and final booking confirmations, may need different rules from ordinary dialogue.

### Measuring the Latency Callers Actually Feel

The delay after the caller stops speaking is not a single metric.

```text
End-of-turn decision
    + final STT result
    + first LLM token
    + Tool or API time
    + first TTS audio
    = perceived response latency
```

Even when every component seems reasonably fast, the total can feel slow. We measure each stage separately, stream generated audio, preload what we can, and provide a short progress message when an external API takes noticeable time.

### Ending a Call Safely

A caller can hang up while the AI is speaking, a booking request is running, a recording is finalizing, the Room is closing, and a Kafka event is being published.

Those operations do not complete as one atomic event.

Shutdown that is too slow leaves workers occupied. Shutdown that is too aggressive can lose the last audio or analysis event. The order of disconnect handling, session shutdown, recording completion, and downstream publication has to be designed explicitly and made safe to execute more than once.

### Transferring to a Human

Cold transfer sends the caller to a human and removes the AI. Warm transfer introduces the human first, shares context, and manages the transition until the caller and representative are safely connected.

During a warm transfer, the patient, AI, and human can occupy different states inside the same call. The system must control who hears whom, decide what happens if the human does not answer, and prevent multiple transfer attempts from racing with one another.

This is less a phone-number-forwarding problem than a distributed state and concurrency problem.

---

## Why LiveKit Fit Our Use Case

Several aspects of LiveKit and LiveKit Agents matched the way we wanted to build the service:

- Patients, AI agents, and human agents share one clear Participant model.
- Patients keep using the hospital's existing phone number.
- STT, LLM, and TTS providers can be selected independently.
- Python business logic, booking APIs, configuration, Tools, and Tasks integrate naturally.
- Turn detection, interruption handling, transcription, and audio playout do not have to be built from scratch.
- Each call runs as an isolated job, which limits the spread of state and failures.

The [agent server lifecycle](https://docs.livekit.io/agents/server/lifecycle/) is particularly useful here. The server waits for dispatch requests and starts a separate job for each call, allowing one service to handle multiple calls with process-level isolation.

But LiveKit does not solve every product problem for us.

We still need to:

- Evaluate STT, LLM, and TTS combinations for Korean telephone audio
- Balance accuracy, latency, and cost
- Handle hospital names, departments, physicians, dates, and times reliably
- Test the complete path through the carrier and SIP provider
- Add explicit confirmation before irreversible actions
- Define security and retention policies for recordings and personal data

LiveKit is a strong real-time foundation. It is not a finished hospital workflow product.

Reliable voice AI emerges only when communications infrastructure, AI models, business rules, and observability work together.

---

## The Most Useful Shift in Perspective

The most useful architectural idea for us was to stop treating the AI as a request-response API and start treating it as **a participant in a live call**.

The patient and AI join the same Room. They exchange audio through Tracks. LiveKit Agents connects listening, turn detection, response generation, speech playout, and tool execution. Our service layer adds hospital-specific workflows for booking, information, DTMF, human transfer, recording, and post-call analysis.

The quality of the result cannot be explained by the choice of LLM alone.

The system must know when the caller has finished. It must stop speaking at the right moment. It must offer only appointments that are actually available. It must transfer safely to a person. And it must preserve critical data when the call disconnects.

LiveKit provides the real-time communications foundation. LiveKit Agents turns the AI into a conversational Participant. The application layer turns that Participant into something more useful than a talking chatbot:

> **A voice AI that answers the phone and completes real work.**

---

## Further Reading

- [About LiveKit](https://docs.livekit.io/intro/about/)
- [Rooms, participants, and tracks](https://docs.livekit.io/intro/basics/rooms-participants-tracks/)
- [Introduction to LiveKit Agents](https://docs.livekit.io/agents/)
- [LiveKit SIP primer](https://docs.livekit.io/reference/telephony/sip-primer/)
- [Accepting calls with LiveKit Telephony](https://docs.livekit.io/telephony/accepting-calls/)
- [Voice pipeline types](https://docs.livekit.io/agents/models/pipelines/)
- [Turn detection](https://docs.livekit.io/agents/logic/turns/turn-detector/)
- [Turns and interruptions](https://docs.livekit.io/agents/logic/turns/)
- [Agent server lifecycle](https://docs.livekit.io/agents/server/lifecycle/)
