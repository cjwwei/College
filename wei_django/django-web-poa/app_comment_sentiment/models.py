from django.db import models
from django.utils import timezone


class Article(models.Model):
    title = models.CharField(max_length=255, verbose_name="新聞標題")
    category = models.CharField(max_length=50, verbose_name="新聞類別", default="政治")
    url = models.URLField(unique=True, max_length=500, verbose_name="新聞網址")
    published_date = models.DateField(verbose_name="發布日期", null=True, blank=True)
    content = models.TextField(verbose_name="新聞內容")

    # 新聞情緒分析結果 (三個面向機率分數 0~1)
    positive_score = models.FloatField(
        null=True, blank=True, verbose_name="正面機率 (0~1)"
    )
    negative_score = models.FloatField(
        null=True, blank=True, verbose_name="負面機率 (0~1)"
    )
    neutral_score = models.FloatField(
        null=True, blank=True, verbose_name="中立機率 (0~1)"
    )

    # AI 追蹤
    ai_model = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="分析使用的 AI 模型"
    )
    analyzed_at = models.DateTimeField(null=True, blank=True, verbose_name="分析時間")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="爬取時間")

    def __str__(self):
        return f"[{self.published_date}] {self.title}"


class Comment(models.Model):
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="所屬新聞",
    )
    content = models.TextField(verbose_name="留言內容")
    upvotes = models.IntegerField(default=0, verbose_name="讚數")
    downvotes = models.IntegerField(default=0, verbose_name="倒讚數")
    replies = models.IntegerField(default=0, verbose_name="回覆數")

    # 若需追蹤個別留言爬取的時間可加入
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="爬取時間")

    def __str__(self):
        return self.content[:30]


class ArticleEmotion(models.Model):
    """
    紀錄該篇新聞「前 30 篇留言」的網民情緒比例總和
    """

    article = models.OneToOneField(
        Article,
        on_delete=models.CASCADE,
        related_name="emotion",
        verbose_name="所屬新聞",
    )

    # 情緒分類百分比 (0~100 或者 0.0~1.0，這裡使用整數百分比做示範)
    cheer_up = models.FloatField(default=0.0, verbose_name="打氣 (%)")
    happy = models.FloatField(default=0.0, verbose_name="開心 (%)")
    mixed = models.FloatField(default=0.0, verbose_name="五味雜陳 (%)")
    dumbfounded = models.FloatField(default=0.0, verbose_name="傻眼 (%)")
    angry = models.FloatField(default=0.0, verbose_name="生氣 (%)")
    sad = models.FloatField(default=0.0, verbose_name="悲傷 (%)")

    # 允許使用不同的 AI 模型針對留言做分析
    ai_model = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="分析使用的 AI 模型"
    )
    analyzed_at = models.DateTimeField(null=True, blank=True, verbose_name="分析時間")

    def __str__(self):
        return f"{self.article.title} - 情緒分析"
