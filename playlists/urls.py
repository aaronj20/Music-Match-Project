from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('home/', views.home_view, name='home'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/<int:user_id>/', views.profile_view, name='user_profile'),
    path('server_info/', views.server_info, name='server_info'),
    # Playlist URLs
    path('playlists/', views.my_playlists_view, name='my_playlists'),
    path('playlists/create/', views.create_playlist_view, name='create_playlist'),
    path('playlists/<int:playlist_id>/', views.playlist_detail_view, name='playlist_detail'),
    path('playlists/<int:playlist_id>/delete/', views.delete_playlist_view, name='delete_playlist'),
    path('playlists/<int:playlist_id>/add-song/', views.add_song_to_playlist, name='add_song_to_playlist'),
    path('playlists/<int:playlist_id>/remove-song/<int:song_id>/', views.remove_song_from_playlist, name='remove_song_from_playlist'),
    path('playlists/<int:playlist_id>/share/', views.share_playlist_to_community, name='share_playlist_to_community'),
]

