# Coach Words — AGENTS.md (Expanded Design v2.0)

> **Goal:** Turn raw coaching session recordings into reliable, reusable knowledge with a local‑first, pipeline‑driven app that is easy to use, easy to extend, and hard to break.

---

## 0) Design Goals & Non‑Goals

**Goals**

* **Clarity over cleverness:** simple mental model (recording → pipeline → artifacts → delivery).
* **Local‑first:** works offline on a laptop; cloud providers optional and swappable.
* **Low‑friction UX:** one‑click defaults, progressive disclosure for power features.
* **Deterministic & resumable:** idempotent runs, crash‑safe checkpoints, re‑entrancy.
* **Extensible:** new providers, stages, or export destinations without touching the core.
* **Observable:** consistent logs/metrics/traces; reproducible bug reports.
* **Trust & privacy:** explicit data handling, PII controls, auditable lineage.

**Non‑Goals**

* Not a general MLOps platform.
* Not a heavy multi‑tenant SaaS (though can be hosted later with minimal changes).

---

## 1) Core Concepts

* **Recording**: an input media file (audio/video) and immutable metadata.
* **Pipeline**: an ordered list of **stages** (agents) that transform inputs to artifacts.
* **Artifact**: any derived file (TXT, JSON, SRT, VTT, chapterized segments, datasets, etc.).
* **Manifest**: a JSON record (`.cw.manifest.json`) tracking inputs, options, versions, hashes, lineage, and produced artifacts.
* **Policy**: rules that choose providers (cost/latency/quality), redaction, retention, etc.
* **Profile**: named bundle of credentials + defaults (e.g., "Local‑Only", "Hybrid‑GCP").

---

## 2) Primary User Journeys

1. **Quick Start (1‑click)**

   * Drag/drop files → default policy → transcribe → TXT+SRT in same folder → done.
2. **Batch with Options**

   * Select files/folders → choose provider+options → estimate cost/time → run → review artifacts.
3. **Power‑User Automations**

   * Configure a **watch folder** or import rule set → auto‑run pipeline → deliver to local + Notion/GDrive → nightly roll‑up summaries.

---

## 3) System Architecture (Local‑First, Cloud‑Optional)

```
UI (Tauri/Web)  ──▶  Orchestrator  ──▶  Event Bus  ──▶  Agents (stages)  ──▶  Artifacts
                    │                   ▲     │
                    ▼                   │     ▼
               Policy Engine            │  Manifest Store
                    │                   │
                Credential Vault ◀──────┘
```

* **UI Shell**: Tauri/Electron front‑end; CLI mirrors core operations.
* **Orchestrator**: state machine driving pipelines, retries, and checkpoints.
* **Event Bus**: in‑process pub/sub for stage events; future‑proof to external bus.
* **Manifest Store**: per‑recording JSON manifest + optional project‑level index DB.
* **Credential Vault**: OS keychain/Keychain Access; supports multiple profiles.

---

## 4) Agent Catalog (Stages)

Each agent implements a standard interface: `init(config)`, `validate(input)`, `run(input) → output`, `capabilities()`, `estimate(input)`, and `explain(error)`.

### 4.1 Ingestion Agent

**Purpose:** Normalize inputs from drag‑drop, file picker, or watch folders.

* **Input:** file paths or directories.
* **Output:** `Recording` objects + `MediaMetadata` (duration, channels, sample rate, codec, checksum).
* **Responsibilities:** duplicate detection (hash), container validation, optional re‑mux to WAV/FLAC, loudness scan.
* **Errors:** unsupported codec, corrupt file, too‑long/too‑short.

### 4.2 Media Analysis Agent

**Purpose:** Pre‑compute helpful features.

* VAD (voice activity detection), language ID, mono/stereo handling, channel split, per‑minute RMS/peaks.

### 4.3 Transcription Provider Adapter

**Purpose:** Call a specific STT engine.

* **Providers:** WhisperX (local), OpenAI Transcribe, GCP STT (Chirp), + adapters.
* **Options:** language, temperature/beam size, word‑level timestamps, diarization hints.
* **Output:** base transcript with segment timing + confidences.
* **Notes:** implement exponential backoff, chunked uploads/streaming, and partial caching.

### 4.4 Diarization Agent (optional)

**Purpose:** Who spoke when.

