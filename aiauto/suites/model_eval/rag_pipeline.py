# aiauto/suites/model_eval/rag_pipeline.py
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Any

# --- Splitter (new package first, then legacy path) ---
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except Exception:
    from langchain.text_splitter import RecursiveCharacterTextSplitter  # older LC

# --- Vector store (community package first, then legacy path) ---
try:
    from langchain_community.vectorstores import FAISS
except Exception:
    from langchain.vectorstores import FAISS  # older LC

from langchain_openai import OpenAIEmbeddings, ChatOpenAI


# -------------------------
# RAG Builder
# -------------------------
def build_rag_pipeline_from_file(
    file_path: str | Path,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    Build a minimal RAG pipeline (split -> embed -> FAISS) from a single text file.

    Returns a dict containing:
      - 'vs'  : FAISS vector store
      - 'llm' : ChatOpenAI client
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Ground-truth file not found: {file_path.resolve()}")

    text = file_path.read_text(encoding="utf-8")
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks: List[str] = splitter.split_text(text)

    # embeddings
    emb = OpenAIEmbeddings()  # uses OPENAI_API_KEY from env
    vs = FAISS.from_texts(chunks, embedding=emb)

    llm = ChatOpenAI(model=model, temperature=0)  # deterministic answers
    return {"vs": vs, "llm": llm}


# -------------------------
# RAG Answer
# -------------------------
def answer_with_rag(
    qa: Dict[str, Any],
    question: str,
    top_k: int = 3,
    unify_style: str = "canonical",
) -> str:
    """
    Retrieve top_k chunks and produce a single canonical answer using only the context.
    """
    vs = qa["vs"]
    llm = qa["llm"]

    docs = vs.similarity_search(question, k=top_k)
    context = "\n\n".join(d.page_content for d in docs)

    system_rules = (
        "You are a strict policy quoting bot.\n"
        "Answer ONLY from the provided CONTEXT. If information is not in CONTEXT, say 'Not found in policy context.'\n"
        "Unify equivalent phrasings into one canonical line. Prefer: 'in 24 hours (on 18 Oct 2025, Saturday)'. "
        "Be concise and precise."
    )

    prompt = (
        f"{system_rules}\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION: {question}\n"
        f"FINAL ANSWER:"
    )

    # ChatOpenAI supports string -> AIMessage via .invoke
    result = llm.invoke(prompt)
    # result.content for newer LC, else str(result)
    return getattr(result, "content", str(result)).strip()
