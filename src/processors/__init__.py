"""Plugin / processor discovery package."""

from src.processors.base.plugin_registry import PluginRegistry, get_plugin_registry
from src.processors.base.processor_base import BaseProcessor

# Import concrete processors so @register side effects run even without discover().
from . import processor_detect_objects as _detect  # noqa: F401
from . import processor_load_image as _load  # noqa: F401
from . import processor_optimize_svg as _optimize  # noqa: F401
from . import processor_remove_background as _bg  # noqa: F401
from . import processor_separate_layers as _layers  # noqa: F401
from . import processor_upscale as _upscale  # noqa: F401
from . import processor_vectorize as _vectorize  # noqa: F401

__all__ = ["BaseProcessor", "PluginRegistry", "get_plugin_registry"]
