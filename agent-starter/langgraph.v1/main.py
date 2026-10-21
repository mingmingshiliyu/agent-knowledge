# main.py
# 04 运行agent
# 多轮上下文的关键：同一个 thread_id。LangGraph 用 thread_id 区分会话，没有配置 thread_id 时每次 invoke 都是全新会话，不会"记得"上一轮。
from build_graph import graph
from langchain_core.messages import HumanMessage

# 通过 config 传入 thread_id 标识会话
thread_config = {"configurable": {"thread_id": "session-1"}}

# 示例 1：简单问答
result = graph.invoke(
    {"messages": [HumanMessage(content="北京今天天气怎么样？")]},
    config=thread_config
)

print("回复:", result["messages"][-1].content)

# 示例 2：多轮对话保持上下文（同一 thread_id）
result = graph.invoke(
    {"messages": [HumanMessage(content="帮我计算 123 + 456 * 789")]},
    config=thread_config
)

print("回复:", result["messages"][-1].content)

# 示例 3：Agent 记得之前的对话
result = graph.invoke(
    {"messages": [HumanMessage(content="刚才的计算结果是多少？")]},
    config=thread_config
)

print("回复:", result["messages"][-1].content)