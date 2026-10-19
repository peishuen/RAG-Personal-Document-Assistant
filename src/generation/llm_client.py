"""
This file sets up the qwen language model (llm) in one place.
generator.py, query_rewriter.py and grounding_check.py all use it, so they do
not need to repeat the same config and model name.
Thinking stays on, but each job gets a thinking budget, because unlimited
thinking made answers slow and used many more tokens than the visible reply.
The max reply length is the thinking budget plus the reply allowance, because
the model counts its thinking tokens against max_tokens.
"""

import os
from langchain_openai import ChatOpenAI

# set the thinking budget and the reply allowance for each job, in tokens
# raise a budget for better reasoning, or lower it to save time and tokens
JOB_SETTINGS = {
    "answer": {"thinking_budget": 300, "reply_tokens": 600},
    "grounding": {"thinking_budget": 200, "reply_tokens": 100},
    "rewrite": {"thinking_budget": 100, "reply_tokens": 100},
    "judge": {"thinking_budget": 200, "reply_tokens": 100},
}

def get_llm(job: str = "answer") -> ChatOpenAI:
    settings = JOB_SETTINGS[job]

    # connect to qwen3.8-flash through the openai-compatible route
    # use this route because the native dashscope sdk gives a 400 error on this endpoint
    return ChatOpenAI(
        model="qwen3.8-flash",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=os.getenv("DASHSCOPE_OPENAI_BASE_URL"),
        # cap the total output, thinking tokens included, so the reply is never cut short by thinking
        max_tokens=settings["thinking_budget"] + settings["reply_tokens"],
        # keep thinking on, but stop it at the budget (a budget of 0 turns thinking off)
        extra_body={
            "enable_thinking": settings["thinking_budget"] > 0,
            **({"thinking_budget": settings["thinking_budget"]} if settings["thinking_budget"] > 0 else {}),
        },
        # ask for token counts when streaming, so the metrics still work
        stream_usage=True,
    )