* **Modes**: (a) provider‑native, (b) external pipeline (e.g., pyannote), (c) acoustic channel split.
* **Output:** speaker‑attributed segments with label map `{S1: "Coach", S2: "Candidate"}` where available.

### 4.5 Alignment Agent (optional)

**Purpose:** Forced alignment for accurate word timings, improving SRT/VTT and search.

### 4.6 Redaction/Anonymization Agent (optional)

**Purpose:** PII detection and replacement.

* **Controls:** irreversible masking vs. reversible pseudonyms via salted map; scope (names/emails/phones/addresses/companies); redact in audio (beeps) optionally.

### 4.7 Post‑Processing Agent

**Purpose:** Clean text (punctuation, capitalization, filler toggles, number normalization), add paragraphing and chapters.

### 4.8 Quality & Review Agent

**Purpose:** Flag low‑confidence spans, long pauses, crosstalk; generate QC checklist; supports in‑app editor with side‑by‑side audio scrubbing.

### 4.9 Summarization & Derivatives Agent

**Purpose:** Produce summaries, action items, topics, key quotes, meeting minutes, and Q&A pairs.

* **Modes:** conservative extractive vs. abstractive; length presets.

### 4.10 Fine‑Tuning Dataset Agent

**Purpose:** Make instruction datasets.

* **Formats:** JSONL for major providers (OpenAI, Claude, Gemini), and a generic schema.
* **Validations:** dedupe, length limits, role balance, leakage checks; split train/val/test.

### 4.11 Export & Delivery Agent

**Purpose:** Write artifacts and send to destinations.

* **Local FS** (default): next to the source recording.
* **Connectors (optional):** Notion page, Google Drive, S3, Git repo commit, email bundle.
* **Retryable writes** with conflict strategy (append version or overwrite by policy).

### 4.12 Orchestrator (Workflow Agent)

**Purpose:** Drive the state machine; ensure checkpointing; enforce policy; schedule retries; expose events.

### 4.13 Credential Management Agent

**Purpose:** Securely store/test provider creds; profile switching; redaction of logs.

### 4.14 Costing & Policy Agent

**Purpose:** Inline estimates for cost/latency/quality; provider selection based on policy (e.g., `preferred = local unless duration>2h then GCP`).

### 4.15 Scheduler & Resource Agent

**Purpose:** Concurrency limits, GPU usage, CPU affinity; fairness across batches; pause/resume.

### 4.16 Audit & Governance Agent

**Purpose:** Data retention, artifact TTL, encryption keys, access logs, provenance graph.

### 4.17 Update & Plugin Manager

**Purpose:** Install/disable provider adapters or stage plugins with semantic‑versioned contracts.

---

## 5) Interface Contracts (TypeScript‑style)

```ts
// Recording and metadata
type RecordingId = string;
interface Recording {
  id: RecordingId;
  path: string;            // absolute
  basename: string;        // without extension
  ext: string;             // .wav/.mp3/.m4a/.mp4
  hash: string;            // content SHA256
  createdAt: string;       // ISO8601
  media: MediaMetadata;
}

interface MediaMetadata {
  durationSec: number;
  sampleRate: number;
  channels: number;
  codec: string;
  languageHint?: string;
}

// Transcript
interface Transcript {
  recordingId: RecordingId;
  segments: Segment[];
  speakers?: SpeakerMap;    // { S1: 'Coach', S2: 'Candidate' }
  stats?: TranscriptStats;
  version: string;          // provider+app version
}

interface Segment {
  startSec: number;
  endSec: number;
  speaker?: string;         // S1/S2
  text: string;
  words?: Word[];           // optional word timings
  confidence?: number;      // 0..1
}

interface Word { startSec: number; endSec: number; text: string; confidence?: number }
interface SpeakerMap { [code: string]: string }
interface TranscriptStats { wpm?: number; werrs?: number; fillerRate?: number }

// Derivative artifacts
interface Artifact {
  kind: 'txt'|'json'|'srt'|'vtt'|'summary'|'dataset'|'chapters'|'manifest';
  path: string;             // absolute
  bytes: number;
  sha256: string;
  createdAt: string;
  generatedBy: string;      // stage id
  source: RecordingId;
  dependsOn?: string[];     // other artifacts ids
}

// Stage interface
interface Stage<Input, Output> {
  id: string; version: string;
  capabilities(): string[];
  estimate(input: Input): Estimate;        // time/cost/size
  validate(input: Input): ValidationError[];
  run(input: Input, ctx: StageContext): Promise<Output>;
}

interface StageContext {
  profile: string;  // which credential/profile is active
  policy: Policy;   // redaction, retention, provider selection
  emit: (event: PipelineEvent) => void;
  manifest: ManifestAPI;
  cache: CacheAPI;
  logger: Logger;
}

interface Estimate { seconds?: number; costUSD?: number; peakRAMMB?: number; }
```

