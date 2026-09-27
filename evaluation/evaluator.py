import gradio as gr
import pandas as pd
from collections import defaultdict
from dotenv import load_dotenv

from evaluation.eval import evaluate_all_retrieval, evaluate_all_answers

load_dotenv(override=True)

# Gates skipped in the retrieval evaluation.
# Band is sent the whole band law, so there is no retrieval to measure.
SKIP_RETRIEVAL_GATES = {"band"}

# Color coding thresholds - Retrieval
MRR_GREEN = 0.9
MRR_AMBER = 0.75
NDCG_GREEN = 0.9
NDCG_AMBER = 0.75
COVERAGE_GREEN = 90.0
COVERAGE_AMBER = 75.0

# Color coding thresholds - Answer (1-5 scale)
ANSWER_GREEN = 4.5
ANSWER_AMBER = 4.0

# Color coding thresholds - Verdict accuracy (%)
VERDICT_GREEN = 90.0
VERDICT_AMBER = 75.0

# Colours that read well on a dark background
GREEN = "#4ade80"
AMBER = "#fbbf24"
RED = "#f87171"


def pick_color(value: float, green: float, amber: float) -> str:
    """Return green, amber or red depending on which threshold the value reaches."""
    if value >= green:
        return GREEN
    elif value >= amber:
        return AMBER
    return RED


def get_color(value: float, metric_type: str) -> str:
    """Get color based on metric value and type."""
    if metric_type == "mrr":
        return pick_color(value, MRR_GREEN, MRR_AMBER)
    elif metric_type == "ndcg":
        return pick_color(value, NDCG_GREEN, NDCG_AMBER)
    elif metric_type == "coverage":
        return pick_color(value, COVERAGE_GREEN, COVERAGE_AMBER)
    elif metric_type == "verdict":
        return pick_color(value, VERDICT_GREEN, VERDICT_AMBER)
    elif metric_type in ["accuracy", "completeness", "relevance"]:
        return pick_color(value, ANSWER_GREEN, ANSWER_AMBER)
    return "#e5e7eb"


def format_metric_html(
    label: str,
    value: float,
    metric_type: str,
    is_percentage: bool = False,
    score_format: bool = False,
) -> str:
    """Format a metric card with color coding (dark-mode friendly)."""
    color = get_color(value, metric_type)
    if is_percentage:
        value_str = f"{value:.1f}%"
    elif score_format:
        value_str = f"{value:.2f}/5"
    else:
        value_str = f"{value:.4f}"
    return f"""
    <div style="margin: 10px 0; padding: 15px; background-color: rgba(255,255,255,0.05); border-radius: 8px; border-left: 5px solid {color};">
        <div style="font-size: 14px; color: #aaa; margin-bottom: 5px;">{label}</div>
        <div style="font-size: 28px; font-weight: bold; color: {color};">{value_str}</div>
    </div>
    """


def complete_banner(text: str) -> str:
    """Green 'evaluation complete' banner (dark-mode friendly)."""
    return f"""
    <div style="margin-top: 20px; padding: 10px; background-color: rgba(40,167,69,0.15); border-radius: 5px; text-align: center; border: 1px solid rgba(40,167,69,0.4);">
        <span style="font-size: 14px; color: #6fdc8c; font-weight: bold;">✓ {text}</span>
    </div>
    """


def run_retrieval_evaluation(progress=gr.Progress()):
    """Run retrieval evaluation for every gate except band."""
    total_mrr = 0.0
    total_ndcg = 0.0
    total_coverage = 0.0
    gate_mrr = defaultdict(list)
    count = 0

    for test, result, prog_value in evaluate_all_retrieval():
        progress(prog_value, desc=f"Evaluating {test.id}...")

        if test.gate in SKIP_RETRIEVAL_GATES:
            continue

        count += 1
        total_mrr += result.mrr
        total_ndcg += result.ndcg
        total_coverage += result.keyword_coverage

        gate_mrr[test.gate].append(result.mrr)

    if count == 0:
        return "<div style='padding: 20px; color: #f87171;'>No tests were evaluated.</div>", pd.DataFrame()

    avg_mrr = total_mrr / count
    avg_ndcg = total_ndcg / count
    avg_coverage = total_coverage / count

    final_html = f"""
    <div style="padding: 0;">
        {format_metric_html("Mean Reciprocal Rank (MRR)", avg_mrr, "mrr")}
        {format_metric_html("Normalized DCG (nDCG)", avg_ndcg, "ndcg")}
        {format_metric_html("Keyword Coverage", avg_coverage, "coverage", is_percentage=True)}
        {complete_banner(f"Evaluation Complete: {count} tests (band excluded)")}
    </div>
    """

    gate_data = []
    for gate, mrr_scores in gate_mrr.items():
        gate_data.append({"Gate": gate, "Average MRR": sum(mrr_scores) / len(mrr_scores)})

    df = pd.DataFrame(gate_data)

    return final_html, df


