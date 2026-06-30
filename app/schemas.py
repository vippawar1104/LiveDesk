from pydantic import BaseModel, Field


class FeedbackSubmission(BaseModel):
    message: str = Field(min_length=3, max_length=2000)
    name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    rating: int | None = Field(default=None, ge=1, le=5)
    page: str | None = Field(default=None, max_length=200)
