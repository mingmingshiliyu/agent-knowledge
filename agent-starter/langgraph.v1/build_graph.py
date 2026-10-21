# build_graph.py
#03 构建图
from langgraph.graph import StateGraph, END
from graph_state import AgentState
from nodes import chatbot, tool_executor, human_review, should_continue

# 创建图
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("chatbot", chatbot)
workflow.add_node("tool_executor", tool_executor)
workflow.add_node("human_review", human_review)

# 设置入口点
workflow.set_entry_point("chatbot")

# 工具执行完回到聊天节点（循环）
workflow.add_edge("tool_executor", "chatbot")

# 条件边：chatbot 之后的走向由 should_continue 决定
workflow.add_conditional_edges(
    "chatbot",
    should_continue,
    {
        "tool_executor": "tool_executor",
        "human_review": "human_review",
        END: END,
    }
)

# 编译图（这一步只编译一次）
# checkpointer=None 是默认值（内存检查点），无需显式传
graph = workflow.compile()

# 持久化检查点（可选，见 3.5.2）
# from langgraph.checkpoint.sqlite import SqliteSaver
# with SqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
#     graph = workflow.compile(checkpointer=checkpointer)