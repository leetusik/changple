from django.core.management.base import BaseCommand
from chatbot.models import Prompt
import json

class Command(BaseCommand):
    help = '프롬프트 데이터를 추가하거나 수정합니다'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, help='JSON 파일 경로')
        parser.add_argument('--mode', type=str, choices=['add', 'update'], default='add',
                          help='작업 모드: add(추가) 또는 update(수정)')
        
    def handle(self, *args, **options):
        file_path = options.get('file')
        mode = options.get('mode')
        
        if not file_path:
            self.stdout.write(self.style.ERROR('파일 경로를 지정해주세요.'))
            return
            
        with open(file_path, 'r', encoding='utf-8') as f:
            prompts_data = json.load(f)
            
        if mode == 'add':
            self._add_prompts(prompts_data)
        elif mode == 'update':
            self._update_prompts(prompts_data)
            
    def _add_prompts(self, prompts_data):
        """새 프롬프트를 추가합니다"""
        added_count = 0
        for prompt_data in prompts_data:
            Prompt.objects.create(
                prompt_id=prompt_data.get('prompt_id'),
                name=prompt_data.get('name'),
                content=prompt_data.get('content'),
                description=prompt_data.get('description', '')
            )
            added_count += 1
                
        self.stdout.write(self.style.SUCCESS(f'{added_count}개의 프롬프트가 추가되었습니다.'))
    
    def _update_prompts(self, prompts_data):
        """기존 프롬프트를 업데이트합니다"""
        updated_count = 0
        errors = []
        
        for prompt_data in prompts_data:
            # ID로 업데이트
            if 'id' in prompt_data:
                try:
                    prompt = Prompt.objects.get(id=prompt_data['id'])
                    self._update_prompt_fields(prompt, prompt_data)
                    updated_count += 1
                except Prompt.DoesNotExist:
                    errors.append(f"ID {prompt_data['id']}인 프롬프트를 찾을 수 없습니다.")
            
            # prompt_id로 업데이트
            elif 'prompt_id' in prompt_data:
                try:
                    prompt = Prompt.objects.get(prompt_id=prompt_data['prompt_id'])
                    self._update_prompt_fields(prompt, prompt_data)
                    updated_count += 1
                except Prompt.DoesNotExist:
                    errors.append(f"prompt_id '{prompt_data['prompt_id']}'인 프롬프트를 찾을 수 없습니다.")
            else:
                errors.append(f"ID나 prompt_id가 없는 항목은 건너뜁니다: {prompt_data}")
        
        self.stdout.write(self.style.SUCCESS(f'{updated_count}개의 프롬프트가 수정되었습니다.'))
        if errors:
            self.stdout.write(self.style.WARNING('다음 오류가 발생했습니다:'))
            for error in errors:
                self.stdout.write(f"- {error}")
    
    def _update_prompt_fields(self, prompt, prompt_data):
        """프롬프트 객체의 필드를 업데이트합니다"""
        # ID는 제외하고 업데이트 (ID는 조회용으로만 사용)
        if 'name' in prompt_data:
            prompt.name = prompt_data['name']
        if 'content' in prompt_data:
            prompt.content = prompt_data['content']
        if 'description' in prompt_data:
            prompt.description = prompt_data['description']
        if 'prompt_id' in prompt_data and 'id' in prompt_data:
            # id로 조회한 경우 prompt_id도 업데이트 가능
            prompt.prompt_id = prompt_data['prompt_id']
            
        prompt.save() 