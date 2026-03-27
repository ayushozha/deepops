from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Mapping


def _load_dotenv(dotenv_path: Path) -> dict[str, str]:
    if not dotenv_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"").strip("'")
    return values


@dataclass(frozen=True)
class Settings:
    service_name: str = "deepops-person-a"
    environment: str = "hackathon"
    aerospike_host: str = "127.0.0.1"
    aerospike_port: int = 3000
    aerospike_namespace: str = "deepops"
    aerospike_set: str = "incidents"
    overmind_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    macroscope_api_key: str | None = None
    macroscope_base_url: str = "https://api.macroscope.com/v1"
    kiro_command: str = "kiro"
    overclaw_agent_name: str = "deepops-person-a"
    overclaw_policy_path: str = "docs/ayush/person-a-policy.md"
    overclaw_dataset_path: str = "data/person_a_dataset.json"

    @property
    def aerospike_config(self) -> dict[str, object]:
        return {
            "hosts": [(self.aerospike_host, self.aerospike_port)],
            "namespace": self.aerospike_namespace,
            "set": self.aerospike_set,
        }


def load_settings(
    *,
    env: Mapping[str, str] | None = None,
    dotenv_path: str | Path = ".env",
) -> Settings:
    dotenv_values = _load_dotenv(Path(dotenv_path))
    merged = dict(dotenv_values)
    merged.update(os.environ)
    if env is not None:
        merged.update(env)

    return Settings(
        service_name=merged.get("DEEPOPS_SERVICE_NAME", "deepops-person-a"),
        environment=merged.get("DEEPOPS_ENVIRONMENT", "hackathon"),
        aerospike_host=merged.get("AEROSPIKE_HOST", "127.0.0.1"),
        aerospike_port=int(merged.get("AEROSPIKE_PORT", "3000")),
        aerospike_namespace=merged.get("AEROSPIKE_NAMESPACE", "deepops"),
        aerospike_set=merged.get("AEROSPIKE_SET", "incidents"),
        overmind_api_key=merged.get("OVERMIND_API_KEY"),
        anthropic_api_key=merged.get("ANTHROPIC_API_KEY"),
        openai_api_key=merged.get("OPENAI_API_KEY"),
        macroscope_api_key=merged.get("MACROSCOPE_API_KEY"),
        macroscope_base_url=merged.get("MACROSCOPE_BASE_URL", "https://api.macroscope.com/v1"),
        kiro_command=merged.get("KIRO_COMMAND", "kiro"),
        overclaw_agent_name=merged.get("OVERCLOW_AGENT_NAME", "deepops-person-a"),
        overclaw_policy_path=merged.get("OVERCLOW_POLICY_PATH", "docs/ayush/person-a-policy.md"),
        overclaw_dataset_path=merged.get("OVERCLOW_DATASET_PATH", "data/person_a_dataset.json"),
    )
