from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

# 定義 Graph 裡面流動的狀態 (State)
# 這比第二階段只能傳 messages 還要強大，您可以自己擴充欄位！
class GraphState(TypedDict):
    # 這裡的 add_messages 表示每次 return messages 時，會自動「追加」進去，而不是覆蓋
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 你可以自己擴充別的欄位，例如紀錄「目前這題查詢了幾次工具」、「草稿」等等
    # 這邊我們暫時只放 messages 來保持簡單
