# ADR 0003: Unified cognition engine (rules-first + optional LLM)

**Date:** 2026-06-12  
**Status:** Accepted  
**Commit:** `9721b1f`

## Context

The turn pipeline had separate `thought_engine.py` (~119 lines) and `reasoning_engine.py` (~29 lines) alongside the classifier and decision engine. Both modules produced overlapping outputs for turn understanding — intent interpretation, emotional context, follow-up suggestions — with duplicated paths and unclear ownership of when each ran.

The pipeline also needed behavior nudges and gated follow-up questions integrated into a single cognition result consumed by `decision_engine.py` and the LLM system prompt.

## Decision

Replace `thought_engine.py` and `reasoning_engine.py` with a single `cognition_engine.py`:

1. **Rules-first** — `generate_cognition_rules()` always runs (fast, deterministic, no API cost).
2. **Conditional LLM** — `should_use_llm_cognition()` triggers mini-LLM call (`gpt-4o-mini`, JSON schema) when heuristics detect ambiguity: low classification confidence, emotional mismatch, reflection triggers, long threads, etc.
3. **Fallback** — On LLM failure, use rules output.
4. **Unified output** — `CognitionResult` with `source: "rules" | "llm"` feeds `decision_engine.apply_cognition_to_behavior()` and `llm.build_system_message()`.

Gated follow-up questions remain policy-driven (code decides whether to ask; LLM only surfaces wording when needed).

## Alternatives considered

| Option | Why rejected |
|--------|--------------|
| Keep parallel thought/reasoning modules | Duplicated logic, unclear precedence, harder to test and extend |
| Always-on LLM cognition | Higher latency and cost on every turn; most turns don't need it |
| Remove cognition layer entirely | Loses behavior nudges, follow-up gating, and structured prompt injection |

## Consequences

**Positive:**

- Single module (~343 lines) with clear rules → optional LLM flow.
- `tests/test_cognition_engine.py` provides focused coverage of rules, LLM path, and fallback.
- `decision_engine.py` gains explicit cognition integration (`apply_cognition_to_behavior`).

**Negative:**

- Heuristic thresholds for LLM invocation need tuning as usage patterns change.
- Rules and LLM paths must stay semantically aligned so behavior doesn't diverge sharply by source.

## References

- Commit `9721b1f`
- `cognition_engine.py`, `decision_engine.py`, `message_processor.py`
- Replaced: `thought_engine.py`, `reasoning_engine.py`
