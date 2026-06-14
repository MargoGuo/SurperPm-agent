"""SQLModel table definitions for SuperPmAgent."""

from app.models.discussion import Discussion
from app.models.execution import Execution
from app.models.global_config import GlobalConfig
from app.models.goal import Goal
from app.models.goal_group import GoalGroup
from app.models.mcp_server import MCPServer
from app.models.secret import Secret
from app.models.skill import Skill, SkillFile
from app.models.topic import Topic
from app.models.workspace import Workspace

__all__ = [
    "Discussion",
    "Execution",
    "GlobalConfig",
    "Goal",
    "GoalGroup",
    "MCPServer",
    "Secret",
    "Skill",
    "SkillFile",
    "Topic",
    "Workspace",
]
