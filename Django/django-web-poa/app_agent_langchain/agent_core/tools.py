from datetime import datetime
from pathlib import Path
import re
import re
from typing import Optional

from langchain_core.tools import tool
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from app_top_keyword.views import get_category_topword
from app_top_person.views import get_category_topPerson
from app_correlation_analysis.views import get_correlation_data
from app_user_keyword_association.views import filter_dataFrame_fullText, get_same_para
from app_user_keyword_db.models import NewsData


load_dotenv()


@tool
def search_and_read_web(query: str) -> str:
    """
    使用關鍵字搜尋網路資訊，並讀取最相關網頁的內容摘要。
    適合用來查詢最新的網路資訊或外部即時新聞（例如：今日新聞、最新政治動態）。
    """
    print(f"\n[Agent Tool] 執行 Tavily 安全搜尋: '{query}'")
    
    # 1. 嘗試呼叫 Tavily API
    try:
        from tavily import TavilyClient
        
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("找不到 TAVILY_API_KEY 環境變數")
            
        client = TavilyClient(api_key=api_key)
        # get_search_context 會直接回傳最適合給 LLM 閱讀的文字串
        response = client.get_search_context(query=query, max_results=3)
        
        if response:
            return response
            
    except Exception as e:
        # 當 401 錯誤或任何網路異常發生時，記錄 Log，但不中斷 Django，啟動 Fallback
        print(f"Tavily 搜尋失敗 ({str(e)})，啟動在地知識庫備援計畫。")

    # 2. 【通用防禦機制】不硬寫特定事件，而是告訴 AI 當前系統連線的真實狀況
    return (
        f"【系統通知：當前外部搜尋引擎 API 驗證受限（401 Unauthorized 或 額度用盡）。】\n"
        f"無法即時連網抓取關於「{query}」的最新網頁內容。\n"
        f"請助理（LLM）委婉向使用者說明目前無法即時連網更新資訊，"
        f"並嘗試根據你現有的知識庫提供協助，或者請使用者換個方式提問。"
    )



@tool
def read_local_document(filepath: str) -> str:
    """Read the content of a local file (e.g., .txt, .md, .csv).
    Use this tool when you need to read local document files to answer user questions.

    Args:
        filepath: 本地檔案的相對路徑或絕對路徑 (例如: 'README.md' 或 'app_agent_genaisdk/第一階段說明.md')。
    """
    print(f"\n[LangChain Tool] 執行 read_local_document(filepath='{filepath}')")

    if not os.path.exists(filepath):
        return f"錯誤：找不到檔案 '{filepath}'。請確認路徑是否正確。"

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 為了避免檔案過長超過 Token 限制，擷取前 4000 個字元
        if len(content) > 4000:
            return f"【檔案內容過長，僅顯示前4000字】\n{content[:4000]}..."
        return content
    except Exception as e:
        return f"讀取檔案時發生錯誤: {str(e)}"


@tool
def save_report_to_file(report_text: str, filename: Optional[str] = None) -> dict:
    """Save generated report text into a local text file.

    Args:
        report_text: The report content that should be written to disk.
        filename: Optional file name without extension. If omitted, a timestamped name is generated.
    """
    # 取得專案根目錄下的 knowledge_base 資料夾
    reports_dir = Path(__file__).resolve().parent.parent.parent / 'knowledge_base'
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 清理 report_text：如果模型在內容前後包了 markdown code block，將其去除
    if report_text.startswith("```"):
        report_text = re.sub(r'^```[\w]*\n|```$', '', report_text, flags=re.MULTILINE)

    if filename:
        safe_name = Path(filename).stem
    else:
        safe_name = datetime.now().strftime('report_%Y%m%d_%H%M%S')

    file_path = reports_dir / f"{safe_name}.txt"
    with file_path.open('w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"[Agent Tool Execution] save_report_to_file 執行完畢，已儲存至 {file_path}\n")
    return {
        "saved_path": str(file_path),
        "message": "Report saved successfully.",
    }
    
    
@tool
def get_latest_article_by_keyword(keyword: str, category: Optional[str] = None, max_chars: int = 1500) -> dict:
    """Get the latest article containing a keyword, optionally filtered by category.

    Args:
        keyword: The keyword to search in article content.
        category: Optional news category filter.
        max_chars: Max characters of content to return to the model.
    """
    print(
        "\n[Agent Tool Execution] 正在執行 get_latest_article_by_keyword(" 
        f"keyword='{keyword}', category='{category}', max_chars={max_chars})..."
    )

    queryset = NewsData.objects.filter(content__contains=keyword)
    if category:
        queryset = queryset.filter(category=category)

    article = queryset.order_by("-date").first()
    if not article:
        print("[Agent Tool Execution] get_latest_article_by_keyword 執行完畢，未找到文章。\n")
        return {"error": "No article found for the given keyword."}

    content = article.content or ""
    if max_chars and len(content) > int(max_chars):
        content = content[: int(max_chars)] + "..."

    print("[Agent Tool Execution] get_latest_article_by_keyword 執行完畢，取得 1 筆資料。\n")
    return {
        "date": article.date.isoformat(),
        "category": article.category,
        "title": article.title,
        "content": content,
        "link": article.link,
    }


@tool
def get_top_keywords(category: str, topk: int = 10) -> list:
    """Get the top keywords and their frequencies for a specific news category."""
    print(f"\n[LangChain Tool] 執行 get_top_keywords(category='{category}', topk={topk})")
    try:
        topk = int(topk)
        _, wf_pairs = get_category_topword(category, topk)
        return [{"keyword": w, "frequency": f} for w, f in wf_pairs]
    except KeyError:
        return [{"error": f"資料庫或系統對應中找不到 '{category}' 這個分類，請嘗試其他分類（如：科技、運動）。"}]
    except Exception as e:
        return [{"error": f"執行失敗: {str(e)}"}]

@tool
def get_top_persons(category: str, topk: int = 5) -> list:
    """Get the most frequently mentioned people in a specific news category."""
    print(f"\n[LangChain Tool] 執行 get_top_persons(category='{category}', topk={topk})")
    try:
        topk = int(topk)
        _, wf_pairs = get_category_topPerson(category, topk)
        return [{"person": w, "frequency": f} for w, f in wf_pairs]
    except KeyError:
        return [{"error": f"系統無法處理 '{category}' 分類的人物統計，可能該分類尚無資料或對應錯誤。"}]
    except Exception as e:
        return [{"error": f"執行失敗: {str(e)}"}]


@tool
def get_keyword_correlation(query_a: str, query_b: str, weeks: int = 12) -> dict:
    """Get the pearson correlation coefficient between two keywords over a specific number of weeks.
    This helps to understand if two keywords are trending together or opposite to each other.

    Args:
        query_a: The first keyword (e.g., '台積電').
        query_b: The second keyword (e.g., '輝達').
        weeks: The number of recent weeks to analyze. Default is 12 weeks.
    """
    print(
        f"\n[LangChain Tool] 執行 get_keyword_correlation(query_a='{query_a}', query_b='{query_b}', weeks={weeks})"
    )
    weeks = int(weeks)
    res = get_correlation_data(query_a, query_b, weeks)
    if res is None:
        return {"error": "No sufficient data found to calculate correlation."}

    pearson_coef, p_value, _, _ = res
    return {
        "keyword_a": query_a,
        "keyword_b": query_b,
        "pearson_correlation": pearson_coef,
        "p_value": p_value,
        "weeks_analyzed": weeks,
    }




"""
(1) Google 也有提供搜尋的API服務，但需要申請 Google Custom Search Engine，並且有每日免費配額限制（100次/天）。如果你想要使用 Google 的搜尋 API，可以參考以下步驟：
1. 前往 Google Custom Search Engine 官網 (https://cse.google.com/cse/)。
2. 建立一個新的搜尋引擎，設定要搜尋的網站（如果想搜尋整個網路，可以在「Sites to search」欄位輸入 `www.google.com`）。
3. 取得搜尋引擎 ID（cx）和 API Key。
4. 使用 Google 的搜尋 API，發送 GET 請求到以下 URL：
https://www.googleapis.com/customsearch/v1?q={query}&cx={cx}&key={API_KEY}
其中 `{query}` 是你的搜尋關鍵字，`{cx}` 是你的搜尋引擎 ID，`{API_KEY}` 是你的 API Key。
不過需要注意的是，Google 的搜尋 API 也有使用限制和配額，如果你需要大量的搜尋次數，可能需要付費升級配額。此外，Google 的搜尋 API 回傳的結果格式比較複雜，需要額外的程式碼來解析和整理成適合 LLM 使用的格式。


(2) DuckDuckGo 的搜尋 API 經常會遇到 401 Unauthorized 的問題，這是因為他們的防爬蟲機制非常嚴格，尤其是對於頻繁的 API 請求。這種情況下，最好的解決方案是改用一個更穩定且專為 AI Agent 設計的搜尋引擎，例如 Tavily。

(3) 改用穩定且免費的 Tavily API
如果你希望這個 Agent 能夠穩定搜尋、不再跟 DuckDuckGo 的防爬蟲機制捉迷藏，最快且最符合 LangChain 生態系的方法就是換成 Tavily。

為什麼推薦 Tavily？

它是 LangChain 官方推薦、專門為 AI Agent 打造的搜尋引擎。

每月提供 1,000 次完全免費的 API 呼叫額度，對開發和中小規模使用完全夠用。

它不需要你用 BeautifulSoup 去痛苦地解析 HTML，它會直接把搜尋結果整理成最適合 LLM 閱讀的乾淨文字摘要。

步驟 1：安裝 Tavily 的 LangChain 整合套件
請在你的虛擬環境終端機執行：

pip install tavily-python
步驟 2：取得免費的 API Key
前往 Tavily 官網 (tavily.com) 註冊一個免費帳號。
https://app.tavily.com/home

在 Dashboard 複製你的 API Key（格式通常是 tvly-....）。

將此 Key 設定到你的 Django .env 檔案中，或者在環境變數中設定：
"""