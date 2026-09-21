# Employment Status Analysis Tool

An AI-assisted tool that analyses whether a working arrangement looks like employment or self-employment, using the tests UK courts apply in employment status and IR35 cases.

It takes the facts of an engagement, runs them through a structured legal framework, and returns a banded conclusion together with factor-by-factor reasoning and any conflicts between what the contract says and what happens in practice.

> **This is a demonstration project, not legal or tax advice.** Real status determinations need professional judgement on the full facts. All test data is synthetic.

---

## Why I built it

Employment status is a judgement, not a calculation. In *Lee Ting Sang v Chung Chi-Keung* [1990], the court warned against applying a mechanical test, and HMRC's own CEST tool has been criticised for returning "undetermined" on hard cases.

I wanted to see whether an LLM could help with the part that needs reading and interpretation, while the structure of the legal test stayed explicit, rule-based and explainable.

---

## How it works

The framework follows *Ready Mixed Concrete v Minister of Pensions* [1968]:

```
Gate 1: Personal service  →  fail → Not employment (analysis stops)
Gate 2: Control           →  fail → Not employment (analysis stops)
Condition 3: six factors  →  banded conclusion
```

**The gates.** Personal service (including whether a right of substitution is genuine) and control are assessed first. If either fails, there can be no contract of service, so the analysis stops. A gate can also return *unclear*, in which case the analysis continues and the uncertainty is shown in the output.

**The six factors** (drawing on *Market Investigations v Minister of Social Security* [1969]):

| Factor | Assessed by |
|---|---|
| In business on own account | Rules |
| Equipment | Rules |
| Exclusivity and duration | Rules |
| Payment basis | Rules |
| Financial risk | LLM |
| Integration | LLM |

Each factor returns a **direction** (employment / self-employment / neutral), a **strength** (strong / moderate / weak), the **evidence** it relied on, and whether there was enough information to assess it.

**The band.** The six results are combined into one of five bands:

> Strong employment · Likely employment · Borderline · Likely not employment · Strong not employment

The band sits above the analysis rather than replacing it. The factor-by-factor reasoning is always shown.

---

## Key design decisions

**The model reads evidence; the code routes and combines.**
Closed facts (who provides equipment, how payment is structured, number of clients) are handled by plain Python rules, so they always produce the same answer. The model is only used where interpreting free text needs judgement: the two gates, financial risk and integration. Each LLM call answers one narrow question with its own prompt and relevant law, instead of the model being asked for a single overall verdict.

**Contract vs practice.**
The law looks at what actually happens, not just what the paperwork says. For personal service, the model flags where the two diverge. For example, a contract grants a right of substitution but the client refused a substitute when one was offered. Where the practice shows the right is not genuine, the gate treats personal service as satisfied.

**Borderline is a real outcome.**
Mixed engagements should land in the middle band instead of being forced into a verdict. A tool that says a case is genuinely borderline is more honest than one that always picks a side.

**No percentage score.**
A percentage implies precision the law does not support, and requires weighting factors against each other in a way the case law resists. The bands express the same gradation without false precision. Following *Hall v Lorimer* [1994], the band guidance frames the exercise as forming an overall picture, not adding up a tally.

---

## What testing showed

**Contradiction detection initially failed.** The model correctly *identified* sham substitution clauses but still failed the gate, treating the clause as genuine. The prompt told the model to record contradictions but never said what a contradiction meant for the outcome. After I added an explicit rule that practice governs over the contract, the affected cases flipped to the correct result.

**Consistency.** At temperature 0, clear-cut engagements returned identical results across five repeated runs. A genuinely marginal case (an unfettered substitution clause that had never been used) varied at Gate 1 in one run out of five, but produced the same final outcome each time. Instability appeared where the law itself is uncertain, not on clear cases.

**Model choice.** Across the 22-engagement test set: Gemini 3.5 Flash Lite completed in about 54 seconds, GPT-5.6 Luna in about 3 minutes 10 seconds, and DeepSeek was too slow for batch use. I chose Gemini for speed.

**Reliability.** Every LLM call retries up to three times. If a response still can't be parsed, the tool degrades to a safe result (unclear gate, insufficient factor, or borderline band) instead of crashing the batch.

---

## Using the app

Two tabs:

- **Batch**: upload a CSV of engagements and get an assessment for each. An example file is included.
- **Single engagement**: fill in a form for one engagement. Worked examples can be loaded with one click.

Results stream in as each engagement completes.

### Running locally

```bash
git clone https://github.com/MatthewGilham/employment-status-tool.git
cd employment-status-tool
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project folder:

```
OPENROUTER_API_KEY=your-key-here
```

Then run from the project folder:

```bash
python app.py
```

---

## Project structure

| File | Purpose |
|---|---|
| `app.py` | Gradio interface |
| `assessment.py` | Data model, rule-based factors, LLM calls, pipeline and output formatting |
| `prompts.py` | System prompts for each LLM call |
| `law_content.py` | Legal content used within the prompts |
| `examples.py` | Worked examples for the single-engagement form |
| `*.csv` | Synthetic engagement data |

---

## Limitations

- **Synthetic data.** The test engagements were generated and are more internally consistent than real cases. I added hand-written edge cases to test contradiction handling, but the set is small.
- **No labelled ground truth.** I judged outputs by reviewing them, not by measuring them against expert-labelled answers, so this demonstrates sensible behaviour, not measured accuracy.
- **Thresholds are judgement calls.** The cut-offs in the rule-based factors (for example, more than 3 clients or more than 18 months) were chosen after looking at the data distribution and are not taken from law.
- **Not applied uniformly on every edge case.** Engagements with similar substitution facts were occasionally treated differently depending on wording. Refining the Gate 1 prompt further is an open item.
- **Scope.** The tool assesses the hypothetical contract between worker and client. It does not model the off-payroll rules' allocation of responsibility or liability, and it is not a substitute for a Status Determination Statement.

---

## Built with

Python · Gradio · OpenRouter · pandas