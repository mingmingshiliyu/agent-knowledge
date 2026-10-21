# nodes.py
# 02定义节点函数
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from graph_state import AgentState

# 初始化 LLM
llm = ChatOpenAI(model="gpt-4o-mini")

# 定义工具（OpenAI 格式，bind_tools 支持 dict 列表）
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                },
                "required": ["expression"]
            }
        }
    }
]

llm_with_tools = llm.bind_tools(tools)


def chatbot(state: AgentState) -> dict:
    """聊天机器人节点：调用 LLM，可能返回 tool_calls"""
    response = llm_with_tools.invoke(state["messages"])
    # ⚠️ 不要在这里用 Command(goto=...) 跳转！
    # 一旦在节点里用 Command 指定 goto，条件边（add_conditional_edges）
    # 就不会再被触发，路由逻辑会绕过条件判断。
    # 正确做法：只返回状态更新，让"条件边"统一负责路由。
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """条件路由函数（决定从 chatbot 去哪里）"""
    last_message = state["messages"][-1]
    if last_message.tool_calls:          # 需要调用工具
        return "tool_executor"
    if state.get("should_ask_human"):    # 需要人工审核
        return "human_review"
    return END                           # 正常结束


def tool_executor(state: AgentState) -> dict:
    """工具执行节点"""
    messages = state["messages"]
    last_message = messages[-1]

    # 执行工具调用
    tool_messages = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        # 根据工具名称执行（生产环境请用真实工具/安全求值）
        if tool_name == "get_weather":
            result = f"{tool_args['city']}今日天气：晴，25°C"
        elif tool_name == "calculate":
            # ⚠️ 不要用 eval()！这里用 ast 安全求值（见第 2 章）
            result = _safe_eval_math(tool_args["expression"])
        else:
            result = f"未知工具: {tool_name}"

        tool_messages.append(ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"]  # 必须回传 tool_call_id
        ))

    return {"messages": tool_messages}


def human_review(state: AgentState) -> dict:
    """人工审核节点"""
    print("\n📋 需要人工审核的内容:")
    print(state["messages"][-1].content)

    approved = input("\n是否批准？(yes/no): ").lower()

    # ⚠️ 不要直接修改 state！LangGraph 的状态是不可变的，
    # 节点必须返回"要更新的字段"dict，由框架合并到状态。
    if approved == "yes":
        return {"should_ask_human": False}
    else:
        return {"messages": [HumanMessage(
            content="请重新生成，上面的内容不符合要求"
        )]}