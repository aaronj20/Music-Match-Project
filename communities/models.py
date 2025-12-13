from django.db import models
from django.contrib.auth.models import User


class Community(models.Model):
    """Music communities based on genre or shared interests"""
    name = models.CharField(max_length=255)
    description = models.TextField()
    genre = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_communities')
    members = models.ManyToManyField(User, related_name='communities', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    def member_count(self):
        return self.members.count()


class CommunityMessage(models.Model):
    """Chat messages within a community"""
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_messages')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.user.username} in {self.community.name}: {self.message[:50]}"

