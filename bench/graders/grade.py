#!/usr/bin/env python3
"""Grade one bench2 phase and write grade.json next to the run artifacts."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]
TESTS = HARNESS / "tests"


def run_python_tests(worktree: Path, test_file: Path, out: Path) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(worktree) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, str(test_file)],
            cwd=str(worktree),
            env=env,
            capture_output=True,
            text=True,
            timeout=900,
        )
        log = proc.stdout + "\n" + proc.stderr
        (out / "grade.log").write_text(log, encoding="utf-8")
        match = re.search(r"Ran (\d+) tests?", log)
        total = int(match.group(1)) if match else 0
        if proc.returncode == 0:
            passed, failed = total, 0
        else:
            failures = int((re.search(r"failures=(\d+)", log) or [0, 0])[1] or 0)
            errors = int((re.search(r"errors=(\d+)", log) or [0, 0])[1] or 0)
            failed = failures + errors
            passed = max(0, total - failed)
        return {
            "kind": "tests",
            "total": total,
            "passed": passed,
            "failed": failed,
            "exit_code": proc.returncode,
            "score": round(passed / total, 4) if total else 0.0,
        }
    except subprocess.TimeoutExpired:
        (out / "grade.log").write_text("timeout\n", encoding="utf-8")
        return {"kind": "tests", "total": 0, "passed": 0, "failed": 0, "exit_code": 124, "score": 0.0}


def count_regression_tests(worktree: Path) -> int:
    """Count test functions added in ledger/tests relative to HEAD."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(worktree), "diff", "--", "ledger/tests"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return len(re.findall(r"^\+\s*def test_", proc.stdout, re.M))
    except Exception:
        return 0


def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 bench2"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, resp.read(200_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except Exception:
        try:
            proc = subprocess.run(
                ["curl", "-L", "-sS", "-A", "Mozilla/5.0 bench2", "--max-time", "25",
                 "-w", "\n%{http_code}", url],
                capture_output=True,
                text=True,
                timeout=35,
            )
            body, _, code = proc.stdout.rpartition("\n")
            return int(code or 0), body[:200_000]
        except Exception:
            return 0, ""


def grade_research(out: Path) -> dict:
    answer = (out / "answer.md").read_text(encoding="utf-8", errors="replace") if (out / "answer.md").exists() else ""
    words = len(re.findall(r"\S+", re.sub(r"https?://\S+", " ", answer)))
    urls = sorted(set(re.findall(r"https?://[^\s)\]>,;]+", answer)))
    reachable = []
    for url in urls[:10]:
        status, body = fetch(url)
        reachable.append({"url": url, "status": status, "has_wal": "wal" in body.lower() or "sqlite" in body.lower()})
    low = answer.lower()
    checks = {
        "word_limit": words <= 420,
        "at_least_3_sources": len(urls) >= 3,
        "all_fetched_sources_reachable": bool(reachable) and all(item["status"] == 200 for item in reachable),
        "sources_mention_sqlite_or_wal": bool(reachable) and all(item["has_wal"] for item in reachable),
        "explains_wal": "wal" in low,
        "explains_checkpoint": "checkpoint" in low,
        "mentions_wal_files": "-wal" in low or "wal file" in low or "archivo wal" in low,
        "mentions_shm": "-shm" in low or "shm" in low,
        "mentions_network_fs": "nfs" in low or "red" in low or "network" in low,
        "mentions_busy_timeout": "busy_timeout" in low or "busy timeout" in low,
        "mentions_autocheckpoint": "autocheckpoint" in low or "auto-checkpoint" in low or "auto checkpoint" in low,
        "mentions_single_writer": "un solo escritor" in low or "single writer" in low or "un escritor" in low,
    }
    score = sum(1 for value in checks.values() if value) / len(checks)
    return {
        "kind": "research",
        "words": words,
        "urls": urls,
        "sources": reachable,
        "checks": checks,
        "score": round(score, 4),
    }


