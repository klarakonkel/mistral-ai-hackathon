# VoiceFlow AI — Build Any Workflow, Just by Talking

## Elevator Pitch

A voice-first AI app that lets **non-engineers** create and run custom automation workflows simply by having a conversation. No code, no drag-and-drop, no learning curve — just describe what you want, and the AI builds and executes it.

## Problem

Non-technical professionals spend hours on repetitive tasks — compiling reports, sending follow-up emails, syncing data between tools. Existing automation platforms (Zapier, n8n, Make) still require users to:

- Understand concepts like "triggers", "actions", and "connectors"
- Manually configure each step through complex UIs
- Be limited to a fixed set of pre-built integrations

**The gap:** People who would benefit most from automation are the least equipped to set it up.

## Solution

VoiceFlow AI is a conversational workflow builder powered by **Mistral AI** and **ElevenLabs**.

1. **Talk** — The user describes their task in natural language via voice
2. **Refine** — The AI agent asks clarifying questions through a back-and-forth dialogue
3. **Generate** — A structured workflow is automatically created and visualized in real time
4. **Execute** — The workflow runs immediately, with results reported back via voice

### What makes this different from existing tools?

> **"The AI IS the integration."**

Unlike Zapier or n8n, we don't rely solely on pre-built connectors. Mistral dynamically generates API calls for any service it knows — meaning the system can adapt to virtually any tool without pre-configured integrations.

For services with well-known APIs, we use Composio for reliable, authenticated access. For everything else, the AI falls back to **browser automation** — directly controlling web apps through the user's browser, just like a human assistant would.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ User speaks                                                   │
│     ↓                                                         │
│ Voxtral Mini Transcribe Realtime (Mistral STT, $0.006/min)   │
│     ↓ [text]                                                  │
│                                                               │
│ Mistral Large 3 (Orchestrator Agent)                          │
│   • Multi-turn dialogue, intent extraction                    │
│   • Clarifying questions ("Which Slack channel?")             │
│   • Delegates workflow generation when ready                  │
│     ↓                                                         │
│                                                               │
│ Fine-tuned Ministral 8B (Workflow Generator)                  │
│   • Natural language → Workflow JSON (fast, accurate)         │
│   • Self-improving via user feedback loop                     │
│     ↓                                                         │
│                                                               │
│ Execution Router                                              │
│   Tier 1: Composio (250+ services)                            │
│   Tier 2: Dynamic API call (domain-allowlisted)               │
│   Tier 3: Browser automation (Playwright)                     │
│     ↓                                                         │
│                                                               │
│ Results → ElevenLabs TTS (character voice, level-based)       │
│                                                               │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ W&B Models: FT metrics, hyperparameter tracking           │ │
│ │ W&B Weave:  LLM call tracing, feedback loop, evaluation  │ │
│ └───────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### Model Roles

| Model | Role | Why |
|-------|------|-----|
| **Voxtral Mini Transcribe Realtime** | Real-time STT (voice → text) | Mistral-native, ultra-low latency, $0.006/min |
| **Mistral Large 3** | Orchestrator agent + teacher for synthetic data | Highest quality reasoning, function calling |
| **Ministral 8B (fine-tuned)** | Workflow JSON generation (student) | Fast, cheap, FT-able, self-improving |
| **ElevenLabs TTS** | Character voice output (level-based evolution) | Voice customization, style control per level |

## Workflow Definition Format

```json
{
  "name": "Daily AI News Digest",
  "trigger": { "type": "schedule", "cron": "0 8 * * *" },
  "steps": [
    {
      "id": "step1",
      "action": "web_search",
      "params": { "query": "latest AI news today" },
      "output": "news_results"
    },
    {
      "id": "step2",
      "action": "llm_summarize",
      "params": { "input": "{{news_results}}", "style": "bullet_points" },
      "output": "summary"
    },
    {
      "id": "step3",
      "action": "send_email",
      "params": { "to": "user@example.com", "subject": "AI News Digest", "body": "{{summary}}" }
    }
  ]
}
```

## Execution Strategy — Three-Tier Fallback

| Tier | Method | When | Example |
|------|--------|------|---------|
| 1 | **Composio SDK** | Service has a Composio connector (250+ services) | Gmail, Slack, Google Sheets, Notion |
| 2 | **Dynamic API call** | Mistral knows the API but Composio doesn't cover it | Niche SaaS REST APIs |
| 3 | **Browser automation** | No API available or auth is complex | Any web app the user is logged into |

