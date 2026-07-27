from django.shortcuts import render
from django.http import JsonResponse
from app_agent_genaisdk.agent_core.agent import run_agent_native_function_calling
import os
import markdown


def chat_view(request):
    """
    Renders the chat interface and handles AJAX POST requests.
    """
    # 1. 取得 session 中過往的歷史紀錄，若無則初始化空陣列
    chat_history = request.session.get('chat_history', [])
    is_valid_history = (
        isinstance(chat_history, list)
        and all(
            isinstance(item, dict) and "role" in item and "text" in item
            for item in chat_history
        )
    )
    if not is_valid_history:
        chat_history = []
        request.session['chat_history'] = chat_history

    if request.method == "POST":
        user_message = request.POST.get("message", "")
        if not user_message:
            return JsonResponse({"error": "Message is empty"}, status=400)

        try:
            print(f"=== [Phase 1 - POA Agent] 開始處理請求 ===")
            print(f"User Message: {user_message}")

            # 2. 呼叫代理並把歷史紀錄傳給他
            bot_reply = run_agent_native_function_calling(user_message, history_dict=chat_history)

            # 3. 得到結果後，把這一輪的對話記錄推入 Session 陣列中
            chat_history.append({"role": "user", "text": user_message})
            chat_history.append({"role": "model", "text": bot_reply})
            
            # 若歷史記錄太長，可選擇保留最近 N 筆對話（選用，在此設定保留最近 10 次往返 = 20筆）
            if len(chat_history) > 20:
                chat_history = chat_history[-20:]
            
            request.session['chat_history'] = chat_history

            print(f"=== [Phase 1 - POA Agent] 請求處理完成 ===")
            return JsonResponse({"reply": bot_reply})
        except Exception as e:
            print(f"=== [Phase 1 - POA Agent] 發生錯誤: {str(e)} ===")
            return JsonResponse({"error": str(e)}, status=500)

    # 4. 渲染初始畫面時，把現有歷史對話帶給前端顯示
    context = {"chat_history": chat_history}
    return render(request, "app_agent_genaisdk/home.html", context)

def clear_history(request):
    """
    清除目前 Session 內的 chat_history
    """
    if request.method == "POST":
        request.session['chat_history'] = []
        return JsonResponse({"status": "success", "message": "History cleared"})
    return JsonResponse({"error": "Invalid request"}, status=400)

def poa_agent_introduction(request):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    files = [
        os.path.join(base_dir, "app_agent_genaisdk", "第一階段說明.md"),
        os.path.join(base_dir, "app_agent_langchain", "第二階段說明.md"),
        os.path.join(base_dir, "app_agent_langgraph", "第三階段說明.md"),
    ]

    html_contents = []
    for filepath in files:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                md_content = f.read()
                html_content = markdown.markdown(
                    md_content,
                    extensions=[
                        "markdown.extensions.extra",
                        "markdown.extensions.nl2br",
                        "markdown.extensions.sane_lists",
                        "markdown.extensions.codehilite",
                        "markdown.extensions.toc",
                    ],
                )
                html_contents.append(html_content)
        else:
            html_contents.append(f"<p>Cannot find {os.path.basename(filepath)}</p>")

    context = {
        "content_phase1": html_contents[0],
        "content_phase2": html_contents[1],
        "content_phase3": html_contents[2],
    }

    return render(request, "app_agent_genaisdk/poa_agent_introduction.html", context)


'''
[19/May/2026 14:24:06] "GET /app_agent_langchain/chat/ HTTP/1.1" 200 19582
=== [Phase 2 - LangChain Agent] 開始處理請求 ===
User Message: 請上網幫我查一下今天台灣的即時天氣如何？

[LangGraph Core] 收到使用者訊息: 請上網幫我查一下今天台灣的即時天氣如何？

[LangChain Tool] 執行 search_and_read_web(query='今天台灣即時天氣 2024-05-23')
[LangChain Tool] 找到最相關網址，開始讀取內容：https://blog.airbare.com.hk/8255/【台灣-旅遊tips】台北天氣懶人包-四季天氣分析建議/

[LangChain Tool] 執行 search_and_read_web(query='2024年5月23日 台灣天氣預報 中央氣象署')
[LangChain Tool] 找到最相關網址，開始讀取內容：https://www.cwa.gov.tw/V8/C/
[LangGraph Core] 生成最終回覆完畢！
=== [Phase 2 - LangChain Agent] 請求處理完成 ===
[19/May/2026 14:24:43] "POST /app_agent_langchain/chat/ HTTP/1.1" 200 2002



我現在要知道，上面的過程來看，Gemini語言模型我呼叫幾次了？


從您提供的日誌過程來看，在這個對話中 Gemini 語言模型總共被呼叫了 **3 次**。

以下是這 3 次呼叫的分解過程（這也是 ReAct / Function Calling Agent 的標準運作流程）：

1. **第 1 次呼叫（理解與規劃）：**
   * **輸入給模型：** 使用者的問題「請上網幫我查一下今天台灣的即時天氣如何？」以及工具列表。
   * **模型的輸出：** 決定呼叫第一個工具 `search_and_read_web`，並產生搜尋關鍵字 `'今天台灣即時天氣 2024-05-23'`。

2. **第 2 次呼叫（評估與後續行動）：**
   * **輸入給模型：** 第 1 次搜尋結果的內容（blog.airbare.com.hk 的網頁內容）。
   * **模型的輸出：** 模型發現第一筆網頁可能是旅遊文章，資訊不夠即時或精確，因此決定再次呼叫工具，產生第二個搜尋關鍵字 `'2024年5月23日 台灣天氣預報 中央氣象署'`。

3. **第 3 次呼叫（總結與回覆）：**
   * **輸入給模型：** 第 2 次搜尋結果的內容（中央氣象署網站內容）。
   * **模型的輸出：** 模型認為收集到的資訊已經足夠回答您的問題，於是停止呼叫工具，將這些資訊彙整後，生成最終的自然語言回覆（對應到 `[LangGraph Core] 生成最終回覆完畢！`）。

所以為了回答您這一個問題，系統在背景實際與 Gemini 進行了 3 次互動！
'''



'''
# 1. 移除舊版且已棄用的 Gemini SDK
pip uninstall google-generativeai -y

# 2. 安裝新版 Gemini SDK
pip install google-genai

# 3. 更新 LangChain 相關套件與 LangGraph
pip install --upgrade langchain langchain-core langchain-google-genai langgraph

# 4. 加入 --force-reinstall 參數可以修復 unknown location 的檔案遺失問題
pip install --upgrade --force-reinstall langgraph langgraph-prebuilt langchain-core

'''

'''
目前可運作的版本組合（2024/5/23）：
# 2. 安裝新版 Gemini SDK
pip install google-genai==1.75.0

# 3. 更新 LangChain 相關套件與 LangGraph (強制安裝穩定的 1.x / 4.x 版本線)
pip install langchain==1.3.1 langchain-core==1.4.0 langchain-google-genai==4.2.2 langgraph==1.2.0 langgraph-prebuilt==1.1.0

# 4. 加入 --force-reinstall 參數可以修復 unknown location 的檔案遺失問題 (如有需要)
pip install --force-reinstall langgraph==1.2.0 langgraph-prebuilt==1.1.0 langchain-core==1.4.0
'''