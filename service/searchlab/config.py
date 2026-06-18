import os


def opensearch_url() -> str:
    return os.getenv("OPENSEARCH_URL", "http://localhost:9200")


def index_name() -> str:
    return os.getenv("SEARCHLAB_INDEX", "searchlab-v0")


def openai_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY") or None


def llm_model() -> str:
    return os.getenv("SEARCHLAB_LLM_MODEL", "gpt-4o-mini")


def llm_judge_model() -> str:
    return os.getenv("SEARCHLAB_LLM_JUDGE_MODEL", "gpt-4o-mini")
