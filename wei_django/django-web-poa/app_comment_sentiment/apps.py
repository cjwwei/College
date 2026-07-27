from django.apps import AppConfig
import sys

class SentimentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_comment_sentiment'
    
    def ready(self):
        # 避免在資料庫遷移或測試時執行排程器
        if 'runserver' in sys.argv:
            from . import scheduler_manager
