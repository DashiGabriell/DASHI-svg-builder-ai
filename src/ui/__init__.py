"""UI package — CustomTkinter desktop shell."""

from src.ui.app import run_app
from src.ui.controller import AppController
from src.ui.state import AppState

__all__ = ["AppController", "AppState", "run_app"]
