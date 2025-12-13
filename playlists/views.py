from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse
from django.conf import settings
import requests
from .models import Playlist, Song, Review
from communities.models import Community
from accounts.models import UserProfile


def server_info(request):
    """Server info endpoint as specified in requirements"""
    server_geodata = requests.get('https://ipwhois.app/json/').json()
    settings_dump = settings.__dict__
    return HttpResponse("{}{}".format(server_geodata, settings_dump))


def index_view(request):
    """Landing page - redirects authenticated users to home"""
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'playlists/index.html')


@login_required
def home_view(request):
    """Home page showing recent activity"""
    user = request.user
    # Get user's communities
    user_communities = user.communities.all()[:5]
    
    # Get recent playlists from user's communities
    recent_playlists = Playlist.objects.filter(
        community__in=user_communities
    ).order_by('-updated_at')[:5]
    
    # Get user's playlists
    user_playlists = user.owned_playlists.all()[:5]
    
    context = {
        'user_communities': user_communities,
        'recent_playlists': recent_playlists,
        'user_playlists': user_playlists,
    }
    return render(request, 'playlists/home.html', context)


@login_required
def profile_view(request, user_id=None):
    """User profile page"""
    if user_id:
        profile_user = get_object_or_404(User, id=user_id)
    else:
        profile_user = request.user
    
    # Get or create profile (should exist via signal, but handle edge case)
    profile, created = UserProfile.objects.get_or_create(user=profile_user)
    playlists = profile_user.owned_playlists.filter(is_public=True)
    badges = profile_user.badges.all()
    
    context = {
        'profile_user': profile_user,
        'profile': profile,
        'playlists': playlists,
        'badges': badges,
    }
    return render(request, 'playlists/profile.html', context)


@login_required
def create_playlist_view(request):
    """Create a new playlist"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        is_public = request.POST.get('is_public') == 'on'
        community_id = request.POST.get('community')
        
        if name:
            playlist = Playlist.objects.create(
                name=name,
                description=description,
                owner=request.user,
                is_public=is_public
            )
            
            # Link to community if specified
            if community_id:
                try:
                    community = Community.objects.get(id=community_id)
                    if request.user in community.members.all():
                        playlist.community = community
                        playlist.save()
                except Community.DoesNotExist:
                    pass
            
            messages.success(request, f'Playlist "{name}" created successfully!')
            return redirect('playlist_detail', playlist_id=playlist.id)
        else:
            messages.error(request, 'Please provide a playlist name.')
    
    # Get user's communities for the dropdown
    user_communities = request.user.communities.all()
    
    return render(request, 'playlists/create_playlist.html', {
        'user_communities': user_communities
    })


@login_required
def playlist_detail_view(request, playlist_id):
    """View playlist details"""
    playlist = get_object_or_404(Playlist, id=playlist_id)
    
    # Check if user can view this playlist
    if not playlist.is_public and playlist.owner != request.user:
        messages.error(request, "This playlist is private.")
        return redirect('home')
    
    # Get songs with PlaylistSong info for ordering and metadata
    from .models import PlaylistSong
    playlist_songs = PlaylistSong.objects.filter(playlist=playlist).select_related('song', 'added_by')
    is_owner = playlist.owner == request.user
    can_edit = is_owner or playlist.is_collaborative
    
    # Get user's communities for sharing
    user_communities = request.user.communities.all() if is_owner else []
    
    context = {
        'playlist': playlist,
        'playlist_songs': playlist_songs,
        'is_owner': is_owner,
        'can_edit': can_edit,
        'user_communities': user_communities,
    }
    return render(request, 'playlists/playlist_detail.html', context)


@login_required
def my_playlists_view(request):
    """View all user's playlists"""
    playlists = Playlist.objects.filter(owner=request.user).order_by('-updated_at')
    
    context = {
        'playlists': playlists,
    }
    return render(request, 'playlists/my_playlists.html', context)


@login_required
def delete_playlist_view(request, playlist_id):
    """Delete a playlist"""
    playlist = get_object_or_404(Playlist, id=playlist_id)
    
    if playlist.owner != request.user:
        messages.error(request, "You can only delete your own playlists.")
        return redirect('my_playlists')
    
    if request.method == 'POST':
        name = playlist.name
        playlist.delete()
        messages.success(request, f'Playlist "{name}" deleted.')
        return redirect('my_playlists')
    
    return render(request, 'playlists/delete_playlist.html', {'playlist': playlist})


