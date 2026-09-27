import sys
import math
from pydantic import BaseModel, Field
from litellm import completion
from dotenv import load_dotenv
import json
from evaluation.test import TestQuestion, load_tests
from rag.retrival import retrieve_law
import law_content
from concurrent.futures import ThreadPoolExecutor, as_completed
import rag.retrival



load_dotenv(override=True)

MODEL = "gpt-4.1-nano"
JUDGE_MODEL = "gpt-4.1-mini"
K = rag.retrival.K
MAX_WORKERS = 5


class RetrievalEval(BaseModel):
    """Evaluation metrics for retrieval performance."""

    mrr: float = Field(description="Mean Reciprocal Rank - average across all keywords")
    ndcg: float = Field(description="Normalized Discounted Cumulative Gain (binary relevance)")
    keywords_found: int = Field(description="Number of keywords found in top-k results")
    total_keywords: int = Field(description="Total number of keywords to find")
    keyword_coverage: float = Field(description="Percentage of keywords found")


class AnswerEval(BaseModel):
    """LLM-as-a-judge evaluation of answer quality."""

    feedback: str = Field(
        description="Concise feedback on the answer quality, comparing it to the reference answer and evaluating based on the reference answer"
    )
    accuracy: float = Field(
        description="How factually correct is the answer compared to the reference answer? 1 (wrong. any wrong answer must score 1) to 5 (ideal - perfectly accurate). An acceptable answer would score 3."
    )
    completeness: float = Field(
        description="How complete is the answer in addressing all aspects of the question? 1 (very poor - missing key information) to 5 (ideal - all the information from the reference answer is provided completely). Only answer 5 if ALL information from the reference answer is included."
    )
    relevance: float = Field(
    description="How relevant is the answer to the gate being assessed? 1 (very poor - off-topic or assesses a different gate) to 5 (ideal - stays focused on the gate being assessed and the facts given)."
    )


def calculate_mrr(keyword: str, retrieved_docs: list) -> float:
    """Calculate reciprocal rank for a single keyword (case-insensitive)."""
    keyword_lower = keyword.lower()
    for rank, doc in enumerate(retrieved_docs, start=1):
        if keyword_lower in doc.page_content.lower():
            return 1.0 / rank
    return 0.0


def calculate_dcg(relevances: list[int], k: int) -> float:
    """Calculate Discounted Cumulative Gain."""
    dcg = 0.0
    for i in range(min(k, len(relevances))):
        dcg += relevances[i] / math.log2(i + 2)  # i+2 because rank starts at 1
    return dcg


def calculate_ndcg(keyword: str, retrieved_docs: list, k: int = K) -> float:
    """Calculate nDCG for a single keyword (binary relevance, case-insensitive)."""
    keyword_lower = keyword.lower()

    # Binary relevance: 1 if keyword found, 0 otherwise
    relevances = [
        1 if keyword_lower in doc.page_content.lower() else 0 for doc in retrieved_docs[:k]
    ]

    # DCG
    dcg = calculate_dcg(relevances, k)

    # Ideal DCG (best case: keyword in first position)
    ideal_relevances = sorted(relevances, reverse=True)
    idcg = calculate_dcg(ideal_relevances, k)

    return dcg / idcg if idcg > 0 else 0.0


def evaluate_retrieval(test: TestQuestion, k: int = K) -> RetrievalEval:
    """
    Evaluate retrieval performance for a test question.

    Args:
        test: TestQuestion object containing question and keywords
        k: Number of top documents to retrieve (default 10)

    Returns:
        RetrievalEval object with MRR, nDCG, and keyword coverage metrics
    """
    # Retrieve documents using shared answer module
    retrieved_docs = retrieve_law(test.facts, test.gate, k=k, pin_rule=False)

    # Calculate MRR (average across all keywords)
    mrr_scores = [calculate_mrr(keyword, retrieved_docs) for keyword in test.keywords]
    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0

    # Calculate nDCG (average across all keywords)
    ndcg_scores = [calculate_ndcg(keyword, retrieved_docs, k) for keyword in test.keywords]
    avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0

    # Calculate keyword coverage
    keywords_found = sum(1 for score in mrr_scores if score > 0)
    total_keywords = len(test.keywords)
    keyword_coverage = (keywords_found / total_keywords * 100) if total_keywords > 0 else 0.0

    return RetrievalEval(
        mrr=avg_mrr,
        ndcg=avg_ndcg,
        keywords_found=keywords_found,
        total_keywords=total_keywords,
        keyword_coverage=keyword_coverage,
    )


import prompts
from assessment import format_law, openrouter, model_gpt

PROMPTS = {
    "personal_service": prompts.system_prompt_gate1,
    "control": prompts.system_prompt_gate2,
    "financial": prompts.system_prompt_financial_risk,
    "organisation": prompts.system_prompt_organisation,
    "band": prompts.system_prompt_band,
}


def answer_test(test):
    if test.gate == "band":
        docs = []
        law = law_content.rmc_assess
    else:
        docs = retrieve_law(test.facts, test.gate)
        law = format_law(docs)
    system_prompt = PROMPTS[test.gate].format(law=law)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": test.facts},
    ]
    response = openrouter.chat.completions.create(
        model=model_gpt,
        messages=messages,
        temperature=0,
    )
    return response.choices[0].message.content, docs

