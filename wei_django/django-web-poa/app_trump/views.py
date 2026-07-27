from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import pandas as pd


def load_data_trump():
    # Read data from csv file
    df_data = pd.read_csv("app_trump/dataset/chen_shih_chung_data.csv", sep=",")
    global data
    data = {}
    for idx, row in df_data.iterrows():
        data[row['name']] = eval(row['value'])
    del df_data
    return data


# load data
load_data_trump()

def home(request):
  print("home was called!")
  return render(request, "app_trump/home.html", {"article_count_for_django": data['article_count_for_django']})

# csrf_exempt is used for POST
# 單獨指定這一支程式忽略csrf驗證
@csrf_exempt
def api_trump(request):
  print("api_trump was called!")
  return JsonResponse(data)


print("app_trump was loaded!")


# get the frequency of each category
# 讓前端用表格方式顯示 (使用Django Template語法)
"""
          <tbody>
            {% for category, count in article_count_for_django %}
            <tr>
              <td>{{ category }}</td>
              <td>{{ count }}</td>
            </tr>
            {% endfor %}
          </tbody>
"""

