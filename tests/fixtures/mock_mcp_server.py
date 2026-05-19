from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tools/sales_metric")
async def sales_metric(payload: dict) -> dict[str, object]:
    question = str(payload.get("question", ""))
    if "失败" in question:
        return {
            "status": "failure",
            "error_reason": "mock business failure",
        }
    return {
        "status": "success",
        "ability_type": "mcp",
        "ability_name": "sales_metric",
        "answer": "样例指标结果",
    }
