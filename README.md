## AI AGENCY
### from a conversation to an automation in seconds (for non-technical users)

## Problem

Companies and organizations are sloooooow with adopting AI.

Non-technical professionals spend hours on repetitive tasks — compiling reports, sending follow-up emails, syncing data between tools. Existing automation platforms (Zapier, n8n, Make) still require users to:

- Understand concepts like "triggers", "actions", and "connectors"
- Manually configure each step through complex UIs
- Be limited to a fixed set of pre-built integrations


**The gap:** People who would benefit most from automation are the least equipped to set it up.


## Solution

AI Agency is a conversational workflow builder powered by **Mistral AI** and **ElevenLabs**.


1. **Talk** — The user describes their task in natural language via voice (just like a casual conversation with another person)
2. **Refine** — The AI agent asks clarifying questions through a back-and-forth dialogue
3. **Generate** — A structured workflow is automatically created and visualized in real time
4. **Execute** — The workflow is ready to run. The implementation is explained to the user via voice. Tasks complete themselves!



## Architecture


```
┌──────────────────────────────────────────────────────┐
│                    User (Voice)                       │
│                        │                              │
│                   ElevenLabs                          │
│              STT ↓          ↑ TTS                     │
│                        │                              │
│            ┌───────────┴───────────┐                  │
│            │   Mistral AI Agent    │                  │
│            │                       │                  │
│            │  • Multi-turn dialogue│                  │
│            │  • Intent extraction  │                  │
│            │  • Workflow design    │                  │
│            │  • Structured output  │                  │
│            └───────────┬───────────┘                  │
│                        │                              │
│                Workflow JSON                           │
│                        │                              │
│            ┌───────────┴───────────┐                  │
│            │   Execution Router    │                  │
│            │                       │                  │
│            │  Known service        │                  │
│            │   → Composio / API    │                  │
│            │                       │                  │
│            │  Unknown service      │                  │
│            │   → Browser automation│                  │
│            │     (Playwright)      │                  │
│            │                       │                  │
│            │  Text processing      │                  │
│            │   → Mistral LLM       │                  │
│            └───────────┬───────────┘                  │
│                        │                              │
│              Real-time UI feedback                    │
│         (workflow graph + step status)                │
└──────────────────────────────────────────────────────┘
```


Project created during Mistral AI Hackathon in Toyko (Feb28-Mar01 2026)