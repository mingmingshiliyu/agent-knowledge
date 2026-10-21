# research_agent.py
# 生产环境建议用 llm.with_structured_output() 代替手写 json.loads，让模型直接输出 Pydantic 对象，避免 JSON 解析失败。
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
import json

class ResearchState(TypedDict):
    topic: str
    outline: str
    sections: list[str]
    draft: str
    needs_rewrite: bool          # 必须声明，否则节点返回会报错
    review_feedback: str         # 必须声明，否则节点返回会报错
    messages: Annotated[list[BaseMessage], operator.add]

class ResearchAgent:
    """研究报告生成 Agent"""

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o")
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(ResearchState)

        workflow.add_node("generate_outline", self.generate_outline)
        workflow.add_node("write_sections", self.write_sections)
        workflow.add_node("draft_report", self.draft_report)
        workflow.add_node("review", self.review_report)

        workflow.set_entry_point("generate_outline")

        workflow.add_edge("generate_outline", "write_sections")
        workflow.add_edge("write_sections", "draft_report")

        # 条件边：review 决定是重写还是结束
        workflow.add_conditional_edges(
            "review",
            lambda state: "rewrite" if state.get("needs_rewrite") else "done",
            {
                "rewrite": "draft_report",
                "done": END,
            }
        )

        return workflow.compile()

    def generate_outline(self, state: ResearchState) -> dict:
        """生成大纲"""
        prompt = f"""请为以下主题生成研究报告大纲：{state['topic']}

要求：
1. 包含 5-8 个主要章节
2. 每个章节有 2-3 个子要点
3. 输出 JSON 格式"""
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return {"outline": response.content}

    def write_sections(self, state: ResearchState) -> dict:
        """撰写各章节内容"""
        prompt = f"""根据以下大纲撰写报告内容：

{state['outline']}

请生成完整的报告草稿。"""
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return {"sections": [response.content]}

    def draft_report(self, state: ResearchState) -> dict:
        """生成报告草稿"""
        sections_content = "\n\n".join(state["sections"])
        prompt = f"""请根据以下内容整理成正式研究报告：

{sections_content}

要求：
1. 添加引言和结论
2. 使用专业语言
3. 格式规范"""
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return {"draft": response.content}

    def review_report(self, state: ResearchState) -> dict:
        """审核报告"""
        prompt = f"""请审核以下研究报告，指出需要改进的地方：

{state['draft']}

如果报告质量达标，输出 JSON: {{"needs_rewrite": false}}
如果需要重大修改，输出 JSON: {{"needs_rewrite": true, "feedback": "具体反馈"}}"""
        response = self.llm.invoke([HumanMessage(content=prompt)])

        # 建议让模型输出严格 JSON（如用 ChatOpenAI 的 response_format）
        review = json.loads(response.content)

        return {
            "needs_rewrite": review.get("needs_rewrite", False),
            "review_feedback": review.get("feedback", ""),
        }

    def run(self, topic: str) -> str:
        """运行研究 Agent"""
        initial_state = {
            "topic": topic,
            "outline": "",
            "sections": [],
            "draft": "",
            "needs_rewrite": False,
            "review_feedback": "",
            "messages": [],
        }
        result = self.graph.invoke(initial_state)
        return result["draft"]