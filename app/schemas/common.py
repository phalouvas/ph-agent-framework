from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Human-readable error message")
    details: str | None = Field(None, description="Additional error details")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status, always 'ok' when healthy")
    version: str = Field(..., description="Application version string")
