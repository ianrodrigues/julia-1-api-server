"""The named-question contract exposed in OpenAPI and validated before inference."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

# Reject blank strings without modifying caller IDs, descriptions, or state text.
Identifier = Annotated[
    str, StringConstraints(strict=True, min_length=1, max_length=128, pattern=r"\S")
]
Description = Annotated[
    str, StringConstraints(strict=True, min_length=1, max_length=4096, pattern=r"\S")
]


class QuestionBase(BaseModel):
    """Common question fields; unknown fields fail loudly instead of being ignored."""

    model_config = ConfigDict(extra="forbid")
    instructions: Annotated[
        str, StringConstraints(strict=True, min_length=1, max_length=8192, pattern=r"\S")
    ]


class ChoiceQuestion(QuestionBase):
    """Select a caller-defined ID from two through twenty descriptions."""

    type: Literal["choice"]
    criteria: dict[Identifier, Description] = Field(min_length=2, max_length=20)


class ScoreQuestion(QuestionBase):
    """Return the expected zero-based index of an ordered rubric."""

    type: Literal["score"]
    criteria: list[Description] = Field(min_length=2, max_length=20)


class NoulQuestion(QuestionBase):
    """Return the probability of true, optionally using custom Boolean descriptions."""

    type: Literal["noul"]
    criteria: dict[Literal["false", "true"], Description] | None = None

    @field_validator("criteria")
    @classmethod
    def validate_boolean_labels(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is not None and set(value) != {"false", "true"}:
            raise ValueError('noul criteria must contain exactly "false" and "true"')
        return value


Question = Annotated[ChoiceQuestion | ScoreQuestion | NoulQuestion, Field(discriminator="type")]


class ClassifyRequest(BaseModel):
    """One state shared by a bounded batch of independent questions."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "state": (
                        "I was charged twice for the same order. "
                        "Please refund the duplicate charge."
                    ),
                    "questions": {
                        "team": {
                            "type": "choice",
                            "instructions": "Which team should handle this request?",
                            "criteria": {
                                "billing": "Billing and payment disputes",
                                "shipping": "Shipping and delivery",
                                "access": "Account access and login",
                            },
                        },
                        "urgency": {
                            "type": "score",
                            "instructions": "How urgently should this request be handled?",
                            "criteria": ["Routine", "Soon", "Immediate"],
                        },
                        "refund_needed": {
                            "type": "noul",
                            "instructions": "Does the customer request a refund?",
                        },
                    },
                }
            ]
        },
    )
    state: Annotated[
        str, StringConstraints(strict=True, min_length=1, max_length=131072, pattern=r"\S")
    ]
    questions: dict[Identifier, Question] = Field(min_length=1, max_length=32)


class ClassifyResponse(BaseModel):
    """Preserve upstream answer fields and any future top-level payload metadata."""

    model_config = ConfigDict(extra="allow")
    answers: dict[str, Any]
    execution_time_ms: float = Field(ge=0)


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    model_loaded: bool
    device: str
