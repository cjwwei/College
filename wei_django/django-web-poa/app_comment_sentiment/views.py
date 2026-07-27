from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from .models import Article


def dashboard(request):
    """Render the main dashboard page."""
    return render(request, "app_comment_sentiment/dashboard.html")

def scheduler(request):
    """Render the scheduler management page."""
    return render(request, "app_comment_sentiment/scheduler.html")

def django_command_scheduling_guide(request):
    """Render the Django command scheduling guide page."""
    return render(request, "app_comment_sentiment/django_command_scheduling_guide.html")

def api_data(request):
    """Return JSON data for the frontend."""
    query = request.GET.get("q", "").strip()
    articles = Article.objects.all().order_by("-published_date", "-created_at")

    if query:
        articles = articles.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        )

    data = []

    for article in articles:
        emotion_data = {}
        if hasattr(article, "emotion") and article.emotion is not None:
            emotion = article.emotion
            emotion_data = {
                "cheer_up": emotion.cheer_up,
                "happy": emotion.happy,
                "mixed": emotion.mixed,
                "dumbfounded": emotion.dumbfounded,
                "angry": emotion.angry,
                "sad": emotion.sad,
            }

        # 取前 30 則熱門留言並包含新聞內容
        comments = list(
            article.comments.all()
            .order_by("-upvotes")
            .values("content", "upvotes", "downvotes")[:30]
        )

        item = {
            "id": article.id,
            "title": article.title,
            "category": article.category,
            "url": article.url,
            "content": article.content,
            "published_date": (
                article.published_date.strftime("%Y-%m-%d")
                if article.published_date
                else ""
            ),
            "positive_score": article.positive_score,
            "negative_score": article.negative_score,
            "neutral_score": article.neutral_score,
            "comments_count": article.comments.count(),
            "emotion": emotion_data,
            "analyzed": article.analyzed_at is not None,
            "comments": comments,
        }
        data.append(item)

    return JsonResponse({"articles": data})

import subprocess
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from . import scheduler_manager

@require_http_methods(["GET"])
def api_scheduler_status(request):
    """取得目前排程的運作狀態"""
    status = scheduler_manager.get_job_status()
    return JsonResponse(status)

@csrf_exempt
@require_http_methods(["POST"])
def api_scheduler_start(request):
    """開啟自動排程"""
    scheduler_manager.start_jobs()
    print("排程已啟動")
    return JsonResponse({"status": "success", "message": "排程已啟動"})

@csrf_exempt
@require_http_methods(["POST"])
def api_scheduler_stop(request):
    """停止自動排程"""
    scheduler_manager.stop_jobs()
    print("排程已取消")
    return JsonResponse({"status": "success", "message": "排程已取消"})

@csrf_exempt
@require_http_methods(["POST"])
def api_run_task(request):
    """立即執行單次任務"""
    task = request.POST.get("task", "")
    if task == "scraper":
        # 放背景執行避免前端等待卡住
        subprocess.Popen(["python", "manage.py", "scrape_yahoo"])
        return JsonResponse({"status": "success", "message": "爬蟲任務已在背景啟動"})
    elif task == "analyzer":
        subprocess.Popen(["python", "manage.py", "analyze_sentiment"])
        return JsonResponse({"status": "success", "message": "情緒分析任務已在背景啟動"})
    return JsonResponse({"status": "error", "message": "未知的任務"}, status=400)

@require_http_methods(["GET"])
def api_scheduler_history(request):
    """取得排程執行歷史紀錄"""
    try:
        history = scheduler_manager.get_execution_history()
        return JsonResponse(history)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
