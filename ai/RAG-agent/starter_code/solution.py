import os
import re

import requests
from dotenv import load_dotenv

try:
    from openai import OpenAI  # OpenAI API compatible client
except ImportError:  # pragma: no cover - if there is no openai package
    OpenAI = None

load_dotenv()


# ---------------------------------------------------------------------------
# Search — Document recovery
# ---------------------------------------------------------------------------

def _search_documents(query: str, top_k: int = 5) -> list:
    """
    Call the search API and return the raw list of results.
    """
    search_url = os.environ.get("SEARCH_API_URL", "")
    search_api_key = os.environ.get("SEARCH_API_KEY", "")

    headers = {}
    if search_api_key:
        headers["Authorization"] = f"Bearer {search_api_key}"

    try:
        response = requests.get(
            search_url,
            params={"query_text": query, "top_k": top_k},
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        results = response.json()
        if not isinstance(results, list):
            return []
        return results
    except Exception:
        return []


def _build_documents(raw_results: list) -> list:
    """
    Converts raw search results to the format [{'id': 1, 'text': ...}, ...].

    - Supports both item formats (dict with key 'text', or raw string).
    - id is only assigned to items with non-empty text, so ids
      always start at 1 and are contiguous (no gaps).
    """

    documents = []
    next_id = 1
    for item in raw_results:
        text = ""
        if isinstance(item, dict):
            text = item.get("text") or ""
        elif isinstance(item, str):
            text = item
        text = text.strip() if isinstance(text, str) else ""
        if text:
            documents.append({"id": next_id, "text": text})
            next_id += 1
    return documents


def _build_context(documents: list) -> str:
    """Formats documents for inclusion in the language model prompt."""
    parts = [f"[سند {doc['id']}]\n{doc['text']}" for doc in documents]
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Generation — Response generation by language model
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "شما یک دستیار پاسخ‌گویی مبتنی بر اسناد (RAG) هستید که به هر موضوع و "
    "حوزه‌ای که اسناد آن را پوشش می‌دهند پاسخ می‌دهید؛ به هیچ دامنه یا موضوع "
    "خاصی وابسته نیستید.\n"
    "قوانین پاسخ‌گویی:\n"
    "۱. پاسخ را فقط بر اساس اسناد ارائه‌شده بنویس و از دانش خارج از اسناد "
    "استفاده نکن.\n"
    "۲. هر جا از اطلاعات یک سند استفاده می‌کنی، بلافاصله بعد از همان جمله یا "
    "عبارت با تگ <cite>N</cite> به شماره (id) همان سند ارجاع بده؛ برای مثال "
    "<cite>1</cite>. شماره باید دقیقاً همان id سندی باشد که در ادامه دیده "
    "می‌شود.\n"
    "۳. اگر بیش از یک سند در یک جمله استفاده شد، برای هر سند یک تگ جداگانه "
    "بگذار، مثلاً <cite>1</cite> <cite>2</cite>.\n"
    "۴. اگر حداقل یک سند در اختیارت قرار گرفته، پاسخ تو باید حتماً شامل "
    "حداقل یک تگ <cite>N</cite> باشد؛ هرگز بدون ارجاع پاسخ نده.\n"
    "۵. اگر پاسخ سوال در اسناد موجود نیست، صریحاً بگو که اطلاعات کافی در "
    "اسناد ارائه‌شده یافت نشد؛ حدس نزن و منبع خارجی ذکر نکن.\n"
    "۶. پاسخ باید به زبان فارسی، دقیق، مختصر و مرتبط با سوال کاربر باشد."
)


def _generate_answer(query: str, documents: list, client, model: str) -> str:
    """Produces the final response by calling the language model (may raise)."""
    if documents:
        context = _build_context(documents)
    else:
        context = "هیچ سند مرتبطی یافت نشد."

    user_prompt = (
        f"اسناد:\n{context}\n\n"
        f"سوال کاربر: {query}\n\n"
        "با توجه به قوانین بالا پاسخ را بنویس."
    )

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    answer = completion.choices[0].message.content or ""
    return answer.strip()


def _fallback_answer(documents: list) -> str:
    """Alternative response for when invoking the language model encounters an error."""
    if documents:
        first_id = documents[0]["id"]
        return (
            "در حال حاضر امکان تولید پاسخ توسط مدل زبانی وجود نداشت. "
            f"می‌توانید اطلاعات مرتبط را در سند <cite>{first_id}</cite> بررسی کنید."
        )
    return "متأسفانه هیچ سند مرتبطی برای این سوال یافت نشد."


# ---------------------------------------------------------------------------
# Citations — Extracting references from the response text
# ---------------------------------------------------------------------------

def _extract_citations(answer: str, valid_ids: set) -> list:
    """
    Extracts the referenced IDs in <cite>N</cite> tags
    (without repetitions, in order of appearance).
    """

    found = re.findall(r"<cite>\s*(\d+)\s*</cite>", answer)
    citations = []
    for f in found:
        n = int(f)
        if n in valid_ids and n not in citations:
            citations.append(n)
    return citations


def _ensure_citation(answer: str, documents: list, citations: list) -> tuple:
    """
    Safety layer: If a document exists but the model does not produce any
    valid <cite> tags,a reference to the first document is automatically
    added so that the output is always documented — regardless of how well
    the language model follows the prompt instruction.
    """
    if documents and not citations:
        first_id = documents[0]["id"]
        answer = f"{answer.rstrip()} <cite>{first_id}</cite>"
        citations = [first_id]
    return answer, citations


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def rag_agent(query: str) -> dict:
    """
    A complete RAG Agent: Retrieve documents related to the question
    and generate a documented answer.

    Args:
    query: User's question in Persian.

    Returns:
    dict containing:
    - answer: Generated answer (with <cite>N</cite> tags)
    - documents: List of documents used [{"id": .., "text": ..}, ...]
    - citations: List of document IDs referenced in the answer text
    """

    llm_base_url = os.environ["LLM_BASE_URL"]
    llm_api_key = os.environ["LLM_API_KEY"]
    llm_model = os.environ["LLM_MODEL_NAME"]

    try:
        raw_results = _search_documents(query, top_k=5)
    except Exception:
        raw_results = []

    documents = _build_documents(raw_results)
    valid_ids = {d["id"] for d in documents}

    try:
        if OpenAI is None:
            raise RuntimeError("پکیج openai در دسترس نیست")
        client = OpenAI(base_url=llm_base_url, api_key=llm_api_key)
        answer = _generate_answer(query, documents, client, llm_model)
        if not answer:
            answer = _fallback_answer(documents)
    except Exception:
        answer = _fallback_answer(documents)

    citations = _extract_citations(answer, valid_ids)
    answer, citations = _ensure_citation(answer, documents, citations)

    return {
        "answer": answer,
        "documents": documents,
        "citations": citations,
    }