def grade_skills(out: Path, vault: Path, worktree: Path) -> dict:
    answer = (out / "answer.md").read_text(encoding="utf-8", errors="replace") if (out / "answer.md").exists() else ""
    low = answer.lower()
    note_path = vault / "Topics" / "orion-bench.md"
    note = note_path.read_text(encoding="utf-8", errors="replace") if note_path.exists() else ""
    bullets = len(re.findall(r"^\s*[-*]\s+\S", note, re.M))
    facts = {
        "fact_retention": "30" in note and ("día" in note.lower() or "dia" in note.lower()),
        "fact_p95": "250" in note,
        "fact_wal": "wal" in note.lower(),
        "fact_spool": "spool" in note.lower(),
        "fact_clock": "skew" in note.lower() or "reloj" in note.lower(),
        "fact_zstd": "zstd" in note.lower() or "compres" in note.lower(),
    }
    note_checks = {
        "note_exists": note_path.exists(),
        "six_bullets": bullets >= 6,
        "has_sources_section": "## fuentes" in note.lower(),
        "wikilinks": len(re.findall(r"\[\[[^\]]+\]\]", note)) >= 3,
        "facts_5_of_6": sum(1 for value in facts.values() if value) >= 5,
        "facts": facts,
    }

    dotpm_checks = {
        "dotpm_responds": False,
        "task_exists": False,
        "task_fields": False,
    }
    try:
        proc = subprocess.run(
            ["dotpm", "tasks", "bench20000000001", "--vault", str(vault)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        data = json.loads(proc.stdout)
        dotpm_checks["dotpm_responds"] = isinstance(data, list)
        for task in data:
            title = (task.get("title") or "").lower()
            if "revisar orion" in title:
                dotpm_checks["task_exists"] = True
                dotpm_checks["task_fields"] = (
                    task.get("description") == "Comparar proveedores y harnesses."
                    and task.get("status") == "todo"
                    and task.get("priority") == "medium"
                    and task.get("tags") == ["bench2"]
                )
                break
    except Exception:
        pass

    pony_checks = {
        "mentions_ledger_file": "ledger/ledger.py" in low,
        "line_references": len(re.findall(r"ledger/ledger\.py:\d+", low)) >= 1,
        "mutable_default": "mutable" in low or "default" in low or "acumul" in low or "arrastr" in low,
        "float_parse": "float" in low or "decimal" in low or "redondeo" in low or "centavo" in low,
        "percent_range": "percent" in low or "porcentaje" in low or "rango" in low,
        "merge_touching": "tocan" in low or "touch" in low or "merge_intervals" in low,
    }
    pony_findings = sum(1 for key in ("mutable_default", "float_parse", "percent_range", "merge_touching") if pony_checks[key])

    security_checks = {
        "sql_injection": "sql" in low and ("inyecc" in low or "injection" in low),
        "path_traversal": "traversal" in low or "../" in low or "path" in low and "files.py" in low,
        "hardcoded_secret": "hardcoded" in low or "secreto" in low or "secret" in low,
        "plaintext_or_timing": "plaintext" in low or "texto plano" in low or "timing" in low or "hash" in low,
        "missing_authorization": "authorization" in low or "autoriz" in low or "delete_user" in low,
        "verbose_error": "traceback" in low or "str(exc)" in low or "error crudo" in low or "stack" in low,
        "service_line_refs": len(re.findall(r"service/[a-z_]+\.py:\d+", low)) >= 3,
    }
    security_count = sum(1 for key in ("sql_injection", "path_traversal", "hardcoded_secret", "plaintext_or_timing", "missing_authorization", "verbose_error") if security_checks[key])

    note_score = sum(1 for value in note_checks.values() if value) / len(note_checks)
    dotpm_score = sum(1 for value in dotpm_checks.values() if value) / len(dotpm_checks)
    pony_score = (sum(1 for value in pony_checks.values() if value) / len(pony_checks)) * min(1.0, pony_findings / 2)
    security_score = (security_count / 6) * (1.0 if security_checks["service_line_refs"] else 0.5)
    score = (note_score + dotpm_score + pony_score + security_score) / 4
    return {
        "kind": "skills",
        "note": note_checks,
        "note_bullets": bullets,
        "dotpm": dotpm_checks,
        "ponytail": pony_checks,
        "ponytail_findings": pony_findings,
        "security": security_checks,
        "security_findings": security_count,
        "subscores": {
            "note": round(note_score, 4),
            "dotpm": round(dotpm_score, 4),
            "ponytail": round(pony_score, 4),
            "security": round(security_score, 4),
        },
        "score": round(score, 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True)
    parser.add_argument("--cell", required=True)
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--vault", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    worktree = Path(args.worktree)
    vault = Path(args.vault)

    if args.phase == "fase1-webapp":
        result = run_python_tests(worktree, TESTS / "webapp_acceptance.py", out)
    elif args.phase == "fase2-render3d":
        result = run_python_tests(worktree, TESTS / "render3d_acceptance.py", out)
    elif args.phase == "fase3-ledger":
        result = run_python_tests(worktree, TESTS / "ledger_acceptance.py", out)
        result["score_tests"] = result["score"]
        result["regression_tests"] = count_regression_tests(worktree)
        result["regression_ok"] = result["regression_tests"] >= 4
        result["score"] = round(result["score"] * 0.8 + (0.2 if result["regression_ok"] else 0.0), 4)
    elif args.phase == "fase4-research":
        result = grade_research(out)
    elif args.phase == "fase5-skills":
        result = grade_skills(out, vault, worktree)
    else:
        raise SystemExit(f"unknown phase {args.phase}")

    result["phase"] = args.phase
    result["cell"] = args.cell
    (out / "grade.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cell": args.cell, "phase": args.phase, "score": result.get("score")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
