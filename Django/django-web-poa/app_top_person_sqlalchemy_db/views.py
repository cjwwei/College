from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import pandas as pd

# 🚨 修正 1：導入你原本就建立好的 Django Model 
# (請確認你的 App 名稱是 app_top_person_db 還是 app_top_person_sqlalchemy_db)
from app_top_person_db.models import TopPerson 

def home(request):
    return render(request, 'app_top_person_sqlalchemy_db/home.html')

@csrf_exempt
def api_get_topPerson(request):
    cate = request.POST.get('news_category')
    topk = request.POST.get('topk')
    
    # 防呆機制：確保 topk 有值且為數字
    if not topk:
        topk = 10
    else:
        topk = int(topk)

    # 呼叫改用 Django ORM 的查詢函式
    chart_data, wf_pairs = get_category_topPerson_db(cate, topk)

    response = {
        'chart_data': chart_data,
        'wf_pairs': wf_pairs,
    }
    return JsonResponse(response)


# 🚨 修正 2：重寫查詢函式，拋棄 SQL 語法，改用 Django ORM 
def get_category_topPerson_db(cate, topk):
    try:
        # 使用 Django ORM 進行安全查詢
        # filter(category=cate) 會自動幫你防範 SQL 注入
        result = TopPerson.objects.get(category=cate)
        
        # 解析資料庫中儲存的字串（格式如: "[('唐斯', 12), ('詹姆斯', 8)]"）
        wf_pairs = eval(result.top_keys)[0:topk]
        
    except TopPerson.DoesNotExist:
        # 防呆機制：如果找不到該分類，回傳空陣列
        wf_pairs = []
    except Exception as e:
        print(f"解析資料失敗: {e}")
        wf_pairs = []
        
    # 拆解出前端 Chart.js 需要的標籤與數值
    words = [w for w, f in wf_pairs]
    freqs = [f for w, f in wf_pairs]
    
    chart_data = {
        "category": cate,
        "labels": words,
        "values": freqs
    }
    
    return chart_data, wf_pairs

print("app_news_analysis--類別熱門人物db載入成功!")