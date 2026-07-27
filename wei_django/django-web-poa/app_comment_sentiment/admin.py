from django.contrib import admin
from .models import Article, Comment, ArticleEmotion


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "published_date",
        "positive_score",
        "negative_score",
        "neutral_score",
        "analyzed_at",
    )
    search_fields = ("title", "content")
    list_filter = ("published_date", "ai_model")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("article", "content_snippet", "upvotes", "downvotes", "replies")
    search_fields = ("content",)

    def content_snippet(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    content_snippet.short_description = "留言內容"


@admin.register(ArticleEmotion)
class ArticleEmotionAdmin(admin.ModelAdmin):
    list_display = (
        "article",
        "cheer_up",
        "happy",
        "mixed",
        "dumbfounded",
        "angry",
        "sad",
        "analyzed_at",
    )
    list_filter = ("ai_model",)
