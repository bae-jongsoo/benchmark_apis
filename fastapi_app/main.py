from fastapi import FastAPI
from routers import benchmark, foods

app = FastAPI(title="FastAPI Benchmark")

app.include_router(benchmark.router)
app.include_router(foods.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
