from fastapi import APIRouter

from helpers.rag_helper import rag_completion
from models.chat import RagChatRequest, RagChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/rag",
    response_model=RagChatResponse,
    summary="RAG chat over uploaded documents",
    description=(
        "Retrieves relevant chunks from documents you uploaded via **POST /documents/upload**, "
        "injects them as CONTEXT with a strict grounded prompt, then answers. "
        "Optional `document_ids` limits search to specific uploads."
    ),
)
async def chat_rag(payload: RagChatRequest) -> RagChatResponse:
    return await rag_completion(payload)
