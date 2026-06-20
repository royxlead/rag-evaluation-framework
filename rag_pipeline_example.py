"""
RAG Evaluation Framework Real-World RAG Pipeline Evaluation Example
====================================================================

This script demonstrates how to evaluate a REAL RAG pipeline using RAG Evaluation Framework.

It shows:
    1. How to FETCH content from a real web page or PDF
    2. How to chunk it into a knowledge base
    3. How your retriever fetches relevant chunks for a user's question
    4. How your LLM generates an answer from those chunks
    5. How RAG Evaluation Framework evaluates the quality of the entire pipeline

Prerequisites:
    pip install rag-evaluation-framework httpx beautifulsoup4

    Set your API key:
        set OPENAI_API_KEY=sk-... (Windows)
        export OPENAI_API_KEY=sk-... (Mac/Linux)
        # Or use Ollama locally (no key needed): LLM = "ollama/llama3"

Usage:
    python rag_pipeline_example.py
"""

from rag_evaluation_framework import Evaluator

# ═══════════════════════════════════════════════════════════════
# STEP 0: Configuration
# ═══════════════════════════════════════════════════════════════

# The LLM below is the JUDGE it evaluates your RAG system's output.
# Use a stronger model here for more reliable evaluations.
LLM = "openai/gpt-4o"  # or "ollama/llama3" (runs locally, no key)

evaluator = Evaluator(llm=LLM, cache=True)


# ═══════════════════════════════════════════════════════════════
# STEP 1: FETCH real content from a web page
# ═══════════════════════════════════════════════════════════════
# In a real RAG system, your knowledge base comes from actual sources:
# web pages, PDFs, internal documents, etc.


