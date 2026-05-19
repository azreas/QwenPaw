from pydantic import BaseModel, Field


class ReadinessCheck(BaseModel):
    name: str
    status: str = Field(pattern="^(pass|warn|fail)$")
    required: bool = False
    message: str = ""


class ReadinessSummary(BaseModel):
    status: str = Field(pattern="^(ready|degraded|blocked)$")
    checks: list[ReadinessCheck]
    blockers: list[str]
