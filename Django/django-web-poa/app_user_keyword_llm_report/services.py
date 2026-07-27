# your_app/services.py
from django.conf import settings
from openai import OpenAI

def ask_gemini_via_openai(prompt: str) -> str:
    """
    使用 OpenAI SDK 接口呼叫 Gemini 3.1 Flash Lite 服務
    """
    url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    
    # 初始化客戶端（settings.GEMINI_API_KEY 是從 .env 讀進來的）
    client = OpenAI(
        base_url=url,
        api_key=settings.GEMINI_API_KEY,
    )
    
    try:
        completion = client.chat.completions.create(
            model="gemini-3.1-flash-lite", # 也可以用你在 notebook 測試的 gemma-4-26b-a4b-it
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI 呼叫失敗: {str(e)}"