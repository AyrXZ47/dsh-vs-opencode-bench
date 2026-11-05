#!/usr/bin/env python3
"""Collect answer, token usage, tool counts and cost from a benchmark run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PRICING = {
    # USD per 1M tokens. direct = pi-ai DeepSeek catalog for deepseek-flash.
    "direct": {"input": 0.30, "output": 1.20, "cache_read": 0.006, "cache_write": 0.0},
    # USD per 1M tokens for opencode-go/deepseek-v4.1-flash.
    "oc": {"input": 0.15, "output": 0.60, "cache_read": 0.003, "cache_write": 0.0},
}


def read_jsonl(path: Path) -> list[dict]:
    events: list[dict] = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            events.append(obj)
    return events


def add_usage(target: dict, usage: dict | None) -> None:
    if not isinstance(usage, dict):
        return
    mapping = {
        "input": ("inputTokens", "input"),
        "output": ("outputTokens", "output"),
        "cache_read": ("cacheReadTokens", "cache_read", "cacheRead"),
        "cache_write": ("cacheWriteTokens", "cache_write", "cacheWrite"),
        "total": ("totalTokens", "total"),
    }
    for key, names in mapping.items():
        for name in names:
            if name in usage and isinstance(usage[name], (int, float)):
                target[key] = target.get(key, 0) + usage[name]
                break


def dsh_summary(events: list[dict]) -> dict:
    usage = {k: 0 for k in ("input", "output", "cache_read", "cache_write", "total")}
    answer = ""
    texts: list[str] = []
    thinking: list[str] = []
    session = ""
    steps = turns = tools = 0
    turn_reason = None
    for event in events:
        etype = event.get("type")
        if etype == "session":
            session = event.get("sessionId", session)
        elif etype == "status" and event.get("phase") == "step_end":
            steps += 1
            add_usage(usage, event.get("usage"))
        elif etype == "status" and event.get("phase") == "turn_end":
            turns += 1
            turn_reason = event.get("reason", turn_reason)
        elif etype in ("tool_call", "tool_result"):
            if etype == "tool_call":
                tools += 1
        elif etype == "text":
            text = event.get("text")
            if isinstance(text, str) and text:
                texts.append(text)
        elif etype == "thinking":
            text = event.get("text")
            if isinstance(text, str) and text:
                thinking.append(text)
        elif etype == "final":
            text = event.get("text")
            if isinstance(text, str):
                answer = text
    if not answer:
        answer = "\n".join(texts)
    return {
        "session": session,
        "answer": answer,
        "all_text": "\n\n".join(texts),
        "thinking": "\n\n".join(thinking),
        "usage": usage,
        "steps": steps,
        "turns": turns,
        "tools": tools,
        "turn_reason": turn_reason,
        "events": len(events),
    }


def oc_summary(events: list[dict]) -> dict:
    usage = {k: 0 for k in ("input", "output", "reasoning", "cache_read", "cache_write")}
    cost_actual = 0.0
    texts: list[str] = []
    last_step_texts: list[str] = []
    thinking: list[str] = []
    session = ""
    steps = tools = 0
    start_ms = None
    end_ms = None
    last_step_index = -1
    for index, event in enumerate(events):
        etype = event.get("type")
        ts = event.get("timestamp")
        if isinstance(ts, (int, float)):
            start_ms = ts if start_ms is None else min(start_ms, ts)
            end_ms = ts if end_ms is None else max(end_ms, ts)
        if event.get("sessionID"):
            session = event.get("sessionID")
        part = event.get("part") if isinstance(event.get("part"), dict) else {}
        if etype == "step_start":
            last_step_index = index
            last_step_texts = []
        elif etype == "text":
            text = part.get("text")
            if isinstance(text, str) and text:
                texts.append(text)
                if index > last_step_index:
                    last_step_texts.append(text)
        elif etype == "reasoning":
            text = part.get("text")
            if isinstance(text, str) and text:
                thinking.append(text)
        elif etype == "step_finish":
            steps += 1
            tokens = part.get("tokens") if isinstance(part.get("tokens"), dict) else {}
            for key, names in {
                "input": ("input",),
                "output": ("output",),
                "reasoning": ("reasoning",),
            }.items():
                for name in names:
                    value = tokens.get(name)
                    if isinstance(value, (int, float)):
                        usage[key] += value
                        break
            cache = tokens.get("cache") if isinstance(tokens.get("cache"), dict) else {}
            if isinstance(cache.get("read"), (int, float)):
                usage["cache_read"] += cache["read"]
            if isinstance(cache.get("write"), (int, float)):
                usage["cache_write"] += cache["write"]
            cost = part.get("cost")
            if isinstance(cost, (int, float)):
                cost_actual += cost
        if isinstance(etype, str) and "tool" in etype:
            tools += 1
    answer = "\n".join(last_step_texts).strip()
    if not answer:
        answer = texts[-1] if texts else ""
    usage["total"] = usage["input"] + usage["output"] + usage["reasoning"]
    wall_ms = None
    if start_ms is not None and end_ms is not None:
        wall_ms = int(end_ms - start_ms)
    return {
        "session": session,
        "answer": answer,
        "all_text": "\n\n".join(texts),
        "thinking": "\n\n".join(thinking),
        "usage": usage,
        "cost_actual": cost_actual,
        "steps": steps,
        "tools": tools,
        "event_wall_ms": wall_ms,
        "events": len(events),
    }


def nominal_cost(usage: dict, pricing: str) -> float:
    p = PRICING[pricing]
    input_tokens = usage.get("input", 0)
    output_tokens = usage.get("output", 0) + usage.get("reasoning", 0)
    cache_read = usage.get("cache_read", 0)
    cache_write = usage.get("cache_write", 0)
    return (
        input_tokens / 1_000_000 * p["input"]
        + output_tokens / 1_000_000 * p["output"]
        + cache_read / 1_000_000 * p["cache_read"]
        + cache_write / 1_000_000 * p["cache_write"]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["dsh", "oc"], required=True)
    parser.add_argument("--events", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--cell", required=True)
    parser.add_argument("--pricing", choices=["direct", "oc"], required=True)
    parser.add_argument("--wall-ms", type=int, required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--started", default="")
    parser.add_argument("--finished", default="")
    parser.add_argument("--provider", default="")
    parser.add_argument("--model", default="")
    args = parser.parse_args()

    events = read_jsonl(Path(args.events))
    data = dsh_summary(events) if args.kind == "dsh" else oc_summary(events)
    usage = data.get("usage", {})
    summary = {
        "cell": args.cell,
        "kind": args.kind,
        "provider": args.provider,
        "model": args.model,
        "pricing": args.pricing,
        "exit_code": args.exit_code,
        "started": args.started,
        "finished": args.finished,
        "wall_ms": args.wall_ms,
        "event_wall_ms": data.get("event_wall_ms"),
        "session": data.get("session", ""),
        "answer": data.get("answer", ""),
        "usage": usage,
        "cost_actual_usd": data.get("cost_actual"),
        "cost_nominal_usd": nominal_cost(usage, args.pricing),
        "steps": data.get("steps", 0),
        "turns": data.get("turns"),
        "tools": data.get("tools", 0),
        "turn_reason": data.get("turn_reason"),
        "events": data.get("events", 0),
    }
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out / "answer.md").write_text(summary["answer"].rstrip() + "\n", encoding="utf-8")
    (out / "all_text.md").write_text(data.get("all_text", "").rstrip() + "\n", encoding="utf-8")
    (out / "thinking.md").write_text(data.get("thinking", "").rstrip() + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "cell": args.cell,
                "exit": args.exit_code,
                "wall_s": round(args.wall_ms / 1000, 1),
                "tokens": usage,
                "cost_nominal_usd": round(summary["cost_nominal_usd"], 6),
                "cost_actual_usd": summary["cost_actual_usd"],
                "answer_first_line": summary["answer"].splitlines()[0] if summary["answer"] else "",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
