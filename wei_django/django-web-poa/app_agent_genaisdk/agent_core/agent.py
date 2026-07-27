import os
from google import genai
from google.genai import types

from app_agent_genaisdk.agent_core.tools import (
    get_top_keywords,
    get_top_persons,
    get_keyword_correlation,
    get_latest_article_by_keyword,
    search_and_read_web,
    read_local_document,
    save_report_to_file,
)

def run_agent_native_function_calling(user_message: str, history_dict: list = None):
    """
    Phase 1: Native Gemini Function Calling (新版 SDK 寫法)
    
    google-genai 的 native tool calling 機制不是透過 Python subprocess 去執行你的函式。
    它會在同一個 Python process 內部：
    讀取你傳入的 callable（例如 get_top_keywords）
    生成工具 schema / function signature
    當模型決定要呼叫工具時，直接在這個 process 裡呼叫對應的 Python 函式
    再把函式回傳結果送回模型做最終回答
    所以它本質上是「本地函式呼叫」，不是啟動子程序。
    """
    if history_dict is None:
        history_dict = []

    from dotenv import load_dotenv
    load_dotenv()
    
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "錯誤：找不到 GEMINI_API_KEY，請確認 .env 設定。"

    # 提示詞要告訴語言模型可以使用哪些工具，以及在什麼情況下使用這些工具。如果情況複雜的話，可以寫在一個 MD 檔案裡面，然後用工具讀取這個提示詞檔案的內容。
    # 這裡也可以告訴語言模型哪些事情可以做，哪些事情不能做，讓它更好地判斷什麼時候該使用工具，什麼時候該直接回答。
    # 
    system_instruction = (
        "你是專業的輿情分析專家（POA Agent）。你具備搜尋網路、讀取本地文件、分析資料庫趨勢與情緒判斷的能力。\n"
        "- 查詢若們趨勢或議題時，依據指定的類別，取3個關鍵詞，若沒有指定類別，預設用政治類，呼叫 `get_top_keywords`。\n"
        "- 查詢熱門關鍵人物時，呼叫 `get_top_persons`。\n"
        "- 比較兩個關鍵字是否經常相伴出現、或查詢議題關聯度時，呼叫 `get_keyword_correlation`。\n"
        "- 當需要查詢資料庫中關於某關鍵字的『最新一篇文章』全文、連結或發布日期時，務必呼叫 `get_latest_article_by_keyword`。\n"
        "- 當用戶說上網搜尋時，呼叫 `search_and_read_web` 上網查資料。\n"
        "- 當需要查詢最新的外部資料、即時新聞或不在資料庫裡的資訊時，呼叫 `search_and_read_web` 上網查資料。\n"
        "- 當需要讀取知識庫文件時，直接傳入檔名給 `read_local_document`（系統會自動去 knowledge_base/ 尋找）。\n"
        "- 當使用者要求「存檔」、「生成報告檔案」或「存到文件」時，呼叫 `save_report_to_file`。\n\n"
        "- 當沒有任何工具可用時，你就用自己的專業知識去回答。\n"
        "**互動範例：**\n"
        "1. 「分析政治類3個最熱門關鍵字，並做摘要。」\n"
        "2. 「從資料庫中找出關於『台積電』的最新一篇文章，摘要其內容並附上原文連結。」\n"
        "3. 「讀取知識庫中的 業務規範.md，並總結其重點。」\n"
        "請將工具數據融會貫通，給出一份生動、有數據佐證的 Markdown 回答。"
    )

    # 1. 初始化 Client
    client = genai.Client(api_key=api_key)

    # 2. 將系統指令與工具打包進 Config
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[
            get_top_keywords,
            get_top_persons,
            get_keyword_correlation,
            get_latest_article_by_keyword,
            search_and_read_web,
            read_local_document,
            save_report_to_file,
        ],
    )
    
    # 3. 把剛剛從 Django 傳進來的字典陣列，轉換給 Gemeni 新版 SDK 要求的 types.Content 型態
    formatted_history = []
    for msg in history_dict:
        formatted_history.append(
            types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["text"])]
            )
        )

    print(f"\n[Agent Core] 收到使用者訊息: {user_message}")
    print("[Agent Core] 準備把訊息發送給 Gemini，並授權模型自動呼叫工具...")
    
    # 3. 建立 Chat 物件
    # 在新版中，只要 tools 傳入了 Python 函式，傳送訊息時就會自動執行函式呼叫的來回溝通
    chat = client.chats.create(
        model="gemini-3.1-flash-lite", # 將你需要的模型名稱放在這裡
        config=config,
        history=formatted_history
    )
    
    # 4. 發送訊息 (Gemini 會在背後自動處理工具呼叫與資料整合)
    response = chat.send_message(user_message)
    
    print("[Agent Core] Gemini 生成最終回覆完畢！")
    print(f"\n\n[Agent Core] Gemini 過程中的對話完整內容:\n{response}")
    return response.text

