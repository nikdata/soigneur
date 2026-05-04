"""
Goals service.

Loads goals from ``app/config/goals.yml`` and returns them as ``Goal`` models.
"""

from __future__ import annotations
from pathlib import Path
import yaml
from app.models.goal import Goal, GoalConfig

goal_file_path = Path(__file__).resolve().parent.parent / "config" / "goals.yaml"


async def fetch_goals() -> list[Goal]:
    """Load and validate goals from the bundled YAML config.

    Returns:
        List of ``Goal`` instances, ordered as in the file.

    Raises:
        FileNotFoundError: If ``goals.yml`` is missing.
        pydantic.ValidationError: If the YAML does not match the models.
        yaml.YAMLError: If the file is not valid YAML.
    """
    if not goal_file_path.is_file():
        msg = f"Goals config not found: {goal_file_path}"
        raise FileNotFoundError(msg)

    raw = yaml.safe_load(goal_file_path.read_text(encoding="utf-8"))
    config = GoalConfig.model_validate(raw)
    return config.goals