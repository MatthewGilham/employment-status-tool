# Employment Status Analysis Tool

An AI-assisted tool that analyses whether a working arrangement looks like employment or self-employment, using the tests UK courts apply in employment status and IR35 cases.

It takes the facts of an engagement, runs them through a structured legal framework, and returns a banded conclusion together with factor-by-factor reasoning and any conflicts between what the contract says and what happens in practice.

The legal content each AI call relies on is selected by retrieval (RAG), and the AI-assessed parts are measured by an evaluation suite of 80 test cases.

> **This is a demonstration project, not legal or tax advice.** Real status determinations need professional judgement on the full facts. All test data is synthetic.

---

## Why I built it

Employment status is a judgement, not a calculation. In *Lee Ting Sang v Chung Chi-Keung* [1990], the court warned against applying a mechanical test, and HMRC's own CEST tool has been criticised for returning "undetermined" on hard cases.

I wanted to see whether an LLM could help with the part that needs reading and interpretation, while the structure of the legal test stayed explicit, rule-based and explainable.

I later added retrieval and an evaluation suite, for two reasons: to learn how RAG works by building it mostly by hand, and to replace "I reviewed the outputs and they looked sensible" with measured results.

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

| Factor                     | Assessed by |
| -------------------------- | ----------- |
| In business on own account | Rules       |
| Equipment                  | Rules       |
| Exclusivity and duration   | Rules       |
| Payment basis              | Rules       |
| Financial risk             | LLM + RAG   |
| Integration                | LLM + RAG   |

Each factor returns a **direction** (employment / self-employment / neutral), a **strength** (strong / moderate / weak), the **evidence** it relied on, and whether there was enough information to assess it.

**The band.** The six results are combined into one of five bands:

> Strong employment · Likely employment · Borderline · Likely not employment · Strong not employment

The band sits above the analysis rather than replacing it. The factor-by-factor reasoning is always shown.

---

## Retrieval (RAG)

Each LLM call needs the relevant law in its prompt. Originally, every call received the whole legal text for its topic. Now each call receives only the passages most relevant to the facts of the engagement in front of it.

```
Legal text for each topic        (law_content.py)
        │  split into chunks of about 3,000 characters
        ▼
Embeddings                       (text-embedding-3-small)
        │  stored with the topic each chunk belongs to
        ▼
Vector database                  (Chroma, saved in law_db/)

At assessment time:
Facts of the engagement  →  search within the one relevant topic
                         →  top 4 passages + the core rule  →  into the prompt
```

**What is indexed.** Four bodies of legal text, one per LLM-assessed topic: personal service, control, financial risk and integration. Each chunk is tagged with its topic.

**How retrieval works.** The engagement's facts are embedded and used as the search query. The search is filtered to the topic being assessed, so the control call can never be handed law about substitution. The four closest passages are returned.

**The core rule is always included.** The first chunk of each topic states the legal test itself. It is pinned to the top of the retrieved passages every time, whatever the search returns. Without this, a search on unusual facts could return four passages of detailed case law and leave the model without the basic rule it is meant to apply.

**The band call does not use retrieval.** Forming the overall conclusion needs the full guidance on weighing factors, so that call still receives the complete text.

**Built mostly by hand.** Embedding, storage, filtering and retrieval are written directly against the OpenAI-compatible API and Chroma. LangChain is used only to split the text into chunks.

---

## Evaluation

The evaluation suite measures two things separately: whether the right law is retrieved, and whether the assessment that follows is correct.

**The test set.** 80 synthetic test cases in `evaluation/tests.jsonl`, covering the four LLM-assessed topics: personal service, control, financial risk and integration. Each one has the facts of an engagement, the topic it tests, the expected verdict, a reference answer, and keywords that should appear in the retrieved law. Cases fall into three categories:

- **direct:** facts stated in legal terms
- **lay_language:** the same kinds of facts described the way a non-lawyer would
- **contract_vs_practice:** the contract says one thing and the working practice another