def fetch_web_page(url: str) -> str:
    """
    Fetch and extract readable text from a web page.
    This is what you'd do to build your knowledge base.

    For PDFs, use: pip install PyMuPDF
    import fitz
    doc = fitz.open("document.pdf")
    text = "\\n".join(page.get_text() for page in doc)

    For plain text files: Path("file.txt").read_text()
    """
    try:
        import httpx
        from bs4 import BeautifulSoup

        print(f" 🌐 Fetching: {url}")
        response = httpx.get(url, follow_redirects=True, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script/style tags
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        # Collapse multiple newlines
        lines = [line for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

        print(f" ✅ Fetched {len(text):,} characters")
        return text
    except ImportError:
        print(" ⚠️ httpx/beautifulsoup4 not installed. Install with:")
        print(" pip install httpx beautifulsoup4")
        print(" Using built-in content instead.")
        return ""
    except Exception as e:
        print(f" ⚠️ Failed to fetch: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into chunks (simulating what a real retriever does).
    In production you'd use a proper chunking strategy (semantic, recursive, etc.).
    """
    if not text:
        return []

    sentences = text.replace("\n", " ").split(". ")
    chunks = []
    current = []

    for sentence in sentences:
        current.append(sentence)
        total = len(" ".join(current))
        if total >= chunk_size:
            chunks.append(". ".join(current).strip() + ".")
            # Keep overlap sentences for next chunk
            overlap_count = max(1, len(current) // 4)
            current = current[-overlap_count:]

    if current:
        chunks.append(". ".join(current).strip() + ".")

    print(f" 📦 Created {len(chunks)} chunks")
    return chunks


# Fetch real content
print("=" * 70)
print(" STEP 1: Build Knowledge Base from Real Sources")
print("=" * 70)

SOURCE_URL = "https://en.wikipedia.org/wiki/France"
raw_text = fetch_web_page(SOURCE_URL)

if raw_text:
    KNOWLEDGE_BASE = chunk_text(raw_text)
else:
    # Fallback: built-in content (no internet required)
    print(" 📦 Using built-in content about France")
    KNOWLEDGE_BASE = [
        (
            "France, officially the French Republic, is a country primarily located in "
            "Western Europe. Its capital, largest city and main cultural and economic "
            "centre is Paris. It shares borders with Belgium, Luxembourg, Germany, "
            "Switzerland, Italy, Monaco, Andorra, and Spain."
        ),
        (
            "France is a unitary semi-presidential republic. The current president is "
            "Emmanuel Macron and the prime minister is Sébastien Lecornu. The current "
            "Fifth Republic was formed in 1958 by Charles de Gaulle."
        ),
        (
            "France has a high nominal per capita income globally, and its economy ranks "
            "among the largest in the world. The currency is the Euro. GDP (PPP) was "
            "estimated at $4.734 trillion with a per capita of $68,567 in 2026."
        ),
        (
            "France is the world's leading tourist destination, having received 102 "
            "million foreign visitors in 2025. It hosts 54 UNESCO World Heritage Sites "
            "and is a global centre of art, science, cuisine and philosophy."
        ),
        (
            "The French Revolution of 1789 overthrew the Ancien Régime and produced the "
            "Declaration of the Rights of Man. France reached its zenith under Napoleon "
            "Bonaparte in the early 19th century."
        ),
        (
            "As of 2026, France has an estimated population of 69.1 million. The official "
            "language is French. Religion demographics: 50% Christianity, 33% no religion, "
            "4% Islam, 2% Buddhism, 1% Judaism."
        ),
    ]

    print(f"\n Knowledge Base: {len(KNOWLEDGE_BASE)} chunks total")


# ═══════════════════════════════════════════════════════════════
# STEP 2: Your RAG Pipeline
# ═══════════════════════════════════════════════════════════════
# In production, your retriever searches a vector DB and your LLM
# generates the answer. Here we simulate both for demonstration.


def retrieve(question: str) -> list[str]:
    """
    YOUR RETRIEVER replace this with your vector DB search.
    """
    q = question.lower()
    relevant = []

    keyword_map = {
        "capital": [0], "paris": [0], "president": [1], "macron": [1],
        "government": [1], "gdp": [2], "economy": [2], "euro": [2],
        "currency": [2], "tourism": [3], "tourist": [3], "unesco": [3],
        "culture": [3], "revolution": [4], "napoleon": [4], "history": [4],
        "population": [5], "religion": [5], "language": [5],
    }

    for kw, indices in keyword_map.items():
        if kw in q:
            for idx in indices:
                if KNOWLEDGE_BASE[idx] not in relevant:
                    relevant.append(KNOWLEDGE_BASE[idx])

    return relevant[:3] if relevant else KNOWLEDGE_BASE[:2]


# ═══════════════════════════════════════════════════════════════
# STEP 3: Evaluate Your Test Cases
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print(" STEP 3: Evaluate RAG Outputs")
print("=" * 70)

test_questions = [
    "What is the capital of France?",
    "Who is the current president of France?",
    "What language do they speak in France?",
    "Tell me about French tourism",
]

for i, question in enumerate(test_questions, 1):
    print(f"\n -- Test {i}: {question}")

    # 1. RETRIEVE get relevant context
    context = retrieve(question)

    # 2. GENERATE call your LLM
    # Replace this block with YOUR actual RAG system's generator.
    # Example:
    # from your_app import rag_llm
    # answer = rag_llm.generate(question, context)
    #
    # For this demo, we simulate with keyword-based answers:
    answers = {
        "capital": "The capital of France is Paris.",
        "president": "The current president of France is Emmanuel Macron.",
        "language": "The official language of France is French.",
        "tourism": "France is the world's leading tourist destination.",
    }
    answer = "France is a country in Europe."
    for key, ans in answers.items():
        if key in question.lower():
            answer = ans
            break

    print(f" Retrieved: {len(context)} chunks")
    print(f" Answer: {answer[:80]}...")

    # 3. EVALUATE this is the core RAG Evaluation Framework call
    result = evaluator.score(
        question=question,
        context=context,
        answer=answer,
    )

    print(f" ├─ Overall: {result.overall_score:.3f}")
    print(f" ├─ Faithful: {result.faithfulness.score:.3f}")
    print(f" ├─ Halluc: {result.hallucination_rate.score:.3f}")
    print(f" ├─ Retrieval: {result.retrieval_precision.score:.3f}")
    print(f" ├─ Relevance: {result.answer_relevance.score:.3f}")
    print(f" ├─ Coverage: {result.context_coverage.score:.3f}")
    print(f" └─ UCM: {result.ucm_confidence.score:.3f}")

    # Diagnosis
    issues = []
    if result.faithfulness.score < 0.7:
        issues.append("LLM hallucinating claims not in context")
    if result.retrieval_precision.score < 0.7:
        issues.append("Retriever fetched irrelevant chunks")
    if result.context_coverage.score < 0.7:
        issues.append("LLM ignored useful content from context")
    if result.hallucination_rate.score > 0.3:
        issues.append("Answer contains fabricated claims")
    if result.answer_relevance.score < 0.7:
        issues.append("Answer doesn't address the question")

    if issues:
        print(f" ❌ Issues: {'; '.join(issues)}")
    else:
        print(" ✅ All metrics healthy")


# ═══════════════════════════════════════════════════════════════
# BONUS: Catch Bad RAG Outputs
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print(" BONUS: What RAG Evaluation Framework Catches")
print("=" * 70)

scenarios = [
    ("Hallucination",
     "What is the capital of France?",
     KNOWLEDGE_BASE[:1],
     "The capital of France is Lyon, famous for its silk industry."),

    ("Bad Retrieval",
     "What is the GDP of France?",
     [KNOWLEDGE_BASE[1], KNOWLEDGE_BASE[4]],  # Gov + history NOT economy
     "The GDP of France is $4.734 trillion."),

    ("Incomplete Answer",
     "Tell me about French tourism and culture",
     [KNOWLEDGE_BASE[3]],
     "France is a popular place."),
]

for name, question, ctx, answer in scenarios:
    print(f"\n -- {name}")
    print(f" Q: {question}")
    print(f" A: {answer}")
    r = evaluator.score(question=question, context=ctx, answer=answer)
    print(f" Overall: {r.overall_score:.3f} "
          f"Faithful: {r.faithfulness.score:.3f} "
          f"Retrieval: {r.retrieval_precision.score:.3f} "
          f"Coverage: {r.context_coverage.score:.3f}")


# ═══════════════════════════════════════════════════════════════
# GENERATE REPORTS
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print(" GENERATE REPORTS")
print("=" * 70)

best = evaluator.score(
    question=test_questions[0],
    context=retrieve(test_questions[0]),
    answer="The capital of France is Paris, located on the Seine River.",
)

for fmt, ext in [("markdown", "md"), ("json", "json"), ("html", "html")]:
    path = f"rag_eval_report.{ext}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(best.report(format=fmt))
    print(f" 📄 Saved: {path}")


# ═══════════════════════════════════════════════════════════════
# HOW TO PLUG IN YOUR REAL RAG SYSTEM
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print(" HOW TO USE WITH YOUR OWN RAG SYSTEM")
print("=" * 70)
print("""
1. Replace `retrieve()` with your vector DB search.
2. Replace the hardcoded answers with your actual LLM call.
3. Run evaluations in CI/CD to catch regressions on every deploy.

Minimal integration:
    ───────────────────────────────────────────────────────
    from rag_evaluation_framework import Evaluator
    from your_app import vector_db, llm

    evaluator = Evaluator(llm="openai/gpt-4o")

    for question in test_set:
        context = vector_db.search(question, top_k=5)
        answer = llm.generate(question, context)

        result = evaluator.score(
            question=question,
            context=context,
            answer=answer,
        )
        print(f"{question}: {result.overall_score:.3f}")
    ───────────────────────────────────────────────────────
""")
print(" Done! Open rag_eval_report.html in your browser to view the report.")
