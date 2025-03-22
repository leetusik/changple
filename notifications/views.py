import django_rq
from django.http import JsonResponse
from django.shortcuts import render

from .tasks import send_notification_email


def send_email_page(request):
    """Render the email send page"""
    return render(request, "notifications/send_email.html")


def send_test_email(request):
    """Send a test email using RQ (web form handler)"""
    if request.method == "POST":
        email = request.POST.get("email", "")
        if not email:
            return JsonResponse(
                {"status": "error", "message": "이메일 주소가 필요합니다."}
            )

        # Queue the email job
        django_rq.enqueue(
            send_notification_email,
            user_email=email,
            subject="Changple 테스트 이메일",
            message="이것은 Changple 알림 기능 테스트 이메일입니다.",
        )

        return JsonResponse(
            {
                "status": "success",
                "message": "이메일이 성공적으로 대기열에 추가되었습니다.",
            }
        )

    return JsonResponse({"status": "error", "message": "POST 요청만 지원합니다."})