**Retrieval evaluation.** For each test, the facts are run through retrieval and scored on:

| Metric           | What it measures                                                    |
| ---------------- | ------------------------------------------------------------------- |
| MRR              | How near the top the first relevant passage appears                 |
| nDCG             | How well all the relevant passages are ranked                       |
| Keyword coverage | Share of the expected keywords found anywhere in the retrieved text |

The pinned core rule is switched off for this evaluation, so the scores reflect the search itself and are not flattered by a passage that is always included.

**Answer evaluation.** Each test is run through the real prompt for its topic at temperature 0, then checked in two ways:

1. **Verdict accuracy, checked in code.** The verdict is read from the model's structured output and compared with the expected verdict. No AI is involved in this check.
2. **Reasoning quality, scored by a judge model.** A second, stronger model compares the answer with the reference answer and scores accuracy, completeness and relevance from 1 to 5. If the verdict is wrong, accuracy is fixed at 1, so fluent reasoning cannot rescue a wrong conclusion.

**The dashboard.** A Gradio app shows the scores with colour coding and a chart of results by topic. A single test can also be run from the command line to inspect its retrieved passages, answer and feedback.

### Results

Latest run, 80 tests:

| Measure                      | Result            |
| ---------------------------- | ----------------- |
| Retrieval: MRR               | 0.77              |
| Retrieval: nDCG              | 0.81              |
| Retrieval: keyword coverage  | 96.9%             |
| Verdict accuracy             | 93.8% (75 of 80)  |
| Judge: accuracy              | 4.89 / 5          |
| Judge: completeness          | 4.64 / 5          |
| Judge: relevance             | 5.00 / 5          |

By topic, retrieval is strongest on integration and control (MRR of roughly 0.9 and 0.86) and weakest on financial risk (roughly 0.6). Answer accuracy is 5.00 on control and financial risk, and slightly lower on integration and personal service.

Two things stand out. Keyword coverage is high while MRR is lower, which means the right law is nearly always retrieved but is not always ranked first. And the assessments stay accurate on financial risk despite its weaker ranking, because the relevant passage is still among the four retrieved and the core rule is always pinned in.

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

**Retrieval is filtered by topic, with the rule pinned.**
Searching the whole legal text for every call would let law from one topic leak into another. Filtering by topic keeps each call narrow, and pinning the core rule guarantees the model always has the test it is applying.

**Verdicts are checked in code, reasoning by a judge.**
Whether a verdict matches the expected one is a fact, so it is checked without AI. Whether the reasoning is sound is a judgement, so a second model scores it. Keeping the two apart means the headline accuracy figure does not depend on another model's opinion.

---

## What testing showed

**Contradiction detection initially failed.** The model correctly *identified* sham substitution clauses but still failed the gate, treating the clause as genuine. The prompt told the model to record contradictions but never said what a contradiction meant for the outcome. After I added an explicit rule that practice governs over the contract, the affected cases flipped to the correct result.

**Consistency.** At temperature 0, clear-cut engagements returned identical results across five repeated runs. A genuinely marginal case (an unfettered substitution clause that had never been used) varied at Gate 1 in one run out of five, but produced the same final outcome each time. Instability appeared where the law itself is uncertain, not on clear cases.

**Model choice.** Across the 22-engagement test set: Gemini 3.5 Flash Lite completed in about 54 seconds, GPT-5.6 Luna in about 3 minutes 10 seconds, and DeepSeek was too slow for batch use. I chose Gemini for speed.

**Chunking mattered more than anything else in retrieval.** With my first chunking approach, retrieval scores were in the 0.50s. Switching to a recursive text splitter with larger chunks (about 3,000 characters), which splits on paragraph and sentence boundaries and keeps each legal point with its supporting cases, raised MRR to 0.77 and keyword coverage to 96.9%. The law text and the embedding model were unchanged; only the way the text was cut up was different.

