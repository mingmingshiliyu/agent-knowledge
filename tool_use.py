# tool use解决问题:
# 一: 工具描述: 让模型知道有哪些工具,对应参数,返回格式
# 二: 调用时机: 模型什么时候调用工具,什么时候该直接回答
# 三: 结果处理: 工具返回结果怎么给回模型,出错怎么办

# 工具调用方式有三种:
# 1. 单工具调用
# 2. 并行工具调用: 并行调用多个任务,注意任务之间的顺序
# 3. ReAct链式调用: 让agent决定下一步.单次调用搞不定先查用户信息,再根据用户等级定折扣,再下单,需要用ReAct,让模型决定下一步做什么
# 4. 动态工具生成: 模型自己写代码当工具
def tool_def():
    tools = [{
        "name": "get_order_status",
        "description": "查询订单状态，需要提供订单号",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "订单号，格式如 ORD202607290001"}
            },
            "required": ["order_id"]
        }
    }]

    def call_llm_with_tools(user_msg, tools):
        resp = llm.chat(
            messages=[{"role": "user", "content": user_msg}],
            tools=tools
        )
        if resp.tool_calls:
            for tc in resp.tool_calls:
                result = execute_tool(tc.name, tc.arguments)
                return llm.chat(messages=[
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "tool_calls": [tc]},
                    {"role": "tool", "content": result, "tool_call_id": tc.id}
                ])
        return resp


import asyncio

# 并行调用工具执行
async def execute_parallel_tools(tool_calls):
    tasks = [execute_tool_async(tc.name, tc.arguments) for tc in tool_calls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [
        {"tool_call_id": tc.id, "content": r if not isinstance(r, Exception) else f"错误: {r}"}
        for tc, r in zip(tool_calls, results)
    ]

# ReAct链式调用: max_steps设太小跑不完,设太大容易死循环,建议6-8步,并加死循环检测(连续两步调用同一个工具且参数相同,直接报错)
# 每次调用都要塞上下文,token消耗大,需要上下文压缩(让llm总结后再作为上下文)
def react_loop(user_msg, tools, max_steps=6):
    messages = [{"role": "user", "content": user_msg}]
    for step in range(max_steps):
        resp = llm.chat(messages=messages, tools=tools)
        if not resp.tool_calls:
            return resp.content
        messages.append({"role": "assistant", "tool_calls": resp.tool_calls})
        for tc in resp.tool_calls:
            result = execute_tool(tc.name, tc.arguments)
            messages.append({"role": "tool", "content": result, "tool_call_id": tc.id})
    return "任务步数超限，请人工介入"

# 工具太多注意力会被稀释:
# 解决: 把用户意图embedding,从工具库召回最相关三五个,只把这几个schema喂给模型
# 边界: 30以上上检索
# 代价: 牺牲一点召回,万一用户意图描述很迷糊,真正需要工具没进top5,就废了
def retrieve_relevant_tools(user_msg, tool_registry, top_k=5):
    query_emb = embed(user_msg)
    scored = [(cosine_sim(query_emb, t.embedding), t) for t in tool_registry]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:top_k]]

def call_with_tool_retrieval(user_msg, tool_registry):
    candidates = retrieve_relevant_tools(user_msg, tool_registry)
    return llm.chat(messages=[{"role": "user", "content": user_msg}], tools=candidates)