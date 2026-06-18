from .models import RagResult
from .context_builder import build as build_context
from .llm_client import LlmClient, LlmTimeoutError, LlmApiError
from .context_builder import build
from .. import config
from ..search.bm25_searcher import search as bm25_search


def run_rag(question: str, top_k: int, model: str | None, client, index: str) -> RagResult:
    if not question or not question.strip():
        return RagResult(answer=None, sources=[], error="Question cannot be empty.")

    api_key = config.openai_api_key()
    if not api_key:
        return RagResult(answer=None, sources=[], error="OPENAI_API_KEY environment variable is not set.")

    resolved_model = model or config.llm_model()

    try:
        hits = bm25_search(client, question, top_k, index)
        if not hits:
            return RagResult(answer="No passages retrieved for this query.", sources=[], error=None)

        context = build_context(hits)
        user_prompt = f"Passages:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        answer = LlmClient(resolved_model, api_key).complete(
            "You are a search assistant. Answer the question using only the provided passages.\n"
            "If the passages do not contain enough information, say so.",
            user_prompt,
        )
        return RagResult(answer=answer, sources=hits, error=None)

    except LlmTimeoutError:
        return RagResult(answer=None, sources=[], error="LLM call timed out after 30 seconds.")
    except LlmApiError as e:
        return RagResult(answer=None, sources=[], error=f"LLM API returned HTTP {e.status_code} — {e.message}")
    except Exception as e:
        return RagResult(answer=None, sources=[], error=str(e) or type(e).__name__)