**Embedding model choice.** I compared four embedding models on the retrieval evaluation: OpenAI's text-embedding-3-small and text-embedding-3-large, Voyage 4 Large and Gemini Embedding 2. The small OpenAI model gave the best results for its price, so the tool uses it.

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
OPENAI_API_KEY=your-key-here
```

The OpenRouter key is used for the assessments and the embeddings. The OpenAI key is used by the judge model in the evaluation.

Build the vector database once (and again whenever `law_content.py` changes):

```bash
python -m rag.ingest
```

Then run the app:

```bash
python app.py
```

### Running the evaluation

```bash
python -m evaluation.evaluator     # dashboard: retrieval and answer scores
python -m evaluation.eval 12       # one test in detail (here, test number 12)
```

The full answer evaluation runs all 80 tests and takes several minutes.

---

## Project structure

| File                      | Purpose                                                                   |
| ------------------------- | ------------------------------------------------------------------------- |
| `app.py`                  | Gradio interface                                                          |
| `assessment.py`           | Data model, rule-based factors, LLM calls, pipeline and output formatting |
| `prompts.py`              | System prompts for each LLM call                                          |
| `law_content.py`          | Legal content that is indexed for retrieval                               |
| `examples.py`             | Worked examples for the single-engagement form                            |
| `styles.py`               | Theme and styling for the interface                                       |
| `rag/ingest.py`           | Splits the legal content, embeds it and builds the vector database        |
| `rag/retrival.py`         | Retrieves the relevant law for a set of facts, filtered by topic          |
| `evaluation/tests.jsonl`  | 80 synthetic test cases with expected verdicts and reference answers      |
| `evaluation/test.py`      | Loads and validates the test cases                                        |
| `evaluation/eval.py`      | Retrieval metrics, answer evaluation and the judge model                  |
| `evaluation/evaluator.py` | Evaluation dashboard                                                      |
| `*.csv`                   | Synthetic engagement data                                                 |

---

## Limitations

- **Synthetic data.** The test engagements and evaluation cases were generated and are more internally consistent than real cases. I added hand-written edge cases to test contradiction handling.
- **No expert-labelled ground truth.** The expected verdicts and reference answers in the evaluation set were written for this project, not by a practitioner. The scores measure agreement with those answers, not correctness as a tribunal would decide it.
- **RAG is not strictly needed at this size.** The legal text is small enough to fit in a prompt. I added retrieval to learn the technique and to give each call a narrower, more relevant slice of law, not because the text would not fit. The retrieval version has known imperfections that I have left in place.
- **Keyword-based retrieval scoring.** A retrieved passage counts as relevant if it contains the expected keywords. This is simple and repeatable, but it can miss a relevant passage that uses different wording.
- **The band conclusion is not in the evaluation set.** The 80 tests cover the four LLM-assessed topics. The final band, which combines all the factors, is not yet measured.
- **Ranking has room to improve.** The right law is almost always retrieved, but an MRR of 0.77 shows it is not always placed first, most noticeably for financial risk.
- **The judge is a model.** Scores for reasoning quality come from a second LLM and carry its own inconsistencies. Verdict accuracy does not depend on it.
- **Thresholds are judgement calls.** The cut-offs in the rule-based factors (for example, more than 3 clients or more than 18 months) were chosen after looking at the data distribution and are not taken from law.
- **Not applied uniformly on every edge case.** Engagements with similar substitution facts were occasionally treated differently depending on wording. Refining the Gate 1 prompt further is an open item.
- **Scope.** The tool assesses the hypothetical contract between worker and client. It does not model the off-payroll rules' allocation of responsibility or liability, and it is not a substitute for a Status Determination Statement.

---

## Built with

Python · Gradio · OpenRouter · Chroma · LangChain text splitters · LiteLLM · Pydantic · pandas