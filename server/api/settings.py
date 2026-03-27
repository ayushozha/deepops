from __future__ import annotations

from hashlib import sha1
from shutil import which
from time import time

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _system_id(service_name: str, environment: str) -> str:
    digest = sha1(f"{service_name}:{environment}".encode("utf-8")).hexdigest()[:10]
    return f"{service_name.upper()}-{environment.upper()}-{digest}".replace("_", "-")


def _global_webhook_url(request: Request) -> str:
    settings = request.app.state.context.settings
    if settings.public_webhook_url:
        return settings.public_webhook_url
    if settings.bland_webhook_url:
        return settings.bland_webhook_url
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/webhooks/bland"


def _integration_entry(
    *,
    name: str,
    status: str,
    summary: str,
    action_label: str,
    color: str,
    details: list[str],
) -> dict[str, object]:
    return {
        "name": name,
        "status": status,
        "summary": summary,
        "action_label": action_label,
        "color": color,
        "details": details,
    }


@router.get("/overview")
async def settings_overview(request: Request) -> dict[str, object]:
    context = request.app.state.context
    settings = context.settings
    store_name = type(context.store).__name__
    kiro_available = which(settings.kiro_command) is not None
    auth0_configured = bool(
        settings.auth0_domain and settings.auth0_client_id and settings.auth0_client_secret
    )
    bland_ready = bool(
        settings.bland_api_key and settings.bland_phone_number and settings.bland_webhook_url
    )
    truefoundry_ready = bool(settings.truefoundry_api_key)
    macroscope_ready = bool(settings.macroscope_api_key)
    overmind_ready = bool(settings.overmind_api_key)

    integrations = [
        _integration_entry(
            name="Airbyte",
            status="active" if not settings.airbyte_fallback_mode else "fallback",
            summary="Data ingestion and sync entrypoint for runtime signals.",
            action_label="Check ingest",
            color="#FF6133",
            details=[
                f"api_url={settings.airbyte_api_url}",
                f"fallback_mode={settings.airbyte_fallback_mode}",
            ],
        ),
        _integration_entry(
            name="Aerospike",
            status="active" if "Aerospike" in store_name else "fallback",
            summary="Canonical incident record store.",
            action_label="Check store",
            color="#C12127",
            details=[
                f"backend={store_name}",
                f"namespace={settings.aerospike_namespace}",
                f"set={settings.aerospike_set}",
                f"host={settings.aerospike_host}:{settings.aerospike_port}",
            ],
        ),
        _integration_entry(
            name="Macroscope",
            status="active" if macroscope_ready else "halted",
            summary="Diagnosis context and codebase understanding provider.",
            action_label="Check auth",
            color="#634BFF",
            details=[
                f"configured={macroscope_ready}",
                f"base_url={settings.macroscope_base_url}",
            ],
        ),
        _integration_entry(
            name="Kiro",
            status="active" if kiro_available else "halted",
            summary="Fix generation command path for constrained remediation.",
            action_label="Check command",
            color="#00DAF3",
            details=[
                f"command={settings.kiro_command}",
                f"available={kiro_available}",
            ],
        ),
        _integration_entry(
            name="Auth0",
            status="active" if auth0_configured else "halted",
            summary="Approval gate and identity provider for human-in-the-loop decisions.",
            action_label="Check gate",
            color="#EB5424",
            details=[
                f"configured={auth0_configured}",
                f"domain={settings.auth0_domain or 'unset'}",
            ],
        ),
        _integration_entry(
            name="Bland AI",
            status="active" if bland_ready else "partial" if settings.bland_api_key else "halted",
            summary="Phone escalation provider for critical incidents.",
            action_label="Check call path",
            color="#FFFFFF",
            details=[
                f"api_key={bool(settings.bland_api_key)}",
                f"phone_number={bool(settings.bland_phone_number)}",
                f"webhook_url={bool(settings.bland_webhook_url)}",
            ],
        ),
        _integration_entry(
            name="TrueFoundry",
            status="active" if truefoundry_ready else "halted",
            summary="Deployment target and rollout callback path.",
            action_label="Check deploy",
            color="#10B981",
            details=[
                f"configured={truefoundry_ready}",
                f"service={settings.truefoundry_service_name}",
                f"environment={settings.truefoundry_environment}",
            ],
        ),
        _integration_entry(
            name="Overmind",
            status="active" if overmind_ready else "halted",
            summary="Tracing and optimization signal capture.",
            action_label="Check trace",
            color="#A855F7",
            details=[
                f"configured={overmind_ready}",
                f"heartbeat_seconds={settings.realtime_heartbeat_seconds}",
            ],
        ),
    ]

    return {
        "system": {
            "service_name": settings.service_name,
            "environment": settings.environment,
            "system_id": _system_id(settings.service_name, settings.environment),
            "terminal_version": "v0.1.0",
            "maintenance_mode": settings.maintenance_mode,
            "backend": "fastapi",
            "store": store_name,
            "allow_in_memory_store": settings.allow_in_memory_store,
        },
        "webhook": {
            "url": _global_webhook_url(request),
            "label": "Inbound automation callback",
            "note": "Primary callback path for outbound sponsor workflows and incident escalations.",
        },
        "integrations": integrations,
        "runtime": {
            "generated_at_ms": int(time() * 1000),
            "api_host": settings.api_host,
            "api_port": settings.api_port,
            "realtime_heartbeat_seconds": settings.realtime_heartbeat_seconds,
            "demo_app_base_url": settings.demo_app_base_url,
        },
    }
