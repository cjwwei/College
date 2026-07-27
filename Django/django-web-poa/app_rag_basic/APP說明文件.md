

這段程式碼實作了一個基於 **Retrieval-Augmented Generation (RAG)** 的 Django 應用程式，主要功能是讓使用者上傳 PDF 文件，系統會將文件內容向量化並存儲在記憶體中的 FAISS 向量索引裡，接著使用者可以提出自然語言問題，系統會從向量庫中檢索最相關的文本片段，並交由 Google Gemini 生成模型產出回答。

以下是各部分的說明：

---

### 1. 全域變數與初始化
```python
_vector_db_texts = []          # 儲存對應的文本 chunk（字串列表）
_faiss_index = faiss.IndexFlatL2(3072)  # FAISS 向量索引，維度 3072（對應 Gemini Embedding 模型）
```
- 這兩個變數是 **全域變數**，用來在記憶體中保存向量資料庫的狀態。
- `_vector_db_texts` 保存每個文字 chunk 的原始內容（含來源檔案標籤）。
- `_faiss_index` 是 FAISS 的 L2 距離索引，用於快速相似度搜尋。
- 注意：這些資料僅存在於記憶體中，**伺服器重啟後會消失**（除非額外實作持久化）。

---

### 2. Django View：`rag_demo_view(request)`
這是 Django 的視圖函式，負責處理網頁請求（GET/POST）：
- **GET 請求**：只會渲染模板 `app_poa_rag/rag_demo.html`，並傳入 `has_vectorstore`（判斷向量庫是否有資料）來控制前端按鈕狀態。
- **POST 請求**：根據 `action` 欄位執行不同操作：
  - `upload`：處理上傳的 PDF 檔案（呼叫 `process_uploaded_pdf`）。
  - `query`：執行 RAG 查詢（呼叫 `query_rag`）。
  - `clear`：清空向量庫（重設 `_vector_db_texts` 和 `_faiss_index`）。

---

### 3. 核心 RAG 邏輯函式

#### (1) `get_genai_client()`
- 從環境變數讀取 `GEMINI_API_KEY`，並回傳 Google GenAI 的客戶端實例。
- 若未設定 API Key 會拋出錯誤。

#### (2) `process_uploaded_pdf(file_obj)`
- **功能**：處理使用者上傳的 PDF 檔案，將其轉換為向量並存入 FAISS。
- **步驟**：
  1. 將上傳的 PDF 暫存至 `TEMP_DIR` 資料夾。
  2. 使用 `pypdf` 讀取 PDF 內容（逐頁提取文字）。
  3. 將文字簡單切塊（每 800 個字為一塊，重疊 150 個字），每塊前面加上 `[來源檔案：{file_name}]` 標籤。
  4. 呼叫 Gemini 的 `gemini-embedding-001` 模型對所有 chunk 進行向量化。
  5. 將得到的向量（轉為 `float32`）加入 FAISS 索引，並將原始文字 chunk 加入 `_vector_db_texts` 列表。
  6. 最後在 `finally` 區塊中刪除暫存的 PDF 檔案，避免佔用磁碟空間。

#### (3) `query_rag(query_text)`
- **功能**：根據使用者的問題，從向量庫中檢索相關內容並生成回答。
- **步驟**：
  1. 檢查 FAISS 是否有資料（`_faiss_index.ntotal == 0`），若無則提示請先上傳 PDF。
  2. 使用同樣的 `gemini-embedding-001` 模型將使用者的問題向量化。
  3. 在 FAISS 中執行相似度搜尋（取前 3 名最相似的向量）。
  4. 根據搜尋到的索引，從 `_vector_db_texts` 中取出對應的原始文字 chunk。
  5. 將這些 chunk 合併成一段「Context」。
  6. 建立系統提示（System Prompt），告訴 Gemini 模型要根據提供的 Context 回答問題，最多三句話。
  7. 呼叫 Gemini 的 `gemini-3.1-flash-lite` 模型生成最終回答。

---

### 4. 重要說明（檔案末尾的註解）
- 目前向量資料僅存在於記憶體中（`_faiss_index` 和 `_vector_db_texts`），伺服器重新啟動或 Django 載入後會消失。
- 若要實現 **持久化儲存**，可以：
  1. 將 FAISS 索引寫入磁碟：`faiss.write_index(_faiss_index, "path/to/index.faiss")`，啟動時用 `faiss.read_index()` 讀回。
  2. 將文字 chunk 存成 JSON、Pickle 或資料庫。
  3. 或者直接改用支持久化的向量資料庫（如 Milvus、Qdrant、PostgreSQL + pgvector 等）。

---

### 總結
這是一個典型的 **「上傳文件 → 向量化存儲 → 檢索相關片段 → 生成回答」的 RAG 流程**，適合用於建構基於私人文件的問答系統。其優點是實作簡單、即時響應；缺點是向量庫不持久化，適合作為 Demo 或暫時性使用。若要投入正式環境，需加入向量庫的儲存與載入機制。