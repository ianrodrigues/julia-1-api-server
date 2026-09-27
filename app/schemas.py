"""The Jev-compatible System One contract exposed in OpenAPI and validated before inference."""

import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Reject blank strings without modifying caller IDs, descriptions, or state text.
Identifier = Annotated[
    str, StringConstraints(strict=True, min_length=1, max_length=128, pattern=r"\S")
]
Text = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=8192, pattern=r"\S")]
# Jev lets instructions and criteria be structured; the model receives them as JSON text.
Content = (
    Text
    | Annotated[dict[str, Any], Field(min_length=1)]
    | Annotated[list[Any], Field(min_length=1)]
)


def render(content: Any) -> str:
    """Render structured content the way the runtime renders structured state."""
    return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)


class QuestionBase(BaseModel):
    """Common question fields; unknown fields fail loudly instead of being ignored."""

    model_config = ConfigDict(extra="forbid")
    instructions: Content


class ChoiceQuestion(QuestionBase):
    """Select a caller-defined option; a null description uses the option ID itself."""

    type: Literal["choice"]
    criteria: dict[Identifier, Content | None] = Field(min_length=2, max_length=20)


class ScoreQuestion(QuestionBase):
    """Return the expected zero-based level of an ordered rubric."""

    type: Literal["score"]
    criteria: list[Content] = Field(min_length=2, max_length=20)


class NoulCriteria(BaseModel):
    model_config = ConfigDict(extra="forbid")
    true: Content | None = None
    false: Content | None = None


class NoulQuestion(QuestionBase):
    """Return the probability of yes, optionally describing what yes and no mean."""

    type: Literal["noul"]
    criteria: NoulCriteria | None = None


Question = Annotated[ChoiceQuestion | ScoreQuestion | NoulQuestion, Field(discriminator="type")]

STATE_EXAMPLE = "Help! My payouts have been failing for 3 days."


class SystemOneRequest(BaseModel):
    """One state shared by a bounded batch of independent, named questions."""

    # Ignore top-level fields a newer Jev client may send, as Jev clients expect.
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "examples": [
                {
                    "state": STATE_EXAMPLE,
                    "model": "jev-latest",
                    "questions": {
                        "department": {
                            "type": "choice",
                            "instructions": "Which team should handle this?",
                            "criteria": {
                                "billing": "Payments, invoicing, refunds",
                                "technical": "Bugs, outages, integrations",
                                "sales": "Pricing, upgrades, new accounts",
                            },
                        },
                        "frustration": {
                            "type": "score",
                            "instructions": "How frustrated is the customer?",
                            "criteria": ["Calm", "Frustrated", "Very angry"],
                        },
                        "is_urgent": {
                            "type": "noul",
                            "instructions": "Does this convey urgency?",
                        },
                    },
                }
            ]
        },
    )
    state: (
        Annotated[
            str, StringConstraints(strict=True, min_length=1, max_length=131072, pattern=r"\S")
        ]
        | Annotated[dict[str, Any], Field(min_length=1)]
        | Annotated[list[Any], Field(min_length=1)]
    )
    # Accepted for Jev compatibility; this server always answers with its own model.
    model: str | None = None
    questions: dict[Identifier, Question] = Field(min_length=1, max_length=32)


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int


class NoulAnswer(BaseModel):
    type: Literal["noul"]
    noul: float = Field(ge=0, le=1)


class ChoiceAnswer(BaseModel):
    type: Literal["choice"]
    choice: str
    probabilities: dict[str, float]
    confidence: float = Field(ge=0, le=1)


class ScoreAnswer(BaseModel):
    type: Literal["score"]
    score: float
    legend: dict[str, Any]
    probabilities: dict[str, float]
    confidence: float = Field(ge=0, le=1)


Answer = Annotated[NoulAnswer | ChoiceAnswer | ScoreAnswer, Field(discriminator="type")]


class SystemOneResponse(BaseModel):
    model: str
    answers: dict[str, Answer]
    usage: Usage


class ModelMetadata(BaseModel):
    name: str
    description: str
    release_date: str


class ListModelsResponse(BaseModel):
    models: list[ModelMetadata]


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    model_loaded: bool
    device: str
