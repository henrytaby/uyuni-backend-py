from pydantic import EmailStr
from sqlmodel import Field

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin


class Customer(BaseModel, AuditMixin, table=True):
    __tablename__ = "customers"
    name: str = Field(default=None)
    last_name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    email: EmailStr = Field(default=None)
    age: int = Field(default=None)
