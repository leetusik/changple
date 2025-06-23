from django.urls import path
from . import views

app_name = "content_uploader"

urlpatterns = [
    path("view/<int:content_id>/", views.view_html_content, name="view_html_content"),
    path("api/notion-content-list/", views.notion_content_list, name="notion_content_list"),
]

# 사용 예시
# <!-- my_template.html -->
# <ul>
#     {% for content in contents %}
#     <li>
#         <a href="{% url 'content_uploader:view_html_content' content_id=content.id %}">
#             {{ content.title }}
#         </a>
#     </li>
#     {% endfor %}
# </ul>