VERDICT_KEY = {
    "personal_service": "outcome",
    "control": "outcome",
    "financial": "direction",
    "organisation": "direction",
    "band": "band",
}


def evaluate_answer(test: TestQuestion) -> tuple[AnswerEval, str, list, bool]:
    """Get the model's answer for a test, check the verdict, and have an LLM judge mark it."""
    generated_answer, retrieved_docs = answer_test(test)

    # Step 8: check the verdict in code
    try:
        data = json.loads(generated_answer)
        outcome_correct = str(data[VERDICT_KEY[test.gate]]).strip().lower() == test.expected_outcome
    except (json.JSONDecodeError, KeyError):
        outcome_correct = False

    # Step 6: judge prompt tailored to employment status
    judge_messages = [
        {
            "role": "system",
            "content": "You are an expert in UK employment status law (Ready Mixed Concrete, IR35) evaluating an AI's assessment of one part of an employment status test. Compare the generated answer to the reference answer. Only give 5/5 scores for perfect answers.",
        },
        {
            "role": "user",
            "content": f"""Gate being assessed: {test.gate}

Facts given to the AI:
{test.facts}

Generated Answer:
{generated_answer}

Expected verdict: {test.expected_outcome}

Reference Answer:
{test.reference_answer}

Evaluate the generated answer on three dimensions:
1. Accuracy: Is the verdict correct, and is the legal reasoning correct compared to the reference answer? If the verdict does not match the expected verdict, accuracy must be 1.
2. Completeness: Does it cover the key reasoning and authorities in the reference answer?
3. Relevance: Does it stay focused on the gate being assessed and the facts given?

Provide concise feedback and scores from 1 (very poor) to 5 (ideal) for each dimension.""",
        },
    ]

    # Step 9: stronger judge model
    judge_response = completion(model=JUDGE_MODEL, messages=judge_messages, response_format=AnswerEval)
    answer_eval = AnswerEval.model_validate_json(judge_response.choices[0].message.content)

    return answer_eval, generated_answer, retrieved_docs, outcome_correct


def evaluate_all_retrieval():
    """Evaluate retrieval for every test except band."""
    tests = load_tests()
    total_tests = len(tests)
    for index, test in enumerate(tests):
        if test.gate == "band":
            continue
        result = evaluate_retrieval(test)
        progress = (index + 1) / total_tests
        yield test, result, progress


def evaluate_all_answers():
    """Evaluate all answers, running several tests at the same time."""
    tests = load_tests()
    total_tests = len(tests)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(evaluate_answer, test): test for test in tests}
        for done, future in enumerate(as_completed(futures), start=1):
            test = futures[future]
            answer_eval, _, _, outcome_correct = future.result()
            yield test, answer_eval, outcome_correct, done / total_tests



def run_cli_evaluation(test_number: int):
    """Run retrieval and answer evaluation for one test and print the results."""
    tests = load_tests()

    if test_number < 0 or test_number >= len(tests):
        print(f"Error: test_row_number must be between 0 and {len(tests) - 1}")
        sys.exit(1)

    test = tests[test_number]

    print(f"\n{'=' * 80}")
    print(f"Test #{test_number} ({test.id})")
    print(f"{'=' * 80}")
    print(f"Gate: {test.gate}")
    print(f"Category: {test.category}")
    print(f"Facts:\n{test.facts}")
    print(f"Keywords: {test.keywords}")
    print(f"Expected Verdict: {test.expected_outcome}")
    print(f"Reference Answer: {test.reference_answer}")

    print(f"\n{'=' * 80}")
    print("Retrieval Evaluation")
    print(f"{'=' * 80}")

    if test.gate == "band":
        print("Skipped: band uses the full band law, not retrieval")
    else:
        retrieval_result = evaluate_retrieval(test)
        print(f"MRR: {retrieval_result.mrr:.4f}")
        print(f"nDCG: {retrieval_result.ndcg:.4f}")
        print(f"Keywords Found: {retrieval_result.keywords_found}/{retrieval_result.total_keywords}")
        print(f"Keyword Coverage: {retrieval_result.keyword_coverage:.1f}%")

    print(f"\n{'=' * 80}")
    print("Answer Evaluation")
    print(f"{'=' * 80}")

    answer_result, generated_answer, retrieved_docs, outcome_correct = evaluate_answer(test)

    print(f"\nGenerated Answer:\n{generated_answer}")
    print(f"\nVerdict Correct: {outcome_correct}")
    print(f"\nFeedback:\n{answer_result.feedback}")
    print("\nScores:")
    print(f"  Accuracy: {answer_result.accuracy:.2f}/5")
    print(f"  Completeness: {answer_result.completeness:.2f}/5")
    print(f"  Relevance: {answer_result.relevance:.2f}/5")
    print(f"\n{'=' * 80}\n")

def main():
    """CLI to evaluate a specific test by row number."""
    if len(sys.argv) != 2:
        print("Usage: python -m evaluation.eval <test_row_number>")
        sys.exit(1)

    try:
        test_number = int(sys.argv[1])
    except ValueError:
        print("Error: test_row_number must be an integer")
        sys.exit(1)

    run_cli_evaluation(test_number)


if __name__ == "__main__":
    main()