---

## 6) Event Model & State Machine

**Events** (all carry `recordingId`, `stageId`, `ts`):

* `TASK_CREATED`, `INGESTED`, `ANALYZED`, `TRANSCRIBE_STARTED`, `TRANSCRIBE_PARTIAL`, `TRANSCRIBE_DONE`, `DIARIZATION_DONE`, `ALIGNMENT_DONE`, `POSTPROCESS_DONE`, `SUMMARY_DONE`, `DATASET_DONE`, `EXPORTED`, `FAILED`, `RETRIED`, `CANCELLED`.

**States**: `NEW → READY → RUNNING → PAUSED → DONE` with sub‑states per stage. Checkpoints at stage boundaries; resume from last successful stage.

---

## 7) Configuration (YAML)

```yaml
# app.yaml
profiles:
  local_only:
    policy:
      provider: whisperx
      redaction: none
      retention_days: 0
  hybrid_gcp:
    credentials:
      gcp_keychain_ref: "gcp-stt-default"
    policy:
      provider: auto          # let policy choose
      provider_rules:
        - if: durationSec > 7200
          use: gcp_chirp
        - if: language in ["ar", "hi"]
          prefer: gcp_chirp
pipelines:
  default: [ingest, analyze, transcribe, postprocess, export]
  rich:    [ingest, analyze, transcribe, diarize, align, redact, postprocess, qa, summarize, dataset, export]
ui:
  show_advanced_by_default: false
```

---

## 8) Storage Conventions & Manifests

* **Artifact naming:** `{basename}.{stage}.{suffix}` (e.g., `call123.transcribe.txt`, `call123.align.json`).
* **Manifest file:** `{basename}.cw.manifest.json` lives next to the source; includes:

  * input file facts (hash, codec, duration), options used, stage versions, outputs (paths+hashes), policy snapshot, profile, and event log.
* **Checksums:** all artifacts hashed; dedupe across runs.
* **Project index:** lightweight SQLite/DuckDB cache for global search and dashboards.

---

## 9) UX/UI Blueprint

* **Start screen:** big drop zone + "Choose Folder"; shows previous projects with status chips.
* **Batch table:** files, duration, detected language, profile, selected pipeline, est. cost/time.
* **Run panel:** per‑file progress bars; pause/cancel; error banner with `Explain()` and one‑click remediation.
* **Review & Edit:** split view (waveform + transcript); keyboard shortcuts; confidence heatmap; quick speaker relabel; export panel (checkboxes for artifacts/destinations).
* **Defaults:** sane presets; advanced options hidden behind “More Options”.
* **Help:** embedded provider setup wizards, test buttons, and cost calculators.
* **Accessibility:** full keyboard nav, screen‑reader labels, focus states.

---

## 10) Extensibility Playbook

* **New Provider Adapter:** implement `Stage<Input=Recording, Output=Transcript>`; register via plugin manifest; declare `capabilities()`; supply `estimate()`.
* **New Stage:** define inputs/outputs via JSON Schema; add to registry; emit events; add UI schema for auto‑generated forms.
* **New Destination:** implement `Writer` interface with `put(path, bytes, metadata)` and retry policy.
* **Versioning:** semantic version for stages; manifest stores exact versions to ensure reproducibility.

---

## 11) Dependency Strategy (Reduce Fragmentation)

* **Runtime:** Python core (agents/orchestrator) + Tauri front‑end (small footprint). CLI mirrors API.
* **Isolation:** each provider in its own optional extras (`pip install coachwords[gcp]`).
* **Env Management:** uv/pip‑tools lock files; prebuilt wheels for Apple Silicon; optional Docker for full isolation.
* **Heavy deps optional:** diarization/alignment only if enabled.
* **No global state:** DI container passes dependencies explicitly.

---

## 12) Testing & Quality

