"""Base processor helpers for the plugin architecture."""

from __future__ import annotations

import logging
from typing import Any

from src.core.exceptions import ProcessorError
from src.core.interfaces import Processor
from src.models.project import ProjectDocument

logger = logging.getLogger(__name__)


class BaseProcessor(Processor):
    """Concrete-friendly base for Strategy processors.

    Subclasses implement ``_execute``; this class handles logging and
    uniform error wrapping.
    """

    @property
    def name(self) -> str:
        raise NotImplementedError

    def process(self, project: ProjectDocument, **kwargs: Any) -> ProjectDocument:
        """Run the processor with structured logging and error mapping."""
        logger.info("Processor '%s' starting (stage=%s)", self.name, project.stage)
        try:
            result = self._execute(project, **kwargs)
        except ProcessorError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Processor '%s' failed", self.name)
            raise ProcessorError(f"Processor '{self.name}' failed: {exc}") from exc

        logger.info("Processor '%s' finished (stage=%s)", self.name, result.stage)
        return result

    def _execute(self, project: ProjectDocument, **kwargs: Any) -> ProjectDocument:
        """Subclass hook — perform the actual transformation."""
        raise NotImplementedError
