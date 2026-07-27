from django.contrib import admin
from django.urls import path
from django.urls import include

urlpatterns = [
    # top keywords
    path('topword/', include('app_top_keyword.urls')),
    # app top persons
    path('topperson/', include('app_top_person.urls')),
    # top ner
    path('topner/', include('app_top_ner.urls')),
    # user keyword analysis
    path('userkeyword/', include('app_user_keyword.urls')),
    
    #app_trump
    path('trump/', include('app_trump.urls')),
   
    # full text search and associated keyword display
    path('userkeyword_assoc/', include('app_user_keyword_association.urls')),
    
    # app movies
    path('movies/', include('app_movies.urls')),
    
    # user keyword sentiment 
    path('userkeyword_senti/', include('app_user_keyword_sentiment.urls')),
    
    # politics mayor election
    path('', include('app_taipei_mayor.urls')),

    #user_keyword_db/admin
    path('userkeyword_db/', include('app_user_keyword_db.urls')),
    path('admin/', admin.site.urls),

    # Yahoo comment sentiment
    path("comment_sentiment/", include("app_comment_sentiment.urls")),

    # News classification
    #path('news_cls/', include('app_news_classification_bert.urls')),
    
    # news recommendation with bert
    #path('news_rcmd/', include('app_news_rcmd_bert.urls')),

    # user keyword report with llm
    path('userkeyword_report/', include('app_user_keyword_llm_report.urls')),

    # correlation
    path('correlation/', include('app_correlation_analysis.urls')),

    # top k person using db
    path('topperson_db/', include('app_top_person_db.urls')),
    
    # top k person using db
    path('topperson_sqlalchemy_db/', include('app_top_person_sqlalchemy_db.urls')),

    path('poa_intro/', include('app_course_intro.urls')),
    
    # POA Agent
    path("agent_genaisdk/", include("app_agent_genaisdk.urls")),
    path("agent_langchain/", include("app_agent_langchain.urls")),
    path("agent_langgraph/", include("app_agent_langgraph.urls")),

    #POA RAG
    path("rag_basic/", include("app_rag_basic.urls")),
    path("rag_agent/", include("app_rag_agent.urls")),

    # course introduction
    path('poa_intro/', include('app_course_intro.urls')),

    # api introduction
    #path('api_intro', TemplateView.as_view(template_name='introduction-of-poa/api-introduction.html'), name='api_introduction'),
]
