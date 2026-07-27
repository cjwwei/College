import re
import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from app_comment_sentiment.models import Article, ArticleEmotion

from openai import OpenAI
import os
from dotenv import load_dotenv

# pip install openai dotenv

# =======================
# 2. AI 情緒分析
# =======================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

# 使用 REST API 直接呼叫
url = "https://generativelanguage.googleapis.com/v1beta/openai/"


client = OpenAI(
    base_url=url,
    api_key=api_key,
)

model_name = "gemini-3.1-flash-lite"  # 或替換成你使用的 Gemini 模型


class Command(BaseCommand):
    help = "使用 LM Studio 分析尚未處理的新聞情緒與留言情緒"

    def handle(self, *args, **options):

        # 找出尚未分析的新聞
        articles = Article.objects.filter(analyzed_at__isnull=True)
        if not articles.exists():
            self.stdout.write(self.style.SUCCESS("目前沒有需要分析的新聞！"))
            return

        self.stdout.write(f"找到 {articles.count()} 篇新聞等待分析...")

        for article in articles:
            self.stdout.write(self.style.WARNING(f"\n正在分析新聞: {article.title}"))

            self.analyze_all_in_one(client, article)

            # 如果都失敗了，不要寫入完成標記
            if article.ai_model == "ERROR":
                self.stdout.write(
                    self.style.ERROR(f">> 分析失敗，尚未標記為完成: {article.title}")
                )
            else:
                # 標記新聞分析完成
                article.ai_model = model_name
                article.analyzed_at = timezone.now()
                article.save()

                self.stdout.write(self.style.SUCCESS(f">> 完成分析: {article.title}"))

    def analyze_all_in_one(self, client, article):
        comments = article.comments.all().order_by("-upvotes")[:30]
        num_comments = comments.count()

        if num_comments == 0:
            comments_text = "無留言"
        else:
            comments_text = "\n".join(
                [f"{i+1}. {c.content}" for i, c in enumerate(comments)]
            )

        system_prompt = "你是一個精準的新聞與輿情分析系統。你必須嚴格輸出合法的 JSON 格式格式，不要加上 ```json 程式碼區塊標記，也不要有任何其他說明文字。"

        prompt = f"""請針對以下「新聞內容」與「網民留言」進行綜合情緒分析。

【任務一：新聞內容基調分析】
請從新聞內容判斷這篇新聞的基調，分別給出「正面(positive)」、「負面(negative)」、「中立(neutral)」的三個面向機率分數，分數在 0.0 到 1.0 之間，且三個面向加總必須等於 1.0。

【任務二：留言情緒分析】
請將這些留言的整體情緒歸類到六種標籤中，並計算其佔比 (總和需為100%)。如果「無留言」，請全部給 0。
標籤為：cheer_up(打氣)、happy(開心)、mixed(五味雜陳)、dumbfounded(傻眼)、angry(生氣)、sad(悲傷)。

務必只輸出如下的 JSON 格式：
{{
  "article_sentiment": {{
    "positive_score": 0.2,
    "negative_score": 0.3,
    "neutral_score": 0.5
  }},
  "comments_emotion": {{
    "cheer_up": 10,
    "happy": 0,
    "mixed": 30,
    "dumbfounded": 47,
    "angry": 10,
    "sad": 3
  }}
}}

【新聞內容】
{article.content[:1000]}

【網民留言】
{comments_text}"""

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1, # 固定輸出，避免同一內容每次分析結果不同
            )
            result = response.choices[0].message.content.strip()

            # 清理可能的 markdown
            result = re.sub(r"^```json\s*", "", result)
            result = re.sub(r"```\s*$", "", result)

            data = json.loads(result)

            # 儲存新聞機率
            art_sent = data.get("article_sentiment", {})
            article.positive_score = float(art_sent.get("positive_score", 0.0))
            article.negative_score = float(art_sent.get("negative_score", 0.0))
            article.neutral_score = float(art_sent.get("neutral_score", 0.0))

            # 儲存留言情緒
            emotion, _ = ArticleEmotion.objects.get_or_create(article=article)
            emotions_data = data.get("comments_emotion", {})
            emotion.cheer_up = float(emotions_data.get("cheer_up", 0))
            emotion.happy = float(emotions_data.get("happy", 0))
            emotion.mixed = float(emotions_data.get("mixed", 0))
            emotion.dumbfounded = float(emotions_data.get("dumbfounded", 0))
            emotion.angry = float(emotions_data.get("angry", 0))
            emotion.sad = float(emotions_data.get("sad", 0))

            emotion.ai_model = model_name
            emotion.analyzed_at = timezone.now()
            emotion.save()

            if article.ai_model == "ERROR":
                article.ai_model = None

            self.stdout.write(f"[分析成功] 留言情緒: {emotions_data}")

        except Exception as e:
            article.ai_model = "ERROR"
            self.stdout.write(
                self.style.ERROR(
                    f"[分析失敗] 錯誤：{e}\n回傳內容：{result if 'result' in locals() else '無'}"
                )
            )
