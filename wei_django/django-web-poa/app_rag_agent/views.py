import os
from django.shortcuts import render, redirect
from django.http import JsonResponse
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

from .tools import search_financial_news, list_news_by_category, calculate_stock_target_price

# Register active tools list
my_tools = [search_financial_news, list_news_by_category, calculate_stock_target_price]
GEN_MODEL = 'gemini-3.1-flash-lite'  # 生成與決策模型 (Gemini 3.1 Flash 具備極強的工具調用精準度)

def chat_view(request):
    """主對話介面視圖，支援頁面渲染 (GET) 與 AJAX 訊息處理 (POST)"""
    # 確保 session 中的對話歷史結構就緒
    if 'chat_history' not in request.session:
        request.session['chat_history'] = []
        
    chat_history = request.session.get('chat_history', [])
    
    if request.method == 'POST':
        # AJAX 訊息傳送
        user_message = request.POST.get('message', '').strip()
        if not user_message:
            return JsonResponse({'status': 'error', 'message': '請輸入訊息！'})
            
        try:
            # 1. 取得 GenAI 客戶端
            api_key = os.environ.get('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("環境變數中找不到 GEMINI_API_KEY，請確認專案根目錄的 .env 檔案設置正確。")
            client = genai.Client(api_key=api_key)
            
            # 2. 從 session 的對話歷史中，還原成 SDK 的 types.Content 歷史物件
            # 為簡化還原，僅傳遞純文字角色對話歷史
            history_objects = []
            for msg in chat_history:
                history_objects.append(
                    types.Content(
                        role=msg['role'],
                        parts=[types.Part.from_text(text=msg['text'])]
                    )
                )
                
            # 3. 初始化對話 Session，並配置工具箱與 Grounding 系統提示
            chat_session = client.chats.create(
                model=GEN_MODEL,
                history=history_objects,
                config=types.GenerateContentConfig(
                    tools=my_tools,
                    system_instruction=(
                        "你是一位非常專業、嚴謹的高階財經諮詢 Agent。你擁有三個專屬工具：\n"
                        "1. search_financial_news：當使用者詢問新聞、動態、產品特色、重大公告時進行語意資料檢索。\n"
                        "2. list_news_by_category：當使用者需要分類過濾新聞清單時進行精確 SQL 檢索。\n"
                        "3. calculate_stock_target_price：進行 EPS 與本益比相乘之精算。\n\n"
                        "請根據使用者的問題，動態、主動且靈活地調用最合適的工具來回答。你可以根據需要多次連續調用工具。\n"
                        "為了確保回答的專業與精確，你必須嚴格遵守以下原則：\n"
                        "- 【數據接地與標記】：所有的財務回答都必須有具體新聞數據支持，並清楚標記引用出處，格式如：[來源: 新聞編號]。\n"
                        "- 【引用清單】：在回答的最底端，必須建立一個「引用參考來源：」的列表，列出被引用新聞的『新聞編號』與『新聞類別』，並將『新聞連結』格式化為 Markdown 點擊連結（如：[點此閱讀](網址)）。\n"
                        "- 【工具範疇限制】：如果使用者的問題超出了你的三個工具能處理的範圍（例如天氣、體育或日常對話），請禮貌拒絕回答，說明你目前的工具箱僅限於財經諮詢，以防止模型瞎編幻覺。"
                    ),
                    temperature=0.1
                )
            )
            
            # 4. 發送訊息給對話 Session (SDK 會自動在後台執行對應的本地工具並處理 loop)
            response = chat_session.send_message(user_message)
            answer = response.text
            print(f"【模型回答】\n{response}")
            
            # 5. 更新並保存對話歷史到 Session
            chat_history.append({'role': 'user', 'text': user_message})
            chat_history.append({'role': 'model', 'text': answer})
            request.session['chat_history'] = chat_history
            request.session.modified = True
            
            
            return JsonResponse({'status': 'success', 'answer': answer})
            
        except Exception as e:
            error_msg = f"【系統錯誤】Agent 執行時發生異常：{str(e)}"
            return JsonResponse({'status': 'error', 'message': error_msg})
            
    # GET 請求：渲染頁面並帶入歷史紀錄
    request.session.pop('chat_history', None)
    request.session.modified = True
    chat_history = []
    
    return render(request, 'app_rag_agent/chat.html', {'chat_history': chat_history})


def app_intro(request):
    """介紹 Agentic RAG 金融諮詢 APP 的架構與運作方式。"""
    return render(request, 'app_rag_agent/intro.html')


def clear_chat(request):
    """清除當前對話歷史紀錄"""
    if 'chat_history' in request.session:
        del request.session['chat_history']
    return redirect('app_rag_agent:chat_view')
