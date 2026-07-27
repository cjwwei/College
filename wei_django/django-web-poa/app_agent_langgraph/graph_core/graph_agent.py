from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

# 我們直接重複利用上一階段寫好的好用語情分析工具！
from app_agent_langchain.agent_core.tools import (
    get_top_keywords,
    get_top_persons,
    get_keyword_correlation,
    search_and_read_web,
    read_local_document,
)
from .state import GraphState
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

"""
app_agent_langgraph 全局配置文件
統一管理模型名稱、API 密鑰、和其他系統參數
"""

import os
from dotenv import load_dotenv

# 加載環境變數
load_dotenv()

# ===== LLM 模型配置 =====
# Gemini 模型名稱 - 在此統一設定，便於修改
# MODEL_NAME = "gemma-4-31b-it"
MODEL_NAME = "gemini-3.1-flash-lite"

# Gemini API 密鑰
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env - 請確認環境變數設定正確")

# ===== Agent 系統提示詞配置 =====
SYSTEM_PROMPT = """你是極度專業的輿情分析專家（Phase 3 Custom Graph Agent）。
這是完整的第三階段架構！請善用你的工具來查資料，並提供一份包含標題、數據、與觀點洞察的精美 Markdown 分析報告。
重要規則：凡是需要新聞類別 category 的工具（例如 get_top_keywords、get_top_persons），若使用者沒有明確提供類別，請先反問使用者，不要自行猜測或填入預設類別。"""


# 初始化 Gemini
llm = ChatGoogleGenerativeAI(model=MODEL_NAME, google_api_key=GEMINI_API_KEY)

# ----- 步驟 1: 定義工具與綁定模型 -----
tools = [
    get_top_keywords,
    get_top_persons,
    get_keyword_correlation,
    search_and_read_web,
    read_local_document,
]
llm_with_tools = llm.bind_tools(tools)


# ----- 步驟 2: 定義節點 (Nodes) -----
# 這是負責「思考」與「下決定」的節點
def agent_node(state: GraphState):
    # 從狀態中提取對話紀錄
    messages = state["messages"]

    print(
        f"[Phase 3 Graph][agent] 進入 agent_node，messages={len(messages)}", flush=True
    )

    # 動態插入專家身分的 System Prompt 作為這輪對話的最高指導原則
    # （從統一的配置文件中讀取）
    system_msg = SystemMessage(content=SYSTEM_PROMPT)

    # 呼叫已經綁定工具的模型
    # 因為是 add_messages 模式，所以只要回傳我們這回合產生的新 message 即可
    response = llm_with_tools.invoke([system_msg] + messages)

    if getattr(response, "tool_calls", None):
        print(f"[Phase 3 Graph][agent] 模型請求工具: {response.tool_calls}", flush=True)
    else:
        print("[Phase 3 Graph][agent] 模型直接輸出最終答案", flush=True)

    return {"messages": [response]}


# 這是負責「執行工具」的節點 (LangGraph 預建提供的工具節點)
tool_node = ToolNode(tools)


# ----- 步驟 3: 定義條件路由 (Conditional Edge) -----
def should_continue(state: GraphState) -> str:
    """判斷模型是不是決定要呼叫工具，還是已經準備好給出最終答案了"""
    last_message = state["messages"][-1]
    print(
        f"[Phase 3 Graph][route] 檢查最後一則訊息是否需要工具，has_tool_calls={bool(last_message.tool_calls)}",
        flush=True,
    )
    # 如果模型的最後一個訊息帶有 tool_calls，代表它想查資料
    if last_message.tool_calls:
        return "continue"
    # 否則就是想直接跟使用者講話了
    return "end"


# ----- 步驟 4: 繪製狀態圖 (StateGraph) -----
# 建立一個以我們自訂 GraphState 為核心的有向圖
workflow = StateGraph(GraphState)

# 加入節點
workflow.add_node("agent", agent_node)
workflow.add_node("action", tool_node)

# 設定起點
workflow.add_edge(START, "agent")

# 設定根據 Agent 回覆來判斷下一步要走去哪裡
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "action",  # 若要繼續，把控制權交給工具節點
        "end": END,  # 若要結束，走到終點
    },
)

# 工具節點執行完後，一定要再回去給 Agent 節點看看資訊夠不夠
workflow.add_edge("action", "agent")

# ----- 步驟 5: 編譯成可執行的 Application -----
# compile 後就會變成一個類似 agent_executor 的東西
app_graph = workflow.compile()


# ----------------- 供 Django Views 呼叫的進入點 -----------------
def run_custom_graph(user_message: str, history_dicts: list) -> tuple[str, list]:
    print(f"\n[Phase 3 Graph] 收到使用者訊息: {user_message}", flush=True)

    # 轉換歷史訊息格式
    messages = []
    for msg in history_dicts:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))

    # 直接執行 graph，節點與路由內部已經會 print 出流程資訊
    final_state = app_graph.invoke({"messages": messages})

    bot_reply = final_state["messages"][-1].content

    # 處理 Gemini 可能吐出清單內容的問題
    if isinstance(bot_reply, list):
        bot_reply = "".join(
            [
                chunk.get("text", "")
                for chunk in bot_reply
                if chunk.get("type") == "text"
            ]
        )

    # 更新並回傳狀態
    history_dicts.append({"role": "user", "content": user_message})
    history_dicts.append({"role": "assistant", "content": bot_reply})

    print("[Phase 3 Graph] 生成最終回覆完畢！", flush=True)
    return bot_reply, history_dicts
