from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Q, Max, F

from datetime import datetime, timedelta
import pandas as pd

# Import the NewsData model
from .models import NewsData

# 匯入其他 app 的 DataFrame 共用函數
from app_user_keyword_association.views import (
    get_title_link_topk,
    get_related_word_clouddata,
    get_same_para,
)

from app_user_keyword.views import get_keyword_time_based_freq

from app_user_keyword_sentiment.views import get_article_sentiment


# For the key association analysis
def home(request):
    return render(request, "app_user_keyword_db/home.html")


@csrf_exempt
def api_get_userkey_data(request):
    userkey = request.POST.get("userkey")
    cate = request.POST["cate"]  # This is an alternative way to get POST data.
    cond = request.POST.get("cond")
    weeks = int(request.POST.get("weeks"))
    key = userkey.split()

    # Get query results from database
    # 使用 ORM 來過濾資料庫的資料
    # 這裡的 queryset 是一個 QuerySet 對象，包含了符合條件的所有新聞資料
    queryset = filter_database_fullText(key, cond, cate, weeks)
    # 使用原生 SQL 來過濾資料庫的資料 也可以
    # queryset = filter_database_fullText_SQL(key, cond, cate, weeks)

    print(f"Query returned {queryset.count()} results")

    # Check if the result is empty
    if not queryset.exists():  # queryset is not empty
        return JsonResponse({"error": "No results found for the given keywords."})

    # 將 queryset 轉換為 DataFrame，之後共用其他的資料分析函數
    df_query = pd.DataFrame(
        list(
            queryset.values(
                "date",
                "category",
                "title",
                "content",
                "link",
                "photo_link",
                "top_key_freq",
                "sentiment",
            )
        )
    )

    # get the data for showing news articles, related words, and word cloud
    newslinks = get_title_link_topk(df_query, k=10)
    related_words, clouddata = get_related_word_clouddata(df_query)
    same_paragraph = get_same_para(df_query, key, cond, k=6)  # multiple keywords
    # num_articles = queryset.count()  # total number of articles (stories, items)
    num_articles = len(df_query)  # total number of articles (stories, items)

    response_article_info = {
        "newslinks": newslinks,
        "same_paragraph": same_paragraph,
        "clouddata": clouddata,
        "num_articles": num_articles,
    }

    # time-based keyword frequency chart data
    key_time_freq = get_keyword_time_based_freq(df_query)  # OK 使用 pandas 很方便
    response_time_occurrence = {
        "key_time_freq": key_time_freq,
    }

    # piechart for sentiment distribution
    sentiCount, sentiPercnt = get_article_sentiment(df_query)
    response_sentiment = {
        "sentiCount": sentiCount,
    }

    # Combine dictionaries correctly
    combined_response = {
        **response_article_info,
        **response_time_occurrence,
        **response_sentiment,
    }
    return JsonResponse(combined_response)


# Searching keywords from "content" column
# This function now uses database queries instead of pandas
def filter_database_fullText(user_keywords, cond, cate, weeks):
    # def filter_database_fullText_ORM(user_keywords, cond, cate, weeks):
    # Get the latest date in the database
    latest_date = NewsData.objects.aggregate(max_date=Max("date"))["max_date"]

    # Calculate start date
    start_date = latest_date - timedelta(weeks=weeks)

    # Base query - filter by date range
    queryset = NewsData.objects.filter(date__gte=start_date, date__lte=latest_date)

    # Filter by category if not "全部"
    if cate != "全部":
        queryset = queryset.filter(category=cate)

    # Filter by keywords based on condition (AND or OR)
    if cond == "and":
        # For AND condition, we need all keywords to be present
        for kw in user_keywords:
            queryset = queryset.filter(content__contains=kw)
    elif cond == "or":
        # For OR condition, any keyword can be present |  ||
        q_objects = Q()
        for kw in user_keywords:
            q_objects |= Q(content__contains=kw)
        queryset = queryset.filter(q_objects)

    return queryset


print("app_user_keyword_db versions loaded!")
