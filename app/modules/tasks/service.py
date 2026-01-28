import uuid
from typing import Optional

from app.core.exceptions import NotFoundException

from .models import Task
from .repository import TaskRepository
from .schemas import TaskCreate, TaskUpdate


class TaskService:
    no_task: str = "Task not found"

    def __init__(self, repository: TaskRepository):
        self.repository = repository

    # CREATE
    # ----------------------
    def create_task(self, item_data: TaskCreate):
        task_db = Task.model_validate(item_data.model_dump())
        return self.repository.create(task_db)

    # GET ONE
    # ----------------------
    def get_task(self, item_id: uuid.UUID):
        task_db = self.repository.get_by_id(item_id)
        if not task_db:
            raise NotFoundException(detail=self.no_task)
        return task_db

    # UPDATE
    # ----------------------
    def update_task(self, item_id: uuid.UUID, item_data: TaskUpdate):
        item_data_dict = item_data.model_dump(exclude_unset=True)
        updated_task = self.repository.update(item_id, item_data_dict)

        if not updated_task:
            raise NotFoundException(detail=self.no_task)
        return updated_task

    # GET ALL PLANS
    # ----------------------
    def get_tasks(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
    ):
        return self.repository.get_all(offset, limit, sort_by, sort_order, search)

    def count(self, search: Optional[str] = None) -> int:
        return self.repository.count(search)

    # DELETE
    # ----------------------
    def delete_task(self, item_id: uuid.UUID):
        success = self.repository.delete(item_id)
        if not success:
            raise NotFoundException(detail=self.no_task)
        return {"detail": "ok"}
