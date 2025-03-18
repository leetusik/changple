"""config URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from users.views import home_view, login_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("django-rq/", include("django_rq.urls")),  # Add RQ dashboard URLs
    path("users/", include("users.urls")),  # Include the users app URLs
    path("", home_view, name="home"),  # Use home_view to handle redirects
    path("login/", login_view, name="login"),  # Add explicit login URL
    path(
        "mypage/", RedirectView.as_view(url="/users/mypage/"), name="mypage_redirect"
    ),  # Redirect to users mypage
]
