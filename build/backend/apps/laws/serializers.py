from rest_framework import serializers
from .models import *

class LawClauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = LawClause
        fields = ['id', 'clause_id', 'heading', 'content', 'examples', 'notes', 'order']

class LawSerializer(serializers.ModelSerializer):
    clauses = LawClauseSerializer(many=True, read_only=True)
    
    class Meta:
        model = Law
        fields = ['id', 'number', 'title', 'clauses', 'full_content', 'created_at']

class LawListSerializer(serializers.ModelSerializer):
    clause_count = serializers.IntegerField(source='clauses.count', read_only=True)
    
    class Meta:
        model = Law
        fields = ['id', 'number', 'title', 'clause_count']

class LawEditionSerializer(serializers.ModelSerializer):
    law_count = serializers.IntegerField(source='laws.count', read_only=True)
    
    class Meta:
        model = LawEdition
        fields = ['id', 'year', 'publication_date', 'is_current', 'law_count']

class LawChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LawChange
        fields = ['id', 'law_number', 'clause_id', 'change_type', 'description', 'old_content', 'new_content']
