from django.db import models

# Create your models here.

class ChatSession(models.Model):
    """채팅 세션 모델"""
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"채팅 세션 {self.session_id}"

class ChatMessage(models.Model):
    """채팅 메시지 모델"""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20)  # 'user' 또는 'assistant'
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

class Prompt(models.Model):
    prompt_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    content = models.TextField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    score = models.IntegerField(default=0)
    num_exposure = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.prompt_id}_{self.updated_at.strftime('%Y%m%d')}"

class ABTest(models.Model):
    query = models.TextField()
    prompt_a = models.ForeignKey(Prompt, on_delete=models.CASCADE, related_name="test_as")
    prompt_b = models.ForeignKey(Prompt, on_delete=models.CASCADE, related_name="test_bs")
    response_a = models.TextField()
    response_b = models.TextField()
    winner = models.CharField(max_length=10, null=True, blank=True, choices=[('a', 'Prompt A'), ('b', 'Prompt B')])
    llm_model = models.CharField(max_length=50)
    llm_temperature = models.FloatField(null=True, blank=True)
    llm_top_k = models.IntegerField(null=True, blank=True)
    chunk_size = models.IntegerField(null=True, blank=True)
    chunk_overlap = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Test: {self.query[:50]}"
    
    def get_winner_prompt(self):
        if self.winner == 'a':
            return self.prompt_a
        elif self.winner == 'b':
            return self.prompt_b
        return None

