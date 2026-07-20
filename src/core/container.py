"""Lightweight dependency injection container.

Provides constructor injection without requiring a heavy third-party DI
framework. Services register factories (or instances) and dependents resolve
them by type or by string key.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

from src.core.exceptions import ConfigurationError

T = TypeVar("T")

Factory = Callable[["Container"], Any]


class Container:
    """Simple service locator / DI registry.

    Typical usage::

        container = Container()
        container.register(Settings, instance=settings)
        container.register(AIService, factory=lambda c: AIService(c.resolve(OpenRouterClient)))
        ai = container.resolve(AIService)
    """

    def __init__(self) -> None:
        self._factories: dict[str, Factory] = {}
        self._singletons: dict[str, Any] = {}
        self._singleton_flags: dict[str, bool] = {}

    @staticmethod
    def _key(service_type: type[Any] | str) -> str:
        if isinstance(service_type, str):
            return service_type
        return f"{service_type.__module__}.{service_type.__qualname__}"

    def register(
        self,
        service_type: type[T] | str,
        *,
        factory: Factory | None = None,
        instance: T | None = None,
        singleton: bool = True,
    ) -> None:
        """Register a service factory or a concrete instance.

        Args:
            service_type: Type or string key used for resolution.
            factory: Callable receiving the container and returning the service.
            instance: Pre-built instance (implies singleton).
            singleton: When True, the first resolved value is cached.
        """
        key = self._key(service_type)

        if instance is not None and factory is not None:
            raise ConfigurationError("Provide either factory or instance, not both.")

        if instance is not None:
            self._singletons[key] = instance
            self._singleton_flags[key] = True
            self._factories[key] = lambda _c: instance
            return

        if factory is None:
            raise ConfigurationError("A factory or instance is required to register a service.")

        self._factories[key] = factory
        self._singleton_flags[key] = singleton
        self._singletons.pop(key, None)

    def is_registered(self, service_type: type[Any] | str) -> bool:
        """Return True if the given type/key has a registration."""
        return self._key(service_type) in self._factories

    def resolve(self, service_type: type[T] | str) -> T:
        """Resolve a service, creating it via its factory when needed.

        Raises:
            ConfigurationError: If the service was never registered.
        """
        key = self._key(service_type)

        if key not in self._factories:
            raise ConfigurationError(f"Service not registered: {key}")

        if self._singleton_flags.get(key, True) and key in self._singletons:
            return cast(T, self._singletons[key])

        value = self._factories[key](self)

        if self._singleton_flags.get(key, True):
            self._singletons[key] = value

        return cast(T, value)

    def reset(self) -> None:
        """Clear all registrations (intended for tests)."""
        self._factories.clear()
        self._singletons.clear()
        self._singleton_flags.clear()


_container: Container | None = None


def get_container() -> Container:
    """Return the process-wide container singleton."""
    global _container
    if _container is None:
        _container = Container()
    return _container


def reset_container() -> None:
    """Replace the global container (tests only)."""
    global _container
    if _container is not None:
        _container.reset()
    _container = Container()
