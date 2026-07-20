"""Factory / registry for Strategy processors (plugin system)."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from collections.abc import Callable
from typing import TypeVar

from src.core.exceptions import PluginError
from src.core.interfaces import Processor

logger = logging.getLogger(__name__)

P = TypeVar("P", bound=type[Processor])


class PluginRegistry:
    """Register and resolve processors by name without touching the core.

    Example::

        @registry.register
        class RemoveNoiseProcessor(BaseProcessor):
            name = "remove_noise"
            ...

        processor = registry.create("remove_noise")
    """

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], Processor]] = {}

    def register(
        self,
        processor_cls: P | None = None,
        *,
        name: str | None = None,
    ) -> P | Callable[[P], P]:
        """Class decorator (or direct call) to register a processor type."""

        def decorator(cls: P) -> P:
            key = name or getattr(cls, "name", None)
            if callable(key):
                # `name` may be a @property on the class — instantiate lightly
                # via a temporary instance only if needed; prefer explicit attr.
                key = None
            if not key:
                # Fall back to reading class-level attribute or name property default
                instance_name = getattr(cls, "processor_name", None)
                key = instance_name or cls.__name__
            key = str(key)

            def factory() -> Processor:
                return cls()  # type: ignore[call-arg]

            if key in self._factories:
                raise PluginError(f"Processor already registered: {key}")

            self._factories[key] = factory
            logger.debug("Registered processor plugin: %s -> %s", key, cls.__name__)
            return cls

        if processor_cls is not None:
            return decorator(processor_cls)
        return decorator

    def register_factory(self, name: str, factory: Callable[[], Processor]) -> None:
        """Register an explicit factory (supports DI-constructed processors)."""
        if name in self._factories:
            raise PluginError(f"Processor already registered: {name}")
        self._factories[name] = factory

    def create(self, name: str) -> Processor:
        """Instantiate a registered processor by name."""
        if name not in self._factories:
            raise PluginError(
                f"Unknown processor '{name}'. Available: {sorted(self._factories)}"
            )
        return self._factories[name]()

    def available(self) -> list[str]:
        """List registered processor names."""
        return sorted(self._factories)

    def discover(self, package_name: str = "src.processors") -> int:
        """Import all submodules under a package to trigger ``@register`` side effects.

        Returns:
            Number of modules imported.
        """
        try:
            package = importlib.import_module(package_name)
        except ImportError as exc:
            raise PluginError(f"Cannot import plugin package '{package_name}'") from exc

        if not hasattr(package, "__path__"):
            return 0

        count = 0
        for module_info in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            # Skip base package internals if needed — importing is still fine
            if module_info.name.endswith(".base.processor_base"):
                continue
            if module_info.name.endswith(".base.plugin_registry"):
                continue
            importlib.import_module(module_info.name)
            count += 1
            logger.debug("Discovered plugin module: %s", module_info.name)
        return count


_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    """Process-wide plugin registry singleton."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry
