from django.http import JsonResponse
from django.shortcuts import render
import pandas as pd
from datetime import datetime, timedelta
from scipy import stats 

from django.views.decorators.csrf import csrf_exempt
from app_user_keyword.views import df


def load_data_correlation():
    # Read data from csv file
    global df
    df = pd.read_csv(
        'app_correlation_analysis/dataset/cna_news_preprocessed_12weeks.csv', sep='|')
    
# load data
load_data_correlation()


def home(request):
    return render(request, 'app_correlation_analysis/home.html')


@csrf_exempt
def api_get_corr_data(request):
    # (1) get keywords, category, condition, and weeks passed from frontend
    # 使用 .get() 預防 Key 不存在時噴錯，並允許自訂 logic (and/or) 傳入
    userkey1 = request.POST.get('userkey1', '')
    userkey2 = request.POST.get('userkey2', '')
    cond = request.POST.get('cond', 'or') 

    print(userkey2)
    print(type(userkey2))

    userkey1 = userkey1.split()
    userkey2 = userkey2.split()

    # 傳入正確的 cond 參數與 weeks
    pearson_coef, p_value, a_line_xy_data, b_line_xy_data = get_correlation_data(
        userkey1, userkey2, cond=cond, weeks=12
    )

    response = {
        'pearson_coef': pearson_coef,
        'p_value': p_value,
        'a_line_xy_data': a_line_xy_data,
        'b_line_xy_data': b_line_xy_data
    }
    return JsonResponse(response)


def get_correlation_data(queryA, queryB, cond='or', weeks=12):
    # 【修正隱藏 Bug】：明確指定 cond 與 weeks 關鍵字參數，避免 weeks 被誤當成 cond 傳入
    a_line_xy_data, a_freq_data = get_keyword_occurrence_time_series(queryA, cond=cond, weeks=weeks)
    b_line_xy_data, b_freq_data = get_keyword_occurrence_time_series(queryB, cond=cond, weeks=weeks)

    try:
        pearson_coef, p_value = stats.pearsonr(a_freq_data, b_freq_data)
        
        # 安全檢查：防範某一組關鍵字完全查無資料（全為0）時，會算出 NaN 導致後續 round() 噴錯
        if pd.isna(pearson_coef) or pd.isna(p_value):
            return None, None, a_line_xy_data, b_line_xy_data
            
        pearson_coef = round(pearson_coef, 3)
        p_value = round(p_value, 5)
    except:
        # 【修正 500 錯誤】：出錯時保證回傳 4 個元素，避免前端解包 (Unpacking) 數量不符而崩潰
        return None, None, a_line_xy_data, b_line_xy_data

    return pearson_coef, p_value, a_line_xy_data, b_line_xy_data


def get_keyword_occurrence_time_series(query_keywords, cond='or', weeks=12):
    # 安全檢查：若使用者沒輸入任何關鍵字，直接返回空時間點，避免後續 Pandas 報錯
    if not query_keywords:
        end_date = df.date.max()
        return [{'x': end_date, 'y': 0}], [0]

    # end_date
    end_date = df.date.max()
    # start date
    start_date_delta = (datetime.strptime(end_date, '%Y-%m-%d').date() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')
    start_date_min = df.date.min()
    # set start_date as the larger one from the start_date_delta and start_date_min
    start_date = max(start_date_delta,   start_date_min)

    # (1) proceed filtering: a duration of a period of time
    # 期間條件
    period_condition = (df.date >= start_date) & (df.date <= end_date) 

    # (2) proceed filtering: news category
    # and or 條件
    if (cond == 'and'):
        # query keywords condition使用者輸入關鍵字條件and
        condition = period_condition & df.content.apply(lambda text: all((qk in text) for qk in query_keywords)) #寫法:all()
    else:
        # query keywords condition使用者輸入關鍵字條件
        condition = period_condition & df.content.apply(lambda text: any((qk in text) for qk in query_keywords)) #寫法:any()

    # condiction is a list of True or False boolean value
    df_query = df[condition]

    query_freq = pd.DataFrame({'date_index':pd.to_datetime( df_query.date ),'freq':[1 for _ in range(len(df_query))]})

    # 開始時間、結束時間兩項必須也加入到query_freq，計算次數時才會有完整的時間軸，否則時間軸長度會因為新聞時間不同，導致時間軸不一致
    dt_start_date = datetime.strptime(start_date, '%Y-%m-%d')
    dt_end_date = datetime.strptime(end_date, '%Y-%m-%d')    
    
    query_freq = pd.concat([query_freq, pd.DataFrame({'date_index': [dt_start_date], 'freq': [0]})])
    query_freq = pd.concat([query_freq, pd.DataFrame({'date_index': [dt_end_date], 'freq': [0]})])

    freq_data = query_freq.groupby(pd.Grouper(key='date_index', freq='D')).sum()

    freq_data.reset_index(inplace=True)

    # 只有y, 沒有時間變數x
    y_freq_data = freq_data.freq.to_list()
    # 有時間變數x,y
    line_xy_data = [{'x':date.strftime('%Y-%m-%d'),'y':freq} for date, freq in zip(freq_data.date_index,freq_data.freq)]

    return line_xy_data, y_freq_data


print('app_correlation was loaded!')