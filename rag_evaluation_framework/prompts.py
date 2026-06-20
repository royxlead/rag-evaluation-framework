"""Prompts used for LLM-based metric evaluations.

All prompts are defined here so users can override them.
"""

# ── Faithfulness ──────────────────────────────────────────────

FAITHFULNESS_DECOMPOSE_PROMPT = (
"You are an expert at analyzing text. Given an answer, "
"decompose it into a list of atomic factual claims. "
"Each claim should be a single, verifiable fact.\n"
"\n"
"Answer: {answer}\n"
"\n"
"Return a JSON list of strings. Example:\n"
'["Paris is the capital of France.", '
'"France is in Western Europe."]'
)

FAITHFULNESS_VERIFY_PROMPT = (
"You are a fact-checking expert. "
"Determine if each claim is ENTAILED by "
"(directly supported by) the provided context.\n"
"\n"
"Context:\n{context}\n"
"\n"
"Claim: {claim}\n"
"\n"
"Respond with EXACTLY one word: SUPPORTED or NOT_SUPPORTED"
)

# ── Hallucination ─────────────────────────────────────────────

HALLUCINATION_VERIFY_PROMPT = (
"You are a fact-checking expert. "
"For the given claim extracted from an LLM answer, determine:\n"
"\n"
"1. Is it GROUNDED (directly supported by the context)?\n"
"2. Is it a FACTUAL claim (makes a verifiable statement about the world)?\n"
"\n"
"Context:\n{context}\n"
"\n"
"Claim: {claim}\n"
"\n"
"Respond in JSON format:\n"
'{{"grounded": true/false, "factual": true/false, '
'"reason": "..."}}'
)

# ── Answer Relevance ──────────────────────────────────────────

ANSWER_RELEVANCE_PROMPT = (
"You are evaluating how relevant an answer is to a question.\n"
"\n"
"Question: {question}\n"
"Answer: {answer}\n"
"\n"
"On a scale of 0.0 to 1.0, rate how well this answer "
"addresses the question. Consider:\n"
"- Does it directly answer what was asked?\n"
"- Does it provide relevant information?\n"
"- Is it on-topic?\n"
"\n"
"Respond with ONLY a number between 0.0 and 1.0."
)

# ── Context Coverage ──────────────────────────────────────────

CONTEXT_COVERAGE_PROMPT = (
"You are evaluating how well an answer covers the information "
"available in the provided context.\n"
"\n"
"Context:\n{context}\n"
"\n"
"Answer: {answer}\n"
"\n"
"On a scale of 0.0 to 1.0, rate what fraction of the relevant "
"information from the context is reflected in the answer. Consider:\n"
"- Did the answer use all relevant facts from the context?\n"
"- Did it miss important information?\n"
"- Did it add information not in the context?\n"
"\n"
"Respond with ONLY a number between 0.0 and 1.0."
)

# ── UCM ───────────────────────────────────────────────────────

UCM_CLAIM_EXTRACTION_PROMPT = (
"Given the following text, extract all atomic factual claims "
"as a JSON array of strings.\n"
"\n"
"Text: {text}\n"
"\n"
"Return ONLY a valid JSON array of strings, like: "
'["claim 1", "claim 2", ...]'
)

# ── Score Calculation ─────────────────────────────────────────

SCORE_EXPLANATION_PROMPT = (
"Given the following evaluation context, "
"provide a brief explanation of the score.\n"
"\n"
"Question: {question}\n"
"Context: {context}\n"
"Answer: {answer}\n"
"Score: {score}\n"
"Metric: {metric_name}\n"
"\n"
"Provide a 1-2 sentence explanation of why this score was assigned."
)
