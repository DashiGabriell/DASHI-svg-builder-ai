"""UI event name constants shared by controllers and views."""

from __future__ import annotations

# Project / pipeline
PROJECT_UPDATED = "project.updated"
STATUS_MESSAGE = "status.message"
ACTION_REQUESTED = "action.requested"
ACTION_COMPLETED = "action.completed"
ACTION_FAILED = "action.failed"

# Preview channels
PREVIEW_ORIGINAL = "preview.original"
PREVIEW_PROCESSED = "preview.processed"
PREVIEW_SVG = "preview.svg"

# Layers (Stage 4+)
LAYERS_UPDATED = "layers.updated"
LAYER_SELECTED = "layer.selected"
