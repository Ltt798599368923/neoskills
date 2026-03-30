"""neoskills schedule - memory-enabled personal schedule agent (CLI)."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import click
from rich.console import Console

# Claude Agent SDK is required for this command.

console = Console()


def _call_claude_agent_sdk(prompt: str) -> str:
    """Strict Claude Agent SDK call path (no API-key fallback)."""
    try:
        import asyncio
        import claude_agent_sdk  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "claude-agent-sdk is required. Install extras: `uv sync --extra sdk`"
        ) from e

    async def _run() -> str:
        parts: list[str] = []
        async for msg in claude_agent_sdk.query(prompt=prompt):
            # Prefer final result text when available
            result = getattr(msg, "result", None)
            if isinstance(result, str) and result.strip():
                parts.append(result.strip())
                continue

            # Fallback: capture assistant text blocks
            content = getattr(msg, "content", None)
            if isinstance(content, list):
                for block in content:
                    text = getattr(block, "text", None)
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            elif isinstance(content, str) and content.strip():
                parts.append(content.strip())

        return "\n\n".join(parts).strip()

    return asyncio.run(_run())


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _append_block(path: Path, heading: str, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n## {heading}\n{content.strip()}\n")


def _extract_sections(raw: str) -> dict[str, str]:
    sections = {"USER_REPORT": "", "DAILY_NOTE": "", "LTM_UPDATES": ""}
    current = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf, current
        if current:
            sections[current] = "\n".join(buf).strip()
        buf = []

    for line in raw.splitlines():
        key = line.strip().rstrip(":")
        if key in sections:
            flush()
            current = key
            continue
        if current:
            buf.append(line)
    flush()
    return sections


def _load_mailbox_snippets(schedule_dir: Path) -> str:
    cfg_path = schedule_dir / "mailboxes.json"
    if not cfg_path.exists():
        return "mailboxes.json not found; mailbox scan skipped."

    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception as e:
        return f"Failed to parse mailboxes.json: {e}"

    outputs: list[str] = []
    for mailbox in cfg.get("mailboxes", []):
        if not mailbox.get("enabled", True):
            continue
        name = mailbox.get("name", "unnamed")
        fetch_cmd = mailbox.get("fetch_command")
        if not fetch_cmd:
            outputs.append(f"[{name}] setup-needed: add fetch_command in mailboxes.json")
            continue
        try:
            proc = subprocess.run(
                fetch_cmd,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            if proc.returncode != 0:
                outputs.append(f"[{name}] command failed ({proc.returncode}): {err[:600]}")
            else:
                outputs.append(f"[{name}]\n{out[:2000]}")
        except Exception as e:
            outputs.append(f"[{name}] command error: {e}")

    return "\n\n".join(outputs) if outputs else "No enabled mailboxes."


@click.group("schedule")
def schedule() -> None:
    """Memory-enabled personal schedule agent commands."""


@schedule.command("daily")
@click.option("--workspace", type=click.Path(path_type=Path), default=Path("/Users/rich/.openclaw/workspace"))
@click.option("--date", "date_str", default=None, help="Date in YYYY-MM-DD (default: today local)")
@click.option("--inbox-file", multiple=True, type=click.Path(path_type=Path), help="Optional inbox summary files")
@click.option("--write", "write_back", is_flag=True, help="Write memory updates to files")
def daily(workspace: Path, date_str: str | None, inbox_file: tuple[Path, ...], write_back: bool) -> None:
    """Generate a daily plan using memory + mailbox context (Claude Agent SDK only)."""
    schedule_dir = workspace / "memory" / "schedule-memory"
    schedule_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    target = datetime.strptime(date_str, "%Y-%m-%d") if date_str else now
    day = target.strftime("%Y-%m-%d")
    yday = (target - timedelta(days=1)).strftime("%Y-%m-%d")

    today_mem = workspace / "memory" / f"{day}.md"
    yesterday_mem = workspace / "memory" / f"{yday}.md"
    ltm = schedule_dir / "long-term-routine.md"

    inbox_chunks = []
    mailbox_scan = _load_mailbox_snippets(schedule_dir)
    inbox_chunks.append("MAILBOX_SCAN:\n" + mailbox_scan)
    for p in inbox_file:
        if p.exists():
            inbox_chunks.append(f"INBOX_FILE[{p}]:\n" + _read_text(p)[:3000])

    # Strict mode: Claude Agent SDK only

    prompt = f"""
You are Richard's schedule-memory agent.
Focus ONLY on schedules, routines, commitments, and planning.

Context:
- Date: {day}
- Today's memory:\n{_read_text(today_mem)[:4000]}
- Yesterday's memory:\n{_read_text(yesterday_mem)[:2500]}
- Long-term routine memory:\n{_read_text(ltm)[:4000]}
- Inbox context:\n{'\n\n'.join(inbox_chunks)[:5000]}

Tasks:
1) Triage inbox signals into urgent/actionable/waiting.
2) Produce a realistic time-blocked day plan.
3) Identify top 3 priorities.
4) Identify risks/conflicts.
5) Suggest durable long-term routine updates (stable patterns only).

Return EXACTLY in this format:
USER_REPORT:
<markdown for Richard>

DAILY_NOTE:
<concise log entry to append to memory/{day}.md>

LTM_UPDATES:
<bullet points to append to long-term-routine.md>
""".strip()

    try:
        raw = _call_claude_agent_sdk(prompt)
    except Exception as e:
        console.print(f"[red]Claude Agent SDK call failed:[/red] {e}")
        raise SystemExit(1)
    sections = _extract_sections(raw)

    report = sections["USER_REPORT"] or raw
    console.print(report)

    if write_back:
        if sections["DAILY_NOTE"]:
            _append_block(today_mem, f"Schedule agent run ({day})", sections["DAILY_NOTE"])
        if sections["LTM_UPDATES"]:
            _append_block(ltm, f"Update {day}", sections["LTM_UPDATES"])
        console.print("\n[green]Memory updates written.[/green]")
    else:
        console.print("\n[dim]Dry run (no file writes). Use --write to persist memory updates.[/dim]")
