"""Gradio interface for the employment status analysis tool."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import os
import json
import prompts
from textwrap import dedent
from assessment import *
import examples
import gradio as gr
import styles





def single_assess(
    substitution_clause,
    substitution_fettered,
    substitution_attempted,
    substitute_payment,
    decides_what_work_and_what_order,
    decides_how_work_performed,
    hours_and_location_set,
    report_to_a_manager,
    clients_last_12_months,
    own_trading_name,
    own_insurance,
    own_vat,
    defective_work_corrected,
    loss_on_engagement,
    who_provide_equipment,
    presented_as_part_of_organisation,
    staff_benefits_training_management,
    total_engagement_length,
    extension_count,
    exclusivity_clause,
    practical_bar,
    paid_for_time_or_completion,
):
    """Assess one engagement from the form. Yields a loading message, then the result. Parameter order must match the inputs list below."""
    # Dropdown text → Optional[bool]; "no clause" means no substitution right exists
    fettered_map = {"no clause": None, "yes": True, "no": False}
    yield "### ⏳ Assessing…\n\nThis usually takes about ten seconds."
    # Build an Engagement from form values; numbers arrive as floats, dropdowns as strings
    e = Engagement(
        engagement_id="Manual entry",
        substitution_clause=substitution_clause,
        substitution_attempted=substitution_attempted,
        substitute_payment=SubPaymentEnum(substitute_payment),
        decides_what_work_and_what_order=decides_what_work_and_what_order,
        decides_how_work_performed=decides_how_work_performed,
        hours_and_location_set=hours_and_location_set,
        report_to_a_manager=report_to_a_manager,
        clients_last_12_months=int(clients_last_12_months),
        own_trading_name=own_trading_name,
        own_insurance=own_insurance,
        own_vat=own_vat,
        defective_work_corrected=defective_work_corrected,
        loss_on_engagement=loss_on_engagement,
        who_provide_equipment=EquipmentProvider(who_provide_equipment),
        presented_as_part_of_organisation=presented_as_part_of_organisation,
        staff_benefits_training_management=staff_benefits_training_management,
        total_engagement_length=int(total_engagement_length),
        extension_count=int(extension_count),
        exclusivity_clause=exclusivity_clause,
        practical_bar=practical_bar,
        paid_for_time_or_completion=PaidForTimeOrCompletionEnum(paid_for_time_or_completion),
        substitution_fettered=fettered_map[substitution_fettered],
    )
    yield format_assessment(run(e))

def batch_assess(file):
    """Assess every engagement in an uploaded CSV, streaming each result as it completes."""
    yield "### ⏳ Assessing…\n\nThis usually takes about ten seconds."
    engagements = load_engagements(file)
    text = ""
    for e in engagements:
        a = run(e)
        text += f"### {e.engagement_id}\n\n"
        text += format_assessment(a)
        text += "\n\n---\n\n"
        yield text


with gr.Blocks(
    title="Employment status analysis") as ui: 
    gr.Markdown("# Employment status analysis")

    with gr.Tab("Batch"):
        file_in = gr.File(label="Upload your enagagements CSV", type="filepath")
        with gr.Accordion("Example datasheets:", open=False):
            gr.Examples(
                examples=[["dataset_example_5.csv"], ["dataset_example_3.csv"]],
                inputs=file_in,
                example_labels = ["Dataset 1", "Dataset 2"]
                )
        go_batch = gr.Button("Assess", variant="primary")
        out_batch = gr.Markdown("Upload your CSV and press Assess")
        go_batch.click(batch_assess, inputs=file_in, outputs=out_batch)
    
    with gr.Tab("Single engagement"):
        gr.Markdown("### Personal service\n *Example are at the bottom of this form* ")
        w_clause = gr.Checkbox(label="Contract contains a right of substitution")
        w_fettered = gr.Dropdown(["no clause", "yes", "no"], value="no clause", label="Is that right fettered?")
        w_attempted = gr.Textbox(lines=2, label="Substitution in practice")
        w_subpay = gr.Dropdown(["client", "worker", "unspecified"], value="unspecified", label="Who would pay a substitute")

        gr.Markdown("### Control")
        w_what = gr.Textbox(lines=2, label="Who decides what work and in what order")
        w_how = gr.Textbox(lines=2, label="Who decides how the work is performed")
        w_hours = gr.Textbox(lines=2, label="How hours and location are set")
        w_manager = gr.Textbox(lines=2, label="Reporting line")

        gr.Markdown("### In business on own account")
        w_clients = gr.Number(value=0, label="Other clients in last 12 months")
        w_trading = gr.Checkbox(label="Own trading name")
        w_insurance = gr.Checkbox(label="Own insurance")
        w_vat = gr.Checkbox(label="VAT registered")

        gr.Markdown("### Financial risk")
        w_defects = gr.Textbox(lines=2, label="Who bears the cost of correcting defective work")
        w_loss = gr.Textbox(lines=2, label="Can the worker make a loss")

        gr.Markdown("### Equipment")
        w_equipment = gr.Dropdown(["client", "worker", "mixed"], value="client", label="Who provides the main equipment")

        gr.Markdown("### Integration")
        w_presented = gr.Textbox(lines=2, label="How the worker is presented")
        w_benefits = gr.Textbox(lines=2, label="Benefits, training, supervision")

        gr.Markdown("### Exclusivity and duration")
        w_length = gr.Number(value=0, label="Total engagement length (months)")
        w_extensions = gr.Number(value=0, label="Number of extensions")
        w_exclusivity = gr.Checkbox(label="Exclusivity clause")
        w_bar = gr.Textbox(lines=2, label="Practical bar on other work")

        gr.Markdown("### Payment")
        w_payment = gr.Dropdown(["time", "completion", "both"], value="time", label="Paid for time or completion")

        with gr.Accordion("Example inputs filled in:", open=False):
            gr.Examples(
                examples=examples.single_examples,
                inputs=[
                    w_clause, w_fettered, w_attempted, w_subpay,
                    w_what, w_how, w_hours, w_manager,
                    w_clients, w_trading, w_insurance, w_vat,
                    w_defects, w_loss,
                    w_equipment,
                    w_presented, w_benefits,
                    w_length, w_extensions, w_exclusivity, w_bar,
                    w_payment,
                ],
                example_labels = ["Example 1", "Example 2"]
            )

        go_single = gr.Button("Assess", variant="primary")
        out_single = gr.Markdown()

        go_single.click(
            single_assess,
            inputs=[
                w_clause, w_fettered, w_attempted, w_subpay,
                w_what, w_how, w_hours, w_manager,
                w_clients, w_trading, w_insurance, w_vat,
                w_defects, w_loss,
                w_equipment,
                w_presented, w_benefits,
                w_length, w_extensions, w_exclusivity, w_bar,
                w_payment,
            ],
            outputs=out_single,
        )

if __name__ == "__main__":
    ui.launch(share=True, inbrowser=True, theme=styles.THEME, css=styles.CSS)
