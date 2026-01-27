from typing import Optional

from sqlmodel import Field

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin


class Task(BaseModel, AuditMixin, table=True):
    """
    Task model that represents a task in the database.
    """

    __tablename__ = "tasks"

    title: str = Field(default=None, description="The title of the task")
    description: Optional[str] = Field(
        default=None, description="The description of the task"
    )
    completed: bool = Field(
        default=False, description="The completion status of the task"
    )
