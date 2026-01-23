from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from master_agent import run_agent_generator

router = APIRouter(prefix="/api/agent", tags=["agent"])

@router.get("/stream")
async def stream_pdd(query: str, session_id: str = None):
    """
    流式返回拼多多 Agent 的执行结果 (SSE 格式)
    """
    return StreamingResponse(run_agent_generator(query, thread_id=session_id), media_type="text/event-stream")
