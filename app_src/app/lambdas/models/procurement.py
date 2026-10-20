from pydantic import BaseModel


class Procurement(BaseModel):
    id: str
    name: str