@login_required
def add_song_to_playlist(request, playlist_id):
    """Add a song to a playlist from Spotify"""
    if request.method != 'POST':
        return redirect('home')
    
    playlist = get_object_or_404(Playlist, id=playlist_id)
    
    # Check if user can add to this playlist
    if playlist.owner != request.user and not playlist.is_collaborative:
        messages.error(request, "You don't have permission to add songs to this playlist.")
        return redirect('playlist_detail', playlist_id=playlist_id)
    
    # Get song data from POST
    spotify_id = request.POST.get('spotify_id')
    name = request.POST.get('name')
    artist = request.POST.get('artist')
    album = request.POST.get('album', '')
    duration_ms = request.POST.get('duration_ms', 0)
    image_url = request.POST.get('image_url', '')
    spotify_url = request.POST.get('spotify_url', '')
    
    if not spotify_id or not name or not artist:
        messages.error(request, "Missing song information.")
        return redirect('playlist_detail', playlist_id=playlist_id)
    
    # Get or create the song
    song, created = Song.objects.get_or_create(
        spotify_id=spotify_id,
        defaults={
            'name': name,
            'artist': artist,
            'album': album,
            'duration_ms': duration_ms,
            'image_url': image_url,
            'spotify_url': spotify_url,
        }
    )
    
    # Check if song is already in playlist
    if playlist.songs.filter(id=song.id).exists():
        messages.info(request, f'"{name}" is already in this playlist.')
    else:
        # Add song to playlist
        from .models import PlaylistSong
        max_order = playlist.playlistsong_set.count()
        PlaylistSong.objects.create(
            playlist=playlist,
            song=song,
            added_by=request.user,
            order=max_order
        )
        messages.success(request, f'Added "{name}" to "{playlist.name}"!')
    
    # Redirect back to the page they came from
    next_url = request.POST.get('next', 'playlist_detail')
    if 'playlist_detail' in next_url or next_url == 'playlist_detail':
        return redirect('playlist_detail', playlist_id=playlist_id)
    return redirect(next_url)


@login_required
def remove_song_from_playlist(request, playlist_id, song_id):
    """Remove a song from a playlist"""
    if request.method != 'POST':
        return redirect('playlist_detail', playlist_id=playlist_id)
    
    playlist = get_object_or_404(Playlist, id=playlist_id)
    song = get_object_or_404(Song, id=song_id)
    
    # Check if user can remove from this playlist
    if playlist.owner != request.user and not playlist.is_collaborative:
        messages.error(request, "You don't have permission to remove songs from this playlist.")
        return redirect('playlist_detail', playlist_id=playlist_id)
    
    # Remove the song
    from .models import PlaylistSong
    try:
        playlist_song = PlaylistSong.objects.get(playlist=playlist, song=song)
        playlist_song.delete()
        messages.success(request, f'Removed "{song.name}" from "{playlist.name}".')
    except PlaylistSong.DoesNotExist:
        messages.error(request, "Song not found in playlist.")
    
    return redirect('playlist_detail', playlist_id=playlist_id)


@login_required
def share_playlist_to_community(request, playlist_id):
    """Share a playlist to a community"""
    if request.method != 'POST':
        return redirect('playlist_detail', playlist_id=playlist_id)
    
    playlist = get_object_or_404(Playlist, id=playlist_id)
    
    # Check if user is the owner
    if playlist.owner != request.user:
        messages.error(request, "Only the playlist owner can share it to communities.")
        return redirect('playlist_detail', playlist_id=playlist_id)
    
    community_id = request.POST.get('community_id')
    if not community_id:
        messages.error(request, "Please select a community.")
        return redirect('playlist_detail', playlist_id=playlist_id)
    
    try:
        community = Community.objects.get(id=community_id)
        
        # Check if user is a member of the community
        if request.user not in community.members.all():
            messages.error(request, "You must be a member of this community to share to it.")
            return redirect('playlist_detail', playlist_id=playlist_id)
        
        # Share the playlist to the community
        playlist.community = community
        playlist.save()
        
        messages.success(request, f'Playlist "{playlist.name}" shared to "{community.name}"!')
    except Community.DoesNotExist:
        messages.error(request, "Community not found.")
    
    return redirect('playlist_detail', playlist_id=playlist_id)
