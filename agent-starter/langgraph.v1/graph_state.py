# graph_state.py
# 1.定义状态类型
from typing import TypedDict, Annotated
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """Agent 的状态定义"""
    messages: Annotated[list[BaseMessage], operator.add]  # 累加式更新
    next_node: str  # 下一个要执行的节点
    should_ask_human: bool  # 是否需要人工确认