def run_answer_evaluation(progress=gr.Progress()):
    """Run answer evaluation for every test, including band."""
    total_accuracy = 0.0
    total_completeness = 0.0
    total_relevance = 0.0
    total_correct = 0
    gate_accuracy = defaultdict(list)
    count = 0

    for test, result, outcome_correct, prog_value in evaluate_all_answers():
        count += 1
        total_accuracy += result.accuracy
        total_completeness += result.completeness
        total_relevance += result.relevance
        if outcome_correct:
            total_correct += 1

        gate_accuracy[test.gate].append(result.accuracy)

        progress(prog_value, desc=f"Evaluating {test.id}...")

    if count == 0:
        return "<div style='padding: 20px; color: #f87171;'>No tests were evaluated.</div>", pd.DataFrame()

    avg_accuracy = total_accuracy / count
    avg_completeness = total_completeness / count
    avg_relevance = total_relevance / count
    verdict_accuracy = total_correct / count * 100

    final_html = f"""
    <div style="padding: 0;">
        {format_metric_html("Verdict Accuracy", verdict_accuracy, "verdict", is_percentage=True)}
        {format_metric_html("Accuracy", avg_accuracy, "accuracy", score_format=True)}
        {format_metric_html("Completeness", avg_completeness, "completeness", score_format=True)}
        {format_metric_html("Relevance", avg_relevance, "relevance", score_format=True)}
        {complete_banner(f"Evaluation Complete: {count} tests ({total_correct} correct verdicts)")}
    </div>
    """

    gate_data = []
    for gate, accuracy_scores in gate_accuracy.items():
        gate_data.append({"Gate": gate, "Average Accuracy": sum(accuracy_scores) / len(accuracy_scores)})

    df = pd.DataFrame(gate_data)

    return final_html, df


def main():
    """Launch the Gradio evaluation app."""
    theme = gr.themes.Soft(font=["Inter", "system-ui", "sans-serif"])

    placeholder = "<div style='padding: 20px; text-align: center; color: #999;'>Click 'Run Evaluation' to start</div>"

    with gr.Blocks(title="RAG Evaluation Dashboard") as app:
        gr.Markdown("# 📊 RAG Evaluation Dashboard")
        gr.Markdown("Evaluate retrieval and answer quality for the Employment Status RAG system")

        # RETRIEVAL SECTION
        gr.Markdown("## 🔍 Retrieval Evaluation")
        gr.Markdown("Personal service, control, financial and organisation. Band is excluded because it is sent the full band law.")

        retrieval_button = gr.Button("Run Evaluation", variant="primary", size="lg")

        with gr.Row():
            with gr.Column(scale=1):
                retrieval_metrics = gr.HTML(placeholder)

            with gr.Column(scale=1):
                retrieval_chart = gr.BarPlot(
                    x="Gate",
                    y="Average MRR",
                    title="Average MRR by Gate",
                    y_lim=[0, 1],
                    height=400,
                )

        # ANSWERING SECTION
        gr.Markdown("## 💬 Answer Evaluation")
        gr.Markdown("All 100 tests. Takes around 7 to 8 minutes.")

        answer_button = gr.Button("Run Evaluation", variant="primary", size="lg")

        with gr.Row():
            with gr.Column(scale=1):
                answer_metrics = gr.HTML(placeholder)

            with gr.Column(scale=1):
                answer_chart = gr.BarPlot(
                    x="Gate",
                    y="Average Accuracy",
                    title="Average Accuracy by Gate",
                    y_lim=[1, 5],
                    height=400,
                )

        # Wire up the evaluations
        retrieval_button.click(
            fn=run_retrieval_evaluation,
            outputs=[retrieval_metrics, retrieval_chart],
        )

        answer_button.click(
            fn=run_answer_evaluation,
            outputs=[answer_metrics, answer_chart],
        )

    app.launch(inbrowser=True, theme=theme)


if __name__ == "__main__":
    main()