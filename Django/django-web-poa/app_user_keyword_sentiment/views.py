from django.http import JsonResponse
from django.shortcuts import render
import pandas as pd
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt

# 宣告全域變數 df
df = None

# 💡 修正 1：啟動時讀取自己 App 路徑下的本地檔案
def load_df_data_v1():
    global df
    try:
        df = pd.read_csv('app_user_keyword_sentiment/dataset/news_dataset.csv', sep='|')
        print("本地新聞資料庫載入成功！")
    except Exception as e:
        print(f"載入檔案失敗，請檢查路徑。錯誤訊息: {e}")

# 執行載入檔案
load_df_data_v1()


# 💡 修正 2：建立屬於自己本地的資料過濾函式（不用再跟隔壁 App 借）
def filter_dataFrame_local(query_keywords, cond, cate, weeks):
    global df
    if df is None:
        return pd.DataFrame() # 防呆：如果 df 沒載入成功，回傳空表格
        
    # 計算時間區間
    end_date = df.date.max()
    start_date_delta = (datetime.strptime(end_date, '%Y-%m-%d').date() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')
    start_date_min = df.date.min()
    start_date = max(start_date_delta, start_date_min)

    # 1. 期間條件
    condition = (df.date >= start_date) & (df.date <= end_date) 
    
    # 2. 類別條件
    if cate != "全部":
        condition = condition & (df.category == cate)

    # 3. 關鍵字 And / Or 條件 (轉換成字串防呆)
    if cond == 'and':
        condition = condition & df.content.apply(lambda text: all((qk in str(text)) for qk in query_keywords))
    elif cond == 'or':
        condition = condition & df.content.apply(lambda text: any((qk in str(text)) for qk in query_keywords))
        
    return df[condition]


def home(request):
    return render(request, 'app_user_keyword_sentiment/home.html')


# 💡 修正 3：只保留本地處理的 API，移除原本呼叫遠端的那段 View
@csrf_exempt
def api_get_userkey_sentiment(request):
    userkey = request.POST.get('userkey', '')
    cate = request.POST.get('cate', '全部')
    cond = request.POST.get('cond', 'or')
    weeks = int(request.POST.get('weeks', 12))
 
    # 進行本地處理資料
    query_keywords = userkey.split()
    
    # 使用我們剛剛建立的本地過濾函式
    df_query = filter_dataFrame_local(query_keywords, cond, cate, weeks)
    
    # 如果查無資料，回傳錯誤訊息
    if len(df_query) == 0:
        return JsonResponse({'error': 'No results found for the given keywords.'})
    
    sentiCount, sentiPercnt = get_article_sentiment(df_query)

    if weeks <= 4:
        freq_type = 'D'
    else:
        freq_type = 'W'

    line_data_pos = get_daily_basis_sentiment_count(df_query, sentiment_type='pos', freq_type=freq_type)
    line_data_neg = get_daily_basis_sentiment_count(df_query, sentiment_type='neg', freq_type=freq_type)

    response = {
        'sentiCount': sentiCount,
        'data_pos': line_data_pos,
        'data_neg': line_data_neg,
    }
    return JsonResponse(response)


def get_article_sentiment(df_query):
    sentiCount = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    sentiPercnt = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    numberOfArticle = len(df_query)
    
    for senti in df_query.sentiment:
        if float(senti) >= 0.6:
            sentiCount['Positive'] += 1
        elif float(senti) <= 0.4:
            sentiCount['Negative'] += 1
        else:
            sentiCount['Neutral'] += 1
            
    for polar in sentiCount:
        try:
            sentiPercnt[polar] = int(sentiCount[polar] / numberOfArticle * 100)
        except ZeroDivisionError:
            sentiPercnt[polar] = 0 
            
    return sentiCount, sentiPercnt


def get_daily_basis_sentiment_count(df_query, sentiment_type='pos', freq_type='D'):
    if sentiment_type == 'pos':
        lambda_function = lambda senti: 1 if float(senti) >= 0.6 else 0 
    elif sentiment_type == 'neg':
        lambda_function = lambda senti: 1 if float(senti) <= 0.4 else 0
    elif sentiment_type == 'neutral':
        # 💡 修正原本寫錯的位元運算子 `&` -> 應該是邏輯 `and`
        lambda_function = lambda senti: 1 if (float(senti) > 0.4 and float(senti) < 0.6) else 0
    else:
        return None 
        
    freq_df = pd.DataFrame({
        'date_index': pd.to_datetime(df_query.date),
        'frequency': [lambda_function(senti) for senti in df_query.sentiment]
    })
    
    freq_df_group = freq_df.groupby(pd.Grouper(key='date_index', freq=freq_type)).sum()
    freq_df_group.reset_index(inplace=True)
    
    xy_line_data = [{'x': date.strftime('%Y-%m-%d'), 'y': int(freq)} for date, freq in zip(freq_df_group.date_index, freq_df_group.frequency)]
    return xy_line_data


print("app_userkey_sentiment was loaded!")