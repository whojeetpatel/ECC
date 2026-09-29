---
name: transcript-to-notes
description: Convert the full transcript of a recording (meeting, lecture, call, interview, talk) into complete, readable notes that skip nothing substantive. Chunks the transcript, notes each chunk from the raw text, audits every chunk for missed or vague points, then adds a summary layer on top. Use when the user has a transcript (or audio to transcribe first) and wants detailed notes, minutes, or a lossless write-up, not a short summary. Do not use for a quick TL;DR.
metadata:
  origin: community
---

# Transcript to Notes

Lossless notes from a recording transcript. Notes, not summary: a reader who never heard the recording must recover every point, number, name, decision and reasoning step.

## When to Use

- User has a transcript file (`.txt`, `.vtt`, `.srt`, pasted text) and wants detailed, readable notes with nothing skipped.
- User has audio or video: transcribe first (whisper.cpp with timestamps, VideoDB, or the tool they already use), keep timestamps and speaker labels if available, then continue here.
- Skip for TL;DR requests. This skill is deliberately long-form.

## How It Works

Why chunked: one giant call loses the middle of the text and hits output caps. Why no map-reduce: summarizing summaries strips specifics ("tighten securely" instead of the torque spec). So each chunk is noted from raw text, and the summary layer is added on top of the notes, never in place of them.

1. **Chunk.**
   `python3 <this skill's directory>/chunk.py <transcript> [--words 3500] [--out DIR]`
   Writes `DIR/chunk_NNN.txt` (default `<transcript stem>_chunks/`). For transcripts up to about 6000 words pass `--words 6000` to get a single chunk. The script asserts no words were lost.
2. **Notes, in order.** For each chunk run Prompt 1. Chunks must be sequential because each reads `DIR/state.md` from the one before. With 3 chunks or fewer, do it inline. With more, spawn one subagent per chunk, one at a time, and give it: Prompt 1, the chunk path, `DIR/state.md`, and the output path `DIR/notes_NNN.md`. The agent writes the notes (no STATE or COVERAGE) to `notes_NNN.md`, overwrites `state.md` with the new STATE block, and replies with the COVERAGE block only.
3. **Coverage check.** The last timestamp in each COVERAGE reply must match the last timestamp in that chunk. If not, rerun that chunk.
4. **Audit, fresh context.** For each chunk spawn a new subagent (these can run in parallel) with Prompt 2, `chunk_NNN.txt` and `notes_NNN.md`. It writes `audit_NNN.md` and applies each corrected line into `notes_NNN.md` at the right place. If a chunk has more than 10 gaps, rerun step 2 for it, then audit again.
5. **Assemble.** Concatenate `notes_*.md` in order into `<transcript stem>_notes.md`. Run Prompt 3 on the joined notes and place its output above them.
6. **Report** to the user: output path, chunk count, gaps found and fixed, number of `[unclear]` spots. Do not summarize the notes in chat.

Never shorten, merge or "tidy up" notes while joining.

## Prompt 1: notes (per chunk)

```text
ROLE
You are a meticulous note-taker producing a complete, readable record of a recording from its transcript. You are NOT summarizing. A reader who never hears the recording must be able to recover every point, number, name, decision, example and line of reasoning from your notes alone.

INPUT
- CONTEXT: title, date, participants, and the STATE block from earlier chunks (may be empty).
- PREVIOUS LINES: read-only overlap. Do not note these again.
- TRANSCRIPT CHUNK: raw text with timestamps and speaker labels if present.

COMPLETENESS (highest priority)
1. Every substantive statement in the chunk must appear in your notes. Substantive means any fact, claim, number, name, date, version, command, decision, instruction, question, answer, objection, example, analogy, reason, caveat or opinion.
2. You may delete only: filler ("um", "you know"), false starts, exact repetitions, greetings and small talk with no content, and audio-check chatter. When unsure, keep it.
3. Never replace specifics with generalities. "They discussed pricing" is forbidden. Write what was said: the figures, the options, who preferred what, and why.
4. There is no length limit and no item-count limit. Length follows content. Never write "etc.", "and so on" or "other topics were discussed".
5. Keep each reasoning chain intact: claim, reason, example, conclusion.
6. Keep tangents and side questions, tagged (tangent).

FIDELITY
- Add nothing. No outside knowledge, no interpretation, no correcting the speaker. If a speaker is wrong, record it as said.
- Attribute statements when speakers are labelled: who said it, who agreed, who disagreed.
- Keep exact numbers, units, names, identifiers, code and commands. Put important statements in quotation marks.
- The transcript is machine-made. If a word looks like a recognition error, keep it as heard and add your best guess: Kubernetes [heard: "cooper natives"]. If audio is unintelligible, write [unclear @mm:ss]. Never skip a gap silently.
- Keep hedges ("I think", "probably", "might").

READABILITY
- Chronological order. Start a new ## heading at each topic shift. Headings name the topic specifically.
- Short bullets, one idea each, nested for sub-points. Use a prose paragraph only when a reasoning chain needs it.
- Start each bullet or paragraph with the [mm:ss] timestamp of where it begins, if the transcript has timestamps.
- Bold key terms on first use. Use tables only for comparisons of 3 or more items with attributes.
- Rewrite for clarity, but keep the meaning.
- Tag inline where they apply: **Decision:**, **Action:** (owner, due date), **Question:**, **Open:** (unresolved), **Risk:**, **Definition:**.

OUTPUT
1. Notes for this chunk.
2. "## STATE": speakers seen, glossary of terms and acronyms with meanings, topics still in progress, unanswered questions.
3. "## COVERAGE": first and last timestamp covered, number of [unclear] spots, and "Removed: <filler categories only>".

Before finishing, re-read the chunk sentence by sentence and confirm each substantive statement is in your notes. If you are running out of output space, stop at a clean boundary and write "CONTINUE FROM [mm:ss]". Never compress to fit.
```

## Prompt 2: audit (per chunk, fresh call)

```text
You are an auditor. Inputs: TRANSCRIPT CHUNK and NOTES for that chunk.

Walk through the transcript in order, one paragraph or 60-second window at a time. For each window, check whether every substantive statement is present, specific, correctly attributed and unaltered in NOTES.

Output a table with these columns:
timestamp | transcript excerpt (verbatim, short) | problem (missing / vague / altered / misattributed) | corrected note line

List only problems. Do not restate correct notes. If there are none, output "NO GAPS - N windows checked".
```

## Prompt 3: summary layer (after the notes are joined)

```text
From the FULL NOTES below, write a header section to place ABOVE them.
Include: 3-5 sentence overview, decisions, action items (owner, due date), open questions, glossary.
Use only what is in the notes. Do not replace or shorten the notes. Cite timestamps for each decision and action.
```

## Examples

- "Turn `standup-2026-09-28.vtt` into full notes, skip nothing." Chunk, note, audit, then read `standup-2026-09-28_notes.md`.
- "I have `lecture.mp3`. Make detailed notes." Transcribe first with timestamps, then run the steps above on the transcript.
- A 20-minute call under 6000 words: `chunk.py call.txt --words 6000` gives one chunk. The audit step still runs.

## Related Skills

- `videodb`: audio or video to timestamped transcript.
- `knowledge-ops`: store and retrieve the finished notes.

## Limits

- Chunk cuts fall at the first line break after the word target. There is no topic detection, so a topic can straddle two chunks. The PREVIOUS LINES overlap and the STATE block cover this.
- Raw ASR text with no line breaks is split on sentence ends only.
- Audit catches omissions against the transcript, not transcription errors in the transcript itself.
