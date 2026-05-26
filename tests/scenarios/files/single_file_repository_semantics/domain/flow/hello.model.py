from pydantic import BaseModel


class HelloOutput(BaseModel):
    value: str