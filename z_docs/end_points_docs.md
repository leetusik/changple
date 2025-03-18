- **Pinecone_services.py**
    - **search_similar_documents** 엔드포인트 (POST)
        
        :  pinecone DB에서 query와 유사한 documents 검색
        
        - URL
            
            ```
            /chatbot/search/
            ```
            
        - JSON
            
            ```json
            {
              "query": "고기집",
              "top_k": 5,
              "filters": {}
            }
            ```
            
        
    - **process_cafe_data** 엔드포인트 (POST)
        
        : django DB의 데이터를 embedding을 거쳐 pinecone 벡터DB로 업로드
        
        - URL
            
            ```
            /chatbot/index-cafe-data/
            ```
            
        - JSON
            
            ```json
            {
              "start_date": "2020-01-01",
              "end_date": "2025-03-18",
              "limit": 100
            }
            ```
            
        
    - **clear_index** 엔드포인트 (터미널에서 python shell 실행후 아래 코드 복붙)
        
        : pinecone의 현재 index의 모든 데이터를 삭제
        
        - URL
            
            ```bash
            python manage.py shell
            ```
            
        - JSON
            
            ```python
            from chatbot.services.pinecone_service import PineconeService
            service = PineconeService()
            success = service.clear_index()
            print(f"인덱스 초기화 결과: {'성공' if success else '실패'}")
            ```
            
        
    - **get_stats** 엔드포인트 (GET)
        
        : django DB와 pinecone의 현재 데이터를 현황 통계 조회
        
        - URL
            
            ```
            /chatbot/pinecone-stats/
            ```
            
    
- **Langchain_services.py**
    - **chat** 엔드포인트 (POST)
        - URL
        
        ```
        /chatbot/chat/
        ```
        
        - JSON
            - **첫 질문** (history 없음)
                
                ```json
                	{
                  "query": "창플은 무엇인가요?"
                }
                ```
                
            - **후속 질문**
                
                ```json
                {
                  "query": "어떤 서비스를 제공하나요?",
                  "history": [
                    {
                      "role": "user",
                      "content": "창플은 무엇인가요?"
                    },
                    {
                      "role": "assistant",
                      "content": "창플은 창의적인 플랫폼을 의미합니다. 저희는 사용자들이 자신의 창의력을 발휘하고 다양한 아이디어를 공유할 수 있는 환경을 제공하는 것을 목표로 하고 있습니다..."
                    }
                  ]
                }
                ```