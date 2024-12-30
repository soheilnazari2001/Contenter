from django.urls import path
from app import views

urlpatterns = [
    path('', views.ContentCreateView.as_view(), name='create_content'),
    path('list', views.ContentListView.as_view(), name='list_content'),
    path('rate', views.RateContentView.as_view(), name='rate_content'),
    path('share/<int:content_id>', views.ShareContentView.as_view(), name='share_content'),
    path('shared/<str:token>', views.GetContentByLinkView.as_view(), name='get_content_by_link'),
]
