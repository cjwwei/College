import os
import numpy as np
import faiss
from pypdf import PdfReader
from google import genai
from google.genai import types
from django.shortcuts import render
from django.conf import settings

# ==========================================
# 1. 全域變數與初始化
# ==========================================
TEMP_DIR = os.path.join(settings.BASE_DIR, "app_rag_basic", "temp_files")
os.makedirs(TEMP_DIR, exist_ok=True)

# 儲存對應的文本內容 (存在記憶體中)
_vector_db_texts = []
# 配合 2026 最新 Gemini 嵌入模型，將維度升級為 3072
_faiss_index = faiss.IndexFlatL2(3072)



# ==========================================
# Django View 視圖 (負責接收網頁請求)
# ==========================================
def rag_demo_view(request):
    # 檢查 FAISS 中是否有資料，來決定前端按鈕狀態
    context = {"has_vectorstore": _faiss_index.ntotal > 0}

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "upload":
            pdf_file = request.FILES.get("pdf_file")
            if pdf_file:
                message = process_uploaded_pdf(pdf_file)
                context["upload_message"] = message
                context["has_vectorstore"] = _faiss_index.ntotal > 0
            else:
                context["upload_message"] = "請選擇檔案！"

        elif action == "query":
            query_text = request.POST.get("query")
            if query_text:
                answer = query_rag(query_text)
                context["answer"] = answer
                context["query"] = query_text # 幫使用者在畫面上保留剛輸入的問題

        elif action == "clear":
            _vector_db_texts.clear()
            _faiss_index.reset()
            context["upload_message"] = "已經成功清空所有文件的向量庫資料！"
            context["has_vectorstore"] = False

    return render(request, "app_rag_basic/rag_demo.html", context)


# ==========================================
# 2. 核心 RAG 邏輯函式
# ==========================================
def get_genai_client():
    """取得 Google 官方 SDK Client"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("環境變數中找不到 GEMINI_API_KEY！請確認 .env 設定。")
    return genai.Client(api_key=api_key)


def process_uploaded_pdf(file_obj):
    """讀取 PDF、切塊，並將向量存入 FAISS"""
    global _vector_db_texts, _faiss_index

    # 移除自動清空邏輯，改為疊加存入
    # _vector_db_texts.clear()
    # _faiss_index.reset()

    file_path = os.path.join(TEMP_DIR, file_obj.name)
    with open(file_path, "wb+") as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)

    try:
        # 使用 pypdf 讀取文字
        reader = PdfReader(file_path)
        raw_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                raw_text += text + "\n"

        # 簡單切塊 (每 800 字切一塊，重疊 150 字)
        chunk_size = 800
        overlap = 150
        chunks = []
        start = 0
        while start < len(raw_text):
            end = start + chunk_size
            # 加上檔案來源標籤(檔案名稱)，使用者提問若有跨文件的搜尋，可以較為精確
            chunks.append(f"[來源檔案：{file_obj.name}]\n" + raw_text[start:end])
            start += chunk_size - overlap
        
        if not chunks:
            return "檔案中找不到任何可讀取的文字。"

        # 呼叫 Gemini 進行 Embedding
        client = get_genai_client()
        # 🔥 [重大修正] 使用最新官方標準名稱：gemini-embedding-001
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=chunks,
        )

        # 將向量轉為 FAISS 需要的 float32 格式
        vectors = np.array([emb.values for emb in response.embeddings], dtype=np.float32)
        
        # 存入 FAISS 與全域變數
        _faiss_index.add(vectors)
        _vector_db_texts.extend(chunks)

        return f"成功處理檔案：{file_obj.name}，共切分為 {len(chunks)} 個文本塊。"
    # 結束後自動刪除 PDF暫存檔，確保不佔用磁碟空間
    finally:
        # 確保無論如何都刪除暫存的 PDF
        if os.path.exists(file_path):
            os.remove(file_path)


"""
向量模型是怎麼插入 prompt 裡的？
使用者的問題 query_text 先被轉成向量
這個向量用來在 FAISS 裡做相似度搜尋
搜到最相關的文件段落（docs）
再把這些文件段落「轉成文字」並放入 prompt 裡
"""
def query_rag(query_text):
    """將問題向量化，從 FAISS 檢索文本後，交由 Gemini 回答"""
    global _vector_db_texts, _faiss_index

    # ntotal 代表目前 FAISS 索引中存了幾筆向量
    if _faiss_index.ntotal == 0:
        return "請先上傳 PDF 檔案！"

    client = get_genai_client()

    # 1. 將使用者的問題向量化
    # 🔥 [重大修正] 查詢時的 Embedding 也要同步使用 gemini-embedding-001
    query_resp = client.models.embed_content(
        model="gemini-embedding-001",
        contents=query_text,
    )
    query_vector = np.array([query_resp.embeddings[0].values], dtype=np.float32)

    # 2. FAISS 相似度搜尋 (找出前 3 名)
    distances, indices = _faiss_index.search(query_vector, 3)

    # 根據 FAISS 找出的索引，把對應的文本抓出來
    top_k_contexts = []
    for idx in indices[0]:
        if idx != -1 and idx < len(_vector_db_texts):
            top_k_contexts.append(_vector_db_texts[idx])
    
    # 印出檢索到的 chunk 到 Server console
    print("[RAG] Retrieved chunks:")
    for i, chunk in enumerate(top_k_contexts, start=1):
        print(f"--- chunk {i} ---")
        print(chunk)
        print("--------------")

    merged_context = "\n\n---\n\n".join(top_k_contexts)

    # 3. 組裝 Prompt 並呼叫 Gemini 生成回答
    system_prompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer the question. "
        "If you don't know the answer, say that you don't know. "
        "Use three sentences maximum and keep the answer concise.\n\n"
        f"Context:\n{merged_context}"
    )

    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=query_text,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
        ),
    )

    return response.text

"""
- `TEMP_DIR` 只儲存上傳的 PDF 暫存檔
- 向量化後的資料不是寫到硬碟，而是存在記憶體裡
  - `_faiss_index`：FAISS 的向量索引，存在記憶體
  - `_vector_db_texts`：記錄對應文本 chunk 的清單，也存在記憶體

所以目前程式重啟或重新載入後，向量庫就會消失。

## 如果要儲存向量

可以改成「持久化儲存」，例如：

1. FAISS 存成磁碟檔：
   - `faiss.write_index(_faiss_index, "path/to/index.faiss")`
   - 啟動時用 `faiss.read_index(...)` 讀回
2. 文本 chunk 也要一起存成 JSON / pickle / DB
3. 或改用資料庫/向量數據庫（比如 SQLite、PostgreSQL、Milvus、Qdrant）

目前你的程式不是把向量化結果存成檔案，而是暫存在記憶體中，這是可行的，
但如果你想讓它在伺服器重啟後繼續使用，就需要額外加上儲存/載入邏輯。
"""