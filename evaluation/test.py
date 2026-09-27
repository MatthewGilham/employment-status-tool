import json
from pathlib import Path
from pydantic import BaseModel, Field

TEST_FILE = str(Path(__file__).parent / "tests.jsonl")


class TestQuestion(BaseModel):
    """A test question with expected keywords and reference answer."""
    id: str  = Field(description="The ID of the question")
    gate: str  = Field(description="The gate relevant to the question")
    facts: str  = Field(description="The facts used to answer the question")
    keywords: list[str] = Field(description="Keywords that must appear in retrieved context")
    expected_outcome: str = Field(description="Expected outcome of analysis")
    reference_answer: str = Field(description="The reference answer for this question")
    category: str = Field(description="Question category (e.g., contract_vs_practice, lay_language, direct)")


def load_tests() -> list[TestQuestion]:
    """Load test questions from JSONL file."""
    tests = []
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line.strip())
            tests.append(TestQuestion(**data))
    return tests
