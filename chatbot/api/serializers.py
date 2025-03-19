"""
Serializers for the chatbot API.
"""

from rest_framework import serializers
from chatbot.models import ChatSession, ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    """채팅 메시지 시리얼라이저"""
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'created_at']

class ChatSessionSerializer(serializers.ModelSerializer):
    """채팅 세션 시리얼라이저"""
    messages = ChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatSession
        fields = ['id', 'session_id', 'created_at', 'updated_at', 'messages']

class SearchQuerySerializer(serializers.Serializer):
    """검색 쿼리 시리얼라이저"""
    query = serializers.CharField(required=True)
    top_k = serializers.IntegerField(required=False, default=5)
    filters = serializers.DictField(required=False, allow_null=True)

class IndexDataSerializer(serializers.Serializer):
    """인덱스 데이터 시리얼라이저"""
    start_date = serializers.DateTimeField(required=False, allow_null=True)
    end_date = serializers.DateTimeField(required=False, allow_null=True)
    limit = serializers.IntegerField(required=False, allow_null=True)
    category_group = serializers.CharField(required=False, allow_null=True)

# Define your serializers here 