import os
import json
import sqlite3
import numpy as np
from typing import List, Dict, Any
from pathlib import Path
from google import genai

# Dynamically locate the financial_news.db from the app directory
DB_PATH = str(Path(__file__).resolve().parent / 'db' / 'financial_news.db')

EMBED_MODEL = 'gemini-embedding-001'

def get_genai_client() -> genai.Client:
    """取得 API Key 并初始化 Google GenAI SDK 客戶端。"""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError('環境變數中找不到 GEMINI_API_KEY，請確認 .env 檔案設置與金鑰正確性。')
    return genai.Client(api_key=api_key)

def embed_texts(texts: List[str]) -> np.ndarray:
    """呼叫 Gemini Embedding API 將文本陣列轉換為 3072 維度特徵向量矩陣。"""
    client = get_genai_client()
    response = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
    )
    return np.array([emb.values for emb in response.embeddings], dtype=np.float32)

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """計算兩個 NumPy 高維向量的餘弦相似度。"""
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)

def load_all_chunks_with_metadata() -> List[Dict[str, Any]]:
    """透過 SQL JOIN 一次性從資料庫載入所有新聞分塊與 Metadata。"""
    if not os.path.exists(DB_PATH):
        print(f"【錯誤】資料庫檔案不存在: {DB_PATH}")
        raise FileNotFoundError(f"找不到資料庫檔案: {DB_PATH}。請確認資料庫已正確生成。")
        
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            nc.id, 
            nc.news_id, 
            nc.chunk_index, 
            nc.chunk_content, 
            nc.embedding, 
            n.category, 
            n.link
        FROM news_chunks nc
        JOIN news n ON nc.news_id = n.id
    """)
    rows = cur.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            'chunk_id': r[0],
            'news_id': r[1],
            'chunk_index': r[2],
            'chunk_content': r[3],
            'embedding': np.array(json.loads(r[4]), dtype=np.float32),
            'category': r[5],
            'link': r[6]
        })
    return results

# ==========================================
# Agent 專屬工具箱定義
# ==========================================

def search_financial_news(query: str) -> str:
    """當使用者詢問關於台灣財經新聞、半導體產業動態、特定公司（如台積電、聯發科、鴻海）的具體時程、產品特色、重大公告或注意事項時，請使用此工具進行語意資料檢索。

    Args:
        query: 檢索的關鍵字或語意問句。
    """
    print(f"【工具調用】search_financial_news 收到檢索請求: '{query}'")
    try:
        # 1. 取得問句之向量
        query_vec = embed_texts([query])[0]
        
        # 2. 載入資料庫內所有分塊
        all_items = load_all_chunks_with_metadata()
        
        scored_items = []
        for item in all_items:
            sim_score = cosine_similarity(query_vec, item['embedding'])
            scored_items.append((sim_score, item))
            
        scored_items.sort(key=lambda x: x[0], reverse=True)
        
        # 4. 整理前 3 筆最相關片段
        results = []
        for score, item in scored_items[:3]:
            results.append(
                f"【來源: {item['news_id']}】(分類: {item['category']})\n"
                f"內容片段: {item['chunk_content']}\n"
                f"來源網址: {item['link']}"
            )
        return "\n\n---\n\n".join(results)
    except Exception as e:
        return f"【錯誤】search_financial_news 檢索失敗: {str(e)}"

def list_news_by_category(category: str) -> str:
    """當使用者需要列出特定分類（如『半導體產業』、『IC設計』、『科技伺服器』、『封測與元件』、『綠能與基礎設施』）的所有新聞標題、編號與連結時，請使用此工具。此工具會直接從 SQL 資料庫進行分類精確過濾。

    Args:
        category: 新聞分類名稱，例如『IC設計』。
    """
    print(f"【工具調用】list_news_by_category 收到分類查詢請求: '{category}'")
    try:
        if not os.path.exists(DB_PATH):
            raise FileNotFoundError(f"找不到資料庫檔案: {DB_PATH}")
            
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # 直接使用 SQL 精確篩選分類
        cur.execute("SELECT id, link, SUBSTR(content, 1, 60) FROM news WHERE category = ?", (category,))
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            return f"【提示】目前資料庫中找不到分類為『{category}』的新聞。"
        
        results = []
        for r in rows:
            results.append(
                f"新聞編號: {r[0]} | 引用連結: {r[1]}\n"
                f"新聞簡介: {r[2]}..."
            )
        return "\n\n---\n\n".join(results)
    except Exception as e:
        return f"【錯誤】list_news_by_category 執行失敗: {str(e)}"

def calculate_stock_target_price(eps: float, pe_ratio: float) -> str:
    """當使用者需要計算估值、合理股價，或是預估每股盈餘 (EPS) 與合理本益比 (PE Ratio) 進行股價計算時，請使用此工具。

    Args:
        eps: 每股盈餘 (Earnings Per Share)。
        pe_ratio: 合理本益比 (Price-to-Earnings Ratio)。
    """
    print(f"【工具調用】calculate_stock_target_price 收到股價計算請求: eps={eps}, pe_ratio={pe_ratio}")
    try:
        target_price = eps * pe_ratio
        return (
            f"【計算結果】合理目標價為 {target_price:.2f} 元。\n"
            f"計算公式：每股盈餘 (EPS) {eps} 元 * 合理本益比 (P/E Ratio) {pe_ratio} 倍。"
        )
    except Exception as e:
        return f"【錯誤】calculate_stock_target_price 計算失敗: {str(e)}"
