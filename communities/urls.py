from django.urls import path
from . import views

urlpatterns = [
    path('explore/', views.explore_view, name='explore'),
    path('create/', views.create_community_view, name='create_community'),
    path('community/<int:community_id>/', views.community_detail_view, name='community_detail'),
    path('community/<int:community_id>/join/', views.join_community_view, name='join_community'),
    path('community/<int:community_id>/leave/', views.leave_community_view, name='leave_community'),
    path('community/<int:community_id>/delete/', views.delete_community_view, name='delete_community'),
    path('community/<int:community_id>/message/', views.send_message_view, name='send_message'),
]

