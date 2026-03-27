from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol, TypeVar

from config import Settings

T = TypeVar("T")


class SpanLike(Protocol):
    def __enter__(self) -> "SpanLike": ...

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None: ...

    def set_attribute(self, key: str, value: Any) -> None: ...


class TracerLike(Protocol):
    def start_as_current_span(self, name: str) -> SpanLike: ...


@dataclass
class NullSpan:
    name: str

    def __enter__(self) -> "NullSpan":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None

    def set_attribute(self, key: str, value: Any) -> None:
        return None


@dataclass
class NullTracer:
    def start_as_current_span(self, name: str) -> NullSpan:
        return NullSpan(name=name)


def get_tracer(settings: Settings) -> TracerLike:
    try:
        import overmind  # type: ignore
    except ImportError:
        return NullTracer()

    if settings.overmind_api_key:
        overmind.init(
            overmind_api_key=settings.overmind_api_key,
            service_name=settings.service_name,
            environment=settings.environment,
        )
    return overmind.get_tracer()


def call_tool(name: str, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    try:
        from overclaw.core.tracer import call_tool as overclaw_call_tool  # type: ignore
    except ImportError:
        return func(*args, **kwargs)

    try:
        return overclaw_call_tool(name=name, func=func, args=args, kwargs=kwargs)
    except TypeError:
        try:
            return overclaw_call_tool(name, func, *args, **kwargs)
        except TypeError:
            return func(*args, **kwargs)


def call_llm(provider_call: Callable[..., T], **kwargs: Any) -> T:
    try:
        from overclaw.core.tracer import call_llm as overclaw_call_llm  # type: ignore
    except ImportError:
        return provider_call(**kwargs)

    try:
        return overclaw_call_llm(**kwargs)
    except TypeError:
        return provider_call(**kwargs)
