from django.shortcuts import render
from django.http import JsonResponse
from .graph_core.graph_agent import run_custom_graph


def chat_view(request):
    """
    Renders the Chat interface for Custom LangGraph (Phase 3)
    """
    if "custom_graph_history" not in request.session:
        request.session["custom_graph_history"] = []

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "clear":
            request.session["custom_graph_history"] = []
            return JsonResponse({"reply": "第三階段圖結構記憶已清除！"})

        user_message = request.POST.get("message", "")
        if not user_message:
            return JsonResponse({"error": "Message is empty"}, status=400)

        try:
            print(f"=== [Phase 3 - Custom Graph Agent] 開始處理請求 ===")
            print(f"User Message: {user_message}")

            history = request.session["custom_graph_history"]

            # 丟給第三階段的 Graph 處理
            bot_reply, new_history = run_custom_graph(user_message, history)

            request.session["custom_graph_history"] = new_history
            request.session.modified = True

            print(f"=== [Phase 3 - Custom Graph Agent] 請求處理完成 ===")
            return JsonResponse({"reply": bot_reply})
        except Exception as e:
            print(f"=== [Phase 3 - Custom Graph Agent] 發生錯誤: {str(e)} ===")
            return JsonResponse({"error": str(e)}, status=500)

    return render(request, "app_agent_langgraph/home.html")