This three-tier approach ensures we can handle **any** service — from mainstream tools down to obscure internal web apps — without needing pre-built connectors for each one.

## Security — Human-in-the-Loop by Design

### Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|------------|
| Arbitrary code execution | Critical | **No `execute_python_code` tool.** All actions are constrained to pre-defined tool types (API calls, service actions). |
| API key / token leakage | High | Credentials are injected server-side at execution time. Mistral never sees raw tokens. |
| Prompt injection | High | User input is sandboxed in conversation context. Workflow JSON is validated against a strict schema before execution. |
| Unintended actions | Medium | **Confirmation step before every execution.** The user reviews the generated workflow and explicitly approves it. |
| Cost runaway | Medium | Max step limit per workflow (10 steps). Rate limiting on API calls. |
| Data privacy | Medium | No conversation logs stored beyond the session. Configurable data retention policy. |

### Domain Allowlist for Dynamic API Calls (Tier 2)

Tier 2 dynamic API calls are restricted to a curated allowlist of domains:

```python
ALLOWED_DOMAINS = [
    "api.slack.com",
    "www.googleapis.com",
    "api.notion.so",
    "api.github.com",
    "api.twitter.com",
    "api.openai.com",
    # ... extensible per user
]
```

Requests to unlisted domains are blocked and flagged for user review.

### Execution Flow with Confirmation

```
User speaks → AI generates workflow → UI shows preview
                                        ↓
                              User reviews each step
                                        ↓
                              User clicks "Run" ✅
                                        ↓
                              Workflow executes
```

This **human-in-the-loop** pattern ensures the AI proposes but never acts autonomously — a key trust signal for both end users and hackathon judges.

## Fine-Tuning & Self-Improving Pipeline

### Overview

The fine-tuning strategy has two phases: initial **knowledge distillation** (SFT) followed by a **self-improving feedback loop** (preference-based re-training). Both are tracked end-to-end with **W&B Models + Weave**.

```
Phase 1: Knowledge Distillation (SFT)
  Mistral Large 3 (teacher) → 250+ synthetic examples → Ministral 8B (student)

Phase 2: Self-Improving Loop (Preference-based)
  User feedback (👍/✏️/👎) → preference data → re-fine-tune → better model
                                                    ↑                │
                                                    └────────────────┘
```

### Why Fine-Tune?

| Metric | Mistral Large 3 (prompt only) | Fine-tuned Ministral 8B |
|--------|-------------------------------|--------------------------|
| Latency | ~2-3s | **~0.5-1s** |
| Cost per call | High | **~1/10** |
| JSON accuracy | Prompt-dependent, variable | **Learned, consistent** |
| Judge impression | "Used the API" | **"Customized the model"** |

### Phase 1: Knowledge Distillation (SFT)

**Step 1: Generate training data with Mistral Large 3 (teacher)**

Use Mistral Large 3 to produce 250+ diverse (request, workflow JSON) pairs:

```
Input:  "Every Friday at 5 PM, pull this week's merged PRs from GitHub,
         write a summary, and post it to #engineering in Slack."

Output: {
  "name": "Weekly PR Summary",
  "trigger": {"type": "schedule", "cron": "0 17 * * 5"},
  "steps": [
    {"id": "s1", "action": "github_list_prs", "params": {"repo": "{{user.repo}}", "state": "merged", "since": "7d"}, "output": "prs"},
    {"id": "s2", "action": "llm_summarize", "params": {"input": "{{prs}}", "style": "weekly_report"}, "output": "report"},
    {"id": "s3", "action": "send_slack_message", "params": {"channel": "#engineering", "text": "{{report}}"}}
  ]
}
```

Data covers diverse scenarios: scheduling, multi-step chains, different services, varying complexity (1-5 steps), multiple languages (EN/JP).

**Step 2: Fine-tune Ministral 8B (student)**

Submit the dataset to Mistral's fine-tuning API with W&B integration:

- Model: `ministral-8b-latest` (recommended for this hackathon)
- Task: Conversation → JSON structured output
- W&B Models integration for training metrics
- Training runs in the background (~1-3 hours)

**Step 3: Deploy with fallback**

```
User request
    ↓
Fine-tuned Ministral 8B (fast, cheap, accurate)
    ↓
If JSON validation fails → retry with Mistral Large 3 (fallback)
```

