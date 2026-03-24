import os
import time
import asyncio
from fastapi import APIRouter

router = APIRouter(prefix="/benchmark")

CPU_HANDLER = os.environ.get("CPU_HANDLER", "sync")


def fib(n: int) -> int:
    """재귀 피보나치 (CPU 부하용)"""
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)


# ===== CPU Bound =====
# CPU_HANDLER 환경변수에 따라 sync/async 핸들러 등록
# - sync (기본): def 핸들러 → FastAPI가 threadpool에서 실행, 이벤트 루프 비블로킹
# - async: async def 핸들러 → 이벤트 루프에서 직접 실행, 블로킹 발생

if CPU_HANDLER == "async":
    @router.get("/cpu")
    async def cpu_bound():
        """CPU Bound (async def): 이벤트 루프 블로킹"""
        result = fib(25)
        return {"result": result}
else:
    @router.get("/cpu")
    def cpu_bound():
        """CPU Bound (def): threadpool 실행"""
        result = fib(25)
        return {"result": result}


# ===== IO Bound =====
@router.get("/io")
async def io_bound():
    """IO Bound: 100ms async sleep"""
    await asyncio.sleep(0.1)
    return {"result": "ok", "slept_ms": 100}


# ===== Mixed =====
@router.get("/mixed")
async def mixed():
    """Mixed: fib(25) + 50ms sleep
    CPU 연산은 이벤트 루프에서 실행 (의도적 — mixed 시나리오 특성)
    """
    result = fib(25)
    await asyncio.sleep(0.05)
    return {"result": result, "slept_ms": 50}
