from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SUPPORTED_AGENTS = ("codex.task", "claude.task")
AGENT_ALIASES = {
    "codex": "codex.task",
    "codex.task": "codex.task",
    "claude": "claude.task",
    "claude.task": "claude.task",
    "claude code": "claude.task",
    "claude code.task": "claude.task",
    "claude-code": "claude.task",
    "claude-code.task": "claude.task",
}


def normalize_agent(value: str) -> str:
    key = str(value or "").strip().lower()
    return AGENT_ALIASES.get(key, str(value or "").strip())


def _ruby_load_yaml(raw: str) -> dict[str, Any]:
    command = [
        "ruby",
        "-ryaml",
        "-rjson",
        "-e",
        "data = YAML.safe_load(ARGF.read, aliases: false); print JSON.generate(data)",
    ]
    result = subprocess.run(
        command,
        input=raw,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "Ruby YAML parser failed."
        raise RuntimeError(message)
    data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise ValueError("task.yml must contain a top-level mapping.")
    return data


def load_yaml(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        return _ruby_load_yaml(raw)

    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError("task.yml must contain a top-level mapping.")
    return data


def _ruby_dump_yaml(document: dict[str, Any]) -> str:
    payload = json.dumps(document, ensure_ascii=False)
    command = [
        "ruby",
        "-ryaml",
        "-rjson",
        "-e",
        (
            "data = JSON.parse(STDIN.read); "
            "output = YAML.dump(data); "
            "print output.sub(/\\A---\\s*\\n/, '')"
        ),
    ]
    result = subprocess.run(
        command,
        input=payload,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "Ruby YAML emitter failed."
        raise RuntimeError(message)
    return result.stdout


def dump_yaml(document: dict[str, Any]) -> str:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        return _ruby_dump_yaml(document)

    return yaml.safe_dump(
        document,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )


def validate_task(task: dict[str, Any], index: int) -> None:
    required_keys = ("task_id", "title", "description", "status", "agent")
    for key in required_keys:
        if key not in task:
            raise ValueError(f"tasks[{index}] is missing required key '{key}'.")


def build_agent_document(
    source_doc: dict[str, Any],
    *,
    agent_name: str,
    generated_from: str,
) -> dict[str, Any]:
    raw_tasks = source_doc.get("tasks")
    if not isinstance(raw_tasks, list):
        raise ValueError("task.yml must contain a top-level tasks array.")

    normalized_tasks: list[dict[str, Any]] = []
    for index, task in enumerate(raw_tasks):
        if not isinstance(task, dict):
            raise ValueError(f"tasks[{index}] must be a mapping.")
        validate_task(task, index)
        normalized_task = dict(task)
        normalized_task["agent"] = normalize_agent(str(task["agent"]))
        normalized_tasks.append(normalized_task)

    filtered_tasks = [task for task in normalized_tasks if task["agent"] == agent_name]
    shared_context = {key: value for key, value in source_doc.items() if key != "tasks"}
    shared_context["generated_from"] = generated_from
    shared_context["agent"] = agent_name
    shared_context["tasks"] = filtered_tasks
    return shared_context


def resolve_directory(raw_arg: str | None) -> Path:
    if not raw_arg:
        return Path(__file__).resolve().parent

    candidate = Path(raw_arg).expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if candidate.is_dir():
        return candidate
    if candidate.is_file() and candidate.name == "task.yml":
        return candidate.parent
    raise FileNotFoundError(f"task target not found: {candidate}")


def render_views(directory: Path) -> None:
    task_path = directory / "task.yml"
    if not task_path.is_file():
        raise FileNotFoundError(f"task.yml not found: {task_path}")

    source_doc = load_yaml(task_path)
    generated_from = str(task_path.relative_to(directory))

    for agent_name in SUPPORTED_AGENTS:
        output_doc = build_agent_document(
            source_doc,
            agent_name=agent_name,
            generated_from=generated_from,
        )
        output_path = directory / f"{agent_name}.yml"
        output_path.write_text(dump_yaml(output_doc), encoding="utf-8")
        print(f"wrote {output_path.relative_to(directory)}")


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        print(
            "usage: python render_task_views.py [./|task.yml|/abs/path/to/task.yml]",
            file=sys.stderr,
        )
        return 1

    raw_target = argv[1] if len(argv) == 2 else None
    try:
        render_views(resolve_directory(raw_target))
    except Exception as exc:  # pragma: no cover - error path glue
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