### Phase 2: Self-Improving Feedback Loop

After initial deployment, the model improves itself through user interactions:

```
┌─────────────────────────────────────────────────────────────┐
│                 Self-Improving Pipeline                       │
│                                                              │
│  1. User requests a workflow                                 │
│  2. FT model generates workflow JSON                         │
│  3. User reviews and provides feedback:                      │
│     👍 Approved as-is    → saved as "chosen" example         │
│     ✏️ Edited then approved → edited version = "chosen",     │
│                              original = "rejected"           │
│     👎 Rejected           → saved as "rejected" example      │
│  4. Feedback accumulates (tracked in W&B Weave)              │
│  5. Every N examples → re-fine-tune with preference data     │
│  6. New model deployed → better accuracy next time           │
└─────────────────────────────────────────────────────────────┘
```

**Preference data format:**

```jsonl
{"messages":[{"role":"user","content":"Search AI news and send to Slack"}],"chosen":{"role":"assistant","content":"{corrected workflow JSON}"},"rejected":{"role":"assistant","content":"{original flawed JSON}"}}
```

If Mistral FT API supports SFT only (no DPO), we use "chosen" examples exclusively for SFT re-training — effectively the same self-improving outcome.

**Connection to gamification:** Character level-up = model improvement. When the character grows, the underlying model is literally getting better at generating workflows. This isn't just cosmetic — it reflects real model improvement.

### W&B Integration (Models + Weave)

Both W&B products are used throughout the pipeline:

**W&B Models — Training & Experiment Tracking:**

```python
# Integrated via Mistral FT API's integrations parameter
job = client.fine_tuning.jobs.create(
    model="ministral-8b-latest",
    training_files=[{"file_id": training_file.id, "weight": 1}],
    validation_files=[validation_file.id],
    hyperparameters={"training_steps": 100, "learning_rate": 0.0001},
    auto_start=True,
    integrations=[{
        "type": "wandb",
        "project": "kotodama-finetuning",
        "api_key": os.environ["WANDB_API_KEY"],
    }]
)
```

Tracks: training loss, validation loss, learning rate schedule, epoch progress, model versions, hyperparameter comparisons across runs.

**W&B Weave — Runtime Tracing & Evaluation:**

```python
import weave
weave.init("kotodama-app")

@weave.op()
def generate_workflow(user_request: str) -> dict:
    response = client.chat.complete(
        model=ft_model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_request}
        ]
    )
    return json.loads(response.choices[0].message.content)

@weave.op()
def collect_feedback(workflow: dict, feedback_type: str, edited: dict = None):
    # All feedback is traced and logged in Weave
    if feedback_type == "approved":
        save_as_chosen(workflow)
    elif feedback_type == "edited":
        save_as_chosen(edited)
        save_as_rejected(workflow)
    elif feedback_type == "rejected":
        save_as_rejected(workflow)
```

Tracks: all LLM calls (input/output/latency), user feedback events, workflow execution results, FT model vs Large accuracy comparison, self-improvement metrics over time.

**W&B Dashboard shows:**

| Panel | What it proves |
|-------|---------------|
| Training loss curve | Model learned the task |
| FT vs Large accuracy comparison | Distillation worked |
| Feedback approval rate over time | Model is self-improving |
| Latency: FT vs Large | 3x speed improvement |
| Cost: FT vs Large | 10x cost reduction |

### Hackathon Timeline for Fine-Tuning

```
Hour 0-1:   Write data generation script, generate 250+ synthetic examples
Hour 1-2:   Clean data, submit SFT job to Mistral API (with W&B Models)
Hour 2-5:   [FT job runs in background] — build main app with W&B Weave tracing
Hour 5+:    Swap endpoint to FT model, validate outputs
Hour 8-10:  Collect 20+ feedback examples, submit re-training job (Phase 2)
Hour 15+:   Demo with improved model, show W&B dashboard
```

**Zero risk:** If fine-tuning doesn't finish in time or quality is poor, we keep using Mistral Large 3. The fallback is the baseline.

### Pitch Line for Judges

> "We distilled Mistral Large 3 into Ministral 8B using 300 synthetic examples, then made it self-improving through a user feedback loop — all tracked end-to-end with W&B Models and Weave. The model gets better every time someone uses it."

## Tech Stack

