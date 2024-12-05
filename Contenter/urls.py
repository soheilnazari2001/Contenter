from django.urls import path
from app import views
from dj_rest_auth.registration.views import RegisterView
from dj_rest_auth.views import LoginView

urlpatterns = [
    path('contents/', views.ContentListView.as_view(), name='content_list'),
    path('contents/<int:content_id>/', views.get_content, name='get_content'),
    path('contents/<int:content_id>/scores/', views.get_content_scores, name='get_content_scores'),
    path('contents/<int:content_id>/scores/create/', views.create_score, name='create_score'),
    path('contents/<int:content_id>/scores/<int:score_id>/update/', views.update_score, name='update_score'),
    path('signup/', RegisterView.as_view(), name='rest_register'),
    path('login/', LoginView.as_view(), name='rest_login'),
]
