"""Command pattern foundations for undoable UI / layer edits."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import deque

logger = logging.getLogger(__name__)


class Command(ABC):
    """Abstract command supporting execute / undo."""

    @abstractmethod
    def execute(self) -> None:
        """Apply the command."""

    @abstractmethod
    def undo(self) -> None:
        """Revert the command."""

    @property
    def description(self) -> str:
        """Human-readable label for history / UI."""
        return self.__class__.__name__


class CommandHistory:
    """Undo/redo stack for editing actions (layers, colors, transforms)."""

    def __init__(self, *, max_size: int = 100) -> None:
        self._undo_stack: deque[Command] = deque(maxlen=max_size)
        self._redo_stack: deque[Command] = deque(maxlen=max_size)

    def execute(self, command: Command) -> None:
        """Execute a command and push it onto the undo stack."""
        command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()
        logger.debug("Executed command: %s", command.description)

    def undo(self) -> bool:
        """Undo the last command. Returns False if history is empty."""
        if not self._undo_stack:
            return False
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        logger.debug("Undid command: %s", command.description)
        return True

    def redo(self) -> bool:
        """Redo the last undone command. Returns False if redo stack is empty."""
        if not self._redo_stack:
            return False
        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)
        logger.debug("Redid command: %s", command.description)
        return True

    def clear(self) -> None:
        """Clear undo and redo history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