| Layer | Technology |
|-------|-----------|
| STT (Voice Input) | Voxtral Mini Transcribe Realtime (Mistral, $0.006/min) |
| TTS (Voice Output) | ElevenLabs (character voice with level-based evolution) |
| Orchestrator Agent | Mistral Large 3 (multi-turn dialogue, function calling) |
| Workflow Generator | Fine-tuned Ministral 8B (distilled + self-improving) |
| Tool Integration | Composio SDK (250+ services, OAuth handling) |
| Browser Automation | Playwright (fallback for unsupported services) |
| Fine-Tuning | Mistral FT API + W&B Models (metrics) + W&B Weave (tracing & eval) |
| Backend | Python + FastAPI |
| Frontend | Next.js + React Flow + Tailwind CSS |
| Hosting | Vercel (frontend) + Railway (backend) |

## Gamification — Character Growth System

### Concept

The AI assistant is embodied as a **character ("Flow-chan")** that grows and evolves as the user creates and executes workflows. Every workflow completed earns XP, unlocks skills, and visually transforms the character — turning a productivity tool into an engaging experience.

```
Execute workflow → Earn XP → Level up → New skills & appearance → Want to automate more
                                                                        ↓
                                                              (Engagement loop)
```

### Skill Tree

The character's growth is organized into skill branches based on workflow categories:

| Branch | Icon | Services | Skill Examples |
|--------|------|----------|---------------|
| Communication | 📧 | Email, Slack, Discord, Teams | "Messenger Lv.1" → "Broadcast Master Lv.5" |
| Data | 📊 | Sheets, SQL, Analytics, CSV | "Data Novice Lv.1" → "Analyst Lv.5" |
| Creative | 🎨 | Image gen, Writing, Translation | "Apprentice Lv.1" → "Creator Lv.5" |
| Scheduling | ⏰ | Cron jobs, Reminders, Calendars | "Timekeeper Lv.1" → "Orchestrator Lv.5" |
| DevOps | 🔧 | GitHub, CI/CD, Monitoring | "Script Kiddie Lv.1" → "SRE Lv.5" |

When all branches reach Lv.5+, the character evolves into a **"Master"** form with a unique appearance.

### Character Evolution & Voice Progression (ElevenLabs)

| Level | Appearance | Voice (ElevenLabs) | Unlocked Capabilities |
|-------|-----------|-------------------|----------------------|
| Lv.1 | Simple egg / hatchling | Shy, slow, hesitant | Single-step workflows only |
| Lv.3 | Small creature with accessories | Friendly, moderate pace | Multi-step workflows, basic conditions |
| Lv.5 | Evolved form, skill-branch themed | Confident, natural | Cross-service workflows, error handling |
| Lv.10 | Full evolution, aura effects | Professional, expressive | Complex multi-branch orchestration |

The voice change is driven by swapping ElevenLabs `voice_id` or adjusting `stability` / `style` parameters at each tier — the character literally sounds more capable as it grows.

### Character State Schema

```json
{
  "character": {
    "name": "Flow-chan",
    "level": 7,
    "xp": 2450,
    "xp_to_next": 3000,
    "appearance_stage": "intermediate_v2",
    "voice_config": {
      "voice_id": "confident_assistant",
      "stability": 0.6,
      "style": 0.7
    },
    "skills": {
      "communication": { "level": 3, "workflows_completed": 12 },
      "data":          { "level": 2, "workflows_completed": 5 },
      "creative":      { "level": 1, "workflows_completed": 2 },
      "scheduling":    { "level": 3, "workflows_completed": 8 },
      "devops":        { "level": 0, "workflows_completed": 0 }
    },
    "achievements": [
      { "id": "first_workflow",  "name": "Hello World",     "icon": "🐣", "earned": true },
      { "id": "multi_service",   "name": "Connector",       "icon": "🔗", "earned": true },
      { "id": "10_workflows",    "name": "Automator",       "icon": "⚡", "earned": false },
      { "id": "all_branches",    "name": "Jack of All",     "icon": "🌟", "earned": false },
      { "id": "complex_workflow", "name": "Architect",       "icon": "🏛️", "earned": false }
    ]
  }
}
```

### XP Calculation

```python
def calculate_xp(workflow):
    base_xp = 100
    step_bonus = len(workflow["steps"]) * 50
    service_diversity = count_unique_services(workflow) * 75
    first_use_bonus = 200 if uses_new_service(workflow) else 0
    complexity_bonus = 100 if has_conditions(workflow) else 0
    return base_xp + step_bonus + service_diversity + first_use_bonus + complexity_bonus
```