* **Unit tests:** stage contracts with golden files.
* **Integration tests:** end‑to‑end small media; verify manifests and artifacts.
* **Property tests:** idempotency, resume correctness, hash/dedupe.
* **Performance tests:** long files, low‑RAM scenarios.
* **Smoke tests:** provider creds and rate limits.

---

## 13) Observability & Supportability

* **Structured logs:** JSON logs per recording; redaction aware.
* **Metrics:** duration by stage, WER proxy, cost per hour.
* **Traces:** stage spans with I/O sizes; surfaced in a dev console.
* **Debug pack:** one‑click bundle (manifest, logs, config, small excerpts).

---

## 14) Privacy, Security, Compliance

* **PII modes:** none/mask/pseudonymize; reversible map stored separately and optionally encrypted.
* **Encryption:** at rest (local OS facilities) and in transit (TLS for connectors).
* **Data retention:** configurable TTL per artifact kind; auto‑purge jobs.
* **Audit:** manifest lineage; who/when if multi‑user.

---

## 15) Performance & Scale Targets (Initial)

* 2× real‑time local WhisperX on M‑series with GPU enabled; fall back gracefully.
* Parallelism: default 2 concurrent transcriptions; backoff based on RAM/thermals.
* Memory guardrails: cap peak RAM per stage; spill to disk when needed.

---

## 16) Roadmap (Milestones)

* **M1 – Core (Weeks 1‑3)**: ingest/analyze/transcribe/postprocess/export; manifests; CLI; default UI.
* **M2 – Rich (Weeks 4‑6)**: diarization, alignment, redaction, summaries; in‑app editor; cost estimator.
* **M3 – Pro (Weeks 7‑9)**: datasets, destinations (Notion/GDrive), watch folders, plugin manager, audit/retention.

---

## 17) Capability Matrix (Starter)

| Capability          | WhisperX (local)  | OpenAI Transcribe | GCP STT (Chirp) |
| ------------------- | ----------------- | ----------------- | --------------- |
| Offline             | ✅                 | ❌                 | ❌               |
| Word timestamps     | ✅                 | ✅                 | ✅               |
| Diarization         | ☑️ (via pyannote) | ✅ (basic)         | ✅ (enhanced)    |
| Multi‑language      | ✅                 | ✅                 | ✅               |
| Cost predictability | ✅ (fixed)         | ⚠️ (usage)        | ⚠️ (usage)      |
| Speed               | ⚠️                | ✅                 | ✅               |

*(☑️ = optional extra stage)*

---

## 18) Error Taxonomy & Remediation

* **E‑INGEST‑UNSUPPORTED‑CODEC**: Suggest re‑mux; one‑click convert.
* **E‑PROVIDER‑AUTH**: Show provider wizard; test credentials.
* **E‑RATE‑LIMIT**: Backoff + queue; advise switching provider.
* **E‑REDaction‑CONFLICT**: Explain irreversible vs reversible choices; confirm.
* **E‑EXPORT‑CONFLICT**: Offer versioned filename or overwrite per policy.

---

## 19) Glossary

* **WER**: Word Error Rate; proxy for quality.
* **Diarization**: assigning text fragments to speakers.
* **Forced alignment**: aligning transcript to audio at the word/phoneme level.
* **Manifest**: the single source of truth for a recording’s processing lifecycle.

---

## 20) Appendix: Minimal Contracts (JSON Schema excerpts)

```json
{
  "$id": "https://coachwords.io/schema/manifest",
  "type": "object",
  "required": ["recording", "pipeline", "stages", "artifacts", "hash"],
  "properties": {
    "recording": {"$ref": "#/definitions/recording"},
    "pipeline": {"type": "array", "items": {"type": "string"}},
    "stages": {"type": "object"},
    "artifacts": {"type": "array", "items": {"$ref": "#/definitions/artifact"}},
    "events": {"type": "array"},
    "policy": {"type": "object"},
    "profile": {"type": "string"},
    "hash": {"type": "string"}
  },
  "definitions": {
    "recording": {"type": "object", "required": ["id", "path", "hash"]},
    "artifact": {"type": "object", "required": ["kind", "path", "sha256"]}
  }
}
```

---

### TL;DR

* Keep the user journey **one‑click** by default.
* Keep the core **small and local**; everything else is a plugin.
* Make every operation **reproducible** via the manifest and explicit versions.
* Prefer **policies** over hard‑coding; prefer **events** over hidden state.
