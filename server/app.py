from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from fastapi import FastAPI

from agent.orchestrator import DiagnosisRunner, FixRunner
from agent.runner import _load_diagnoser, _load_fixer
from agent.store_adapter import IncidentStore
from agent.tracing import TracerLike, get_tracer
from config import Settings, load_settings
from server.api.agent import router as agent_router
from server.api.approval import router as approval_router
from server.api.escalation import router as escalation_router
from server.api.ingest import router as ingest_router
from server.api.incidents import router as incidents_router
from server.api.stream import router as stream_router
from server.api.settings import router as settings_router
from server.api.webhooks import router as webhooks_router
from server.integrations.aerospike_repo import build_incident_store
from server.integrations.airbyte_client import AirbyteClient
from server.integrations.auth0_client import Auth0Client, Auth0Config, Auth0ConfigError
from server.integrations.bland_client import BlandClient, BlandConfigError, MockBlandClient
from server.integrations.demo_app_client import DemoAppClient
from server.integrations.truefoundry_client import MockTrueFoundryClient, TrueFoundryClient
from server.services.deployment_service import DeploymentService
from server.services.demo_flow_service import DemoFlowService
from server.services.escalation_service import EscalationService
from server.services.gating_service import GatingService
from server.services.ingestion_service import IngestionService
from server.services.incident_service import IncidentService
from server.services.realtime_hub import RealtimeHub


@dataclass
class BackendContext:
    settings: Settings
    store: IncidentStore
    realtime_hub: RealtimeHub
    incidents: IncidentService
    gating: GatingService
    tracer: TracerLike
    diagnose: DiagnosisRunner
    generate_fix: FixRunner
    ingestion: IngestionService
    escalation: EscalationService
    deployment: DeploymentService
    workflow: DemoFlowService
    auth0: Auth0Client | None


def _build_bland_client(settings: Settings):
    if settings.bland_api_key:
        try:
            return BlandClient(api_key=settings.bland_api_key, base_url=settings.bland_base_url)
        except BlandConfigError:
            pass
    return MockBlandClient()


def _build_truefoundry_client(settings: Settings):
    if settings.truefoundry_api_key:
        return TrueFoundryClient(
            api_key=settings.truefoundry_api_key,
            base_url=settings.truefoundry_base_url,
            service_name=settings.truefoundry_service_name,
            environment=settings.truefoundry_environment,
        )
    return MockTrueFoundryClient(
        service_name=settings.truefoundry_service_name,
        environment=settings.truefoundry_environment,
    )


def _build_auth0_client(settings: Settings) -> Auth0Client | None:
    if not (settings.auth0_domain and settings.auth0_client_id and settings.auth0_client_secret):
        return None
    config = Auth0Config(
        domain=settings.auth0_domain,
        client_id=settings.auth0_client_id,
        client_secret=settings.auth0_client_secret,
        audience=settings.auth0_audience or "",
        redirect_uri=settings.auth0_redirect_uri or "",
        organization_id=settings.auth0_organization_id,
        approval_connection=settings.auth0_approval_connection,
        management_audience=settings.auth0_management_audience or "",
    )
    try:
        return Auth0Client(config=config)
    except Auth0ConfigError:
        return None


def _build_demo_app_client(settings: Settings) -> DemoAppClient:
    return DemoAppClient.from_settings(settings)


def _build_airbyte_client(settings: Settings) -> AirbyteClient:
    return AirbyteClient.from_settings(settings)


def create_app(
    *,
    settings: Settings | None = None,
    store: IncidentStore | None = None,
    diagnose: DiagnosisRunner | None = None,
    generate_fix: FixRunner | None = None,
    tracer: TracerLike | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    store = store or build_incident_store(settings)
    realtime_hub = RealtimeHub()
    incidents = IncidentService(store=store, realtime_hub=realtime_hub)
    gating = GatingService(incidents=incidents)
    tracer = tracer or get_tracer(settings)
    bland_client = _build_bland_client(settings)
    truefoundry = _build_truefoundry_client(settings)
    auth0 = _build_auth0_client(settings)
    demo_client = _build_demo_app_client(settings)
    airbyte_client = _build_airbyte_client(settings)
    ingestion = IngestionService(demo_client=demo_client, airbyte_client=airbyte_client)
    escalation = EscalationService(incidents=incidents, bland_client=bland_client)
    deployment = DeploymentService(store_adapter=incidents, truefoundry_client=truefoundry)
    workflow = DemoFlowService(
        settings=settings,
        store=store,
        incidents=incidents,
        tracer=tracer,
        diagnose=diagnose or _load_diagnoser(),
        generate_fix=generate_fix or _load_fixer(),
        escalation=escalation,
        truefoundry=truefoundry,
        deployment=deployment,
        auth0=auth0,
    )
    context = BackendContext(
        settings=settings,
        store=store,
        realtime_hub=realtime_hub,
        incidents=incidents,
        gating=gating,
        tracer=tracer,
        diagnose=workflow.diagnose,
        generate_fix=workflow.generate_fix,
        ingestion=ingestion,
        escalation=escalation,
        deployment=deployment,
        workflow=workflow,
        auth0=auth0,
    )

    app = FastAPI(title="DeepOps Backend", version="0.1.0")
    app.state.context = context

    @app.get("/api/health", tags=["health"])
    async def health() -> dict[str, Any]:
        try:
            sample = context.store.list_incidents(limit=1)
            return {
                "ok": True,
                "service": settings.service_name,
                "environment": settings.environment,
                "backend": "fastapi",
                "store": type(context.store).__name__,
                "sample_count": len(sample),
                "demo_app": {
                    "base_url": demo_client.base_url,
                    "fallback_mode": demo_client.fallback_mode,
                },
                "airbyte": {
                    "api_url": airbyte_client.api_url,
                    "fallback_mode": airbyte_client.fallback_mode,
                },
            }
        except Exception as exc:
            return {
                "ok": False,
                "service": settings.service_name,
                "environment": settings.environment,
                "backend": "fastapi",
                "store": type(context.store).__name__,
                "error": str(exc),
                "demo_app": {
                    "base_url": demo_client.base_url,
                    "fallback_mode": demo_client.fallback_mode,
                },
                "airbyte": {
                    "api_url": airbyte_client.api_url,
                    "fallback_mode": airbyte_client.fallback_mode,
                },
            }

    app.include_router(incidents_router)
    app.include_router(ingest_router)
    app.include_router(stream_router)
    app.include_router(settings_router)
    app.include_router(agent_router)
    app.include_router(approval_router)
    app.include_router(escalation_router)
    app.include_router(webhooks_router)
    return app
