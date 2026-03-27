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
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    maintenance_mode: bool = False
    public_webhook_url: str | None = None
    demo_app_base_url: str = "http://localhost:8001"
    demo_app_fallback_mode: bool = True
    airbyte_api_url: str = "http://localhost:8000/api/v1"
    airbyte_api_key: str | None = None
    airbyte_fallback_mode: bool = True
    aerospike_host: str = "127.0.0.1"
    aerospike_port: int = 3000
    aerospike_namespace: str = "deepops"
    aerospike_set: str = "incidents"
    allow_in_memory_store: bool = True
    realtime_heartbeat_seconds: int = 15
    overmind_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    bland_api_key: str | None = None
    bland_base_url: str = "https://api.bland.ai/v1"
    bland_phone_number: str | None = None
    bland_webhook_url: str | None = None
    macroscope_api_key: str | None = None
    macroscope_base_url: str = "https://api.macroscope.com/v1"
    kiro_command: str = "kiro"
    truefoundry_api_key: str | None = None
    truefoundry_base_url: str = "https://api.truefoundry.com/v1"
    truefoundry_service_name: str = "deepops-demo-app"
    truefoundry_environment: str = "hackathon"
    auth0_domain: str | None = None
    auth0_client_id: str | None = None
    auth0_client_secret: str | None = None
    auth0_audience: str | None = None
    auth0_redirect_uri: str | None = None
    auth0_organization_id: str | None = None
    auth0_approval_connection: str | None = None
    auth0_management_audience: str | None = None
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
        api_host=merged.get("DEEPOPS_API_HOST", "127.0.0.1"),
        api_port=int(merged.get("DEEPOPS_API_PORT", "8000")),
        maintenance_mode=merged.get("DEEPOPS_MAINTENANCE_MODE", "false").lower() in {"1", "true", "yes", "on"},
        public_webhook_url=merged.get("DEEPOPS_PUBLIC_WEBHOOK_URL"),
        demo_app_base_url=merged.get("DEEPOPS_DEMO_APP_BASE_URL", merged.get("DEMO_APP_URL", "http://localhost:8001")),
        demo_app_fallback_mode=merged.get("DEEPOPS_DEMO_APP_FALLBACK_MODE", "true").lower() in {"1", "true", "yes", "on"},
        airbyte_api_url=merged.get("AIRBYTE_API_URL", "http://localhost:8000/api/v1"),
        airbyte_api_key=merged.get("AIRBYTE_API_KEY"),
        airbyte_fallback_mode=merged.get("AIRBYTE_FALLBACK_MODE", "true").lower() in {"1", "true", "yes", "on"},
        aerospike_host=merged.get("AEROSPIKE_HOST", "127.0.0.1"),
        aerospike_port=int(merged.get("AEROSPIKE_PORT", "3000")),
        aerospike_namespace=merged.get("AEROSPIKE_NAMESPACE", "deepops"),
        aerospike_set=merged.get("AEROSPIKE_SET", "incidents"),
        allow_in_memory_store=merged.get("DEEPOPS_ALLOW_IN_MEMORY_STORE", "true").lower() in {"1", "true", "yes", "on"},
        realtime_heartbeat_seconds=int(merged.get("DEEPOPS_REALTIME_HEARTBEAT_SECONDS", "15")),
        overmind_api_key=merged.get("OVERMIND_API_KEY"),
        anthropic_api_key=merged.get("ANTHROPIC_API_KEY"),
        openai_api_key=merged.get("OPENAI_API_KEY"),
        bland_api_key=merged.get("BLAND_API_KEY"),
        bland_base_url=merged.get("BLAND_BASE_URL", "https://api.bland.ai/v1"),
        bland_phone_number=merged.get("BLAND_PHONE_NUMBER"),
        bland_webhook_url=merged.get("BLAND_WEBHOOK_URL"),
        macroscope_api_key=merged.get("MACROSCOPE_API_KEY"),
        macroscope_base_url=merged.get("MACROSCOPE_BASE_URL", "https://api.macroscope.com/v1"),
        kiro_command=merged.get("KIRO_COMMAND", "kiro"),
        truefoundry_api_key=merged.get("TRUEFOUNDRY_API_KEY"),
        truefoundry_base_url=merged.get("TRUEFOUNDRY_BASE_URL", "https://api.truefoundry.com/v1"),
        truefoundry_service_name=merged.get("TRUEFOUNDRY_SERVICE_NAME", "deepops-demo-app"),
        truefoundry_environment=merged.get("TRUEFOUNDRY_ENVIRONMENT", merged.get("DEEPOPS_ENVIRONMENT", "hackathon")),
        auth0_domain=merged.get("AUTH0_DOMAIN"),
        auth0_client_id=merged.get("AUTH0_CLIENT_ID"),
        auth0_client_secret=merged.get("AUTH0_CLIENT_SECRET"),
        auth0_audience=merged.get("AUTH0_AUDIENCE"),
        auth0_redirect_uri=merged.get("AUTH0_REDIRECT_URI", merged.get("AUTH0_CALLBACK_URL")),
        auth0_organization_id=merged.get("AUTH0_ORGANIZATION_ID"),
        auth0_approval_connection=merged.get("AUTH0_APPROVAL_CONNECTION", merged.get("AUTH0_CONNECTION")),
        auth0_management_audience=merged.get("AUTH0_MANAGEMENT_AUDIENCE"),
        overclaw_agent_name=merged.get("OVERCLAW_AGENT_NAME", merged.get("OVERCLOW_AGENT_NAME", "deepops-person-a")),
        overclaw_policy_path=merged.get("OVERCLAW_POLICY_PATH", merged.get("OVERCLOW_POLICY_PATH", "docs/ayush/person-a-policy.md")),
        overclaw_dataset_path=merged.get("OVERCLAW_DATASET_PATH", merged.get("OVERCLOW_DATASET_PATH", "data/person_a_dataset.json")),
    )