| Workflow Example | XP Earned |
|-----------------|-----------|
| 1-step email send | 225 (100 + 50 + 75) |
| 3-step: search → summarize → Slack | 475 (100 + 150 + 225) |
| 5-step cross-service with conditions | 850+ |
| First time using GitHub API | +200 bonus |

### Implementation Cost (Hackathon)

| Task | Owner | Time |
|------|-------|------|
| Character state schema + XP logic + level-up API | Klara | ~1h |
| ElevenLabs voice_id swap by level | Koki | ~15min |
| Character visuals (SVG / PNG sprite set, 4-5 stages) | Koki | ~1.5h |
| Level-up animation + XP bar + skill tree UI | Koki | ~1.5h |
| **Total** | | **~4h** |

### Demo Impact

> **[User executes a 3-step workflow]**
>
> **[Screen]:** XP bar fills up... **LEVEL UP!** Character transforms with a flash animation. New skill badge "Slack Master" appears.
>
> **[Character (voice, now more confident)]:** "Nice! I just learned Slack Master! I can now handle threads and reactions too. What should we automate next?"
>
> **[Audience reaction]:** This is not just a tool — it's an experience.

## Hackathon Track & Challenges

| Target | Rationale |
|--------|-----------|
| **Mistral AI Track** | Mistral is the core engine — agent, function calling, structured output, fine-tuning |
| **ElevenLabs Challenge** | Voice dialogue as primary UX + character voice evolution by level |
| **Hugging Face Challenge** | Agent with planning, tool use, and multi-step reasoning |
| **Supercell Challenge** | Character growth system with XP, skill tree, and visual evolution |
| **Mistral "Best Vibe"** | Voice-first UX + gamification = peak vibe energy |

## Judging Criteria Alignment

1. **Technicality** — Multi-model system (Voxtral + Large 3 + FT Ministral 8B), three-tier execution fallback, knowledge distillation, self-improving feedback loop, W&B Models + Weave integration. Far beyond simple prompting.
2. **Creativity** — "Talk to build workflows" + character growth that mirrors real model improvement is a novel paradigm no one else is doing.
3. **Usefulness** — Directly addresses the gap between non-technical users and automation tools. Self-improving means it gets better for each user over time.
4. **Demo** — Highly visual: user speaks, nodes appear in real time, workflow executes, character levels up, W&B dashboard shows improvement metrics.
5. **Track alignment** — 3 Mistral models (Voxtral, Large 3, Ministral 8B) deeply embedded in every layer. W&B Models + Weave for the fine-tuning track.

## Demo Scenario

> **Presenter:** "Let me show you how a marketing manager with zero coding skills can automate their morning routine."
>
> **[Speaks to the app]:** "Every morning at 8 AM, search for the latest news about our competitors, summarize the key points, and send me a Slack message with the summary."
>
> **[AI responds via voice]:** "Got it. I'll set up a daily workflow. Which competitors should I track?"
>
> **[User]:** "OpenAI, Google DeepMind, and Anthropic."
>
> **[AI]:** "Perfect. Should I also post it to a Slack channel, or just DM you?"
>
> **[User]:** "Post it to #market-intel."
>
> **[Screen shows]:** Workflow nodes appearing one by one with animations — Search → Summarize → Slack Post. Each node lights up green as it executes in real time.
>
> **[AI via voice]:** "Done! Your workflow is live. Here's this morning's summary..."
>
> **[Screen]:** XP bar fills — **LEVEL UP!** Character evolves, new skill badge "Slack Master" unlocks.
>
> **[Character (voice, now more confident)]:** "Nice! I just learned a new skill. Want to try something even bigger?"

## Task Split

| Owner | Responsibility | Time |
|-------|---------------|------|
| **Klara (Backend + PM + Pitch)** | Mistral agent, execution engine, fine-tuning pipeline (SFT + self-improving loop), W&B integration, project management, pitch preparation | ~9h |
| **Koki (Frontend + Voice + Character)** | Landing page, workflow visualizer (React Flow), Voxtral STT + ElevenLabs TTS integration, character system (visuals, XP, voice evolution), demo polish | ~9h |
| **Both** | Demo scenario, video recording, submission | ~2h |

### GitHub Repository

http://github.com/klarakonkel/mistral-ai-hackathon
