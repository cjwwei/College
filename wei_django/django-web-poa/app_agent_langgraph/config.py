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
#MODEL_NAME = "gemma-4-31b-it"
MODEL_NAME = "gemini-3.1-flash-lite"

# Gemini API 密鑰
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env - 請確認環境變數設定正確")

# ===== Agent 系統提示詞配置 =====
SYSTEM_PROMPT = """你是極度專業的輿情分析專家（Phase 3 Custom Graph Agent）。
這是完整的第三階段架構！請善用你的工具來查資料，並提供一份包含標題、數據、與觀點洞察的精美 Markdown 分析報告。
重要規則：凡是需要新聞類別 category 的工具（例如 get_top_keywords、get_top_persons），若使用者沒有明確提供類別，請先反問使用者，不要自行猜測或填入預設類別。"""

# ===== 其他配置參數 =====
# 聊天消息歷史記錄的 Session Key
SESSION_HISTORY_KEY = "custom_graph_history"

# 最大遞迴迴圈次數（防止無限迴圈）
MAX_ITERATIONS = 10
