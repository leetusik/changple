import os
from dotenv import load_dotenv
from algoliasearch.search.client import SearchClientSync
from algoliasearch.http.exceptions import RequestException

load_dotenv()

ALGOLIA_APPLICATION_ID = os.environ['APPLICATION_ID']
ALGOLIA_SEARCH_API_KEY = os.environ['SEARCH_API_KEY']

algolia_client = SearchClientSync(ALGOLIA_APPLICATION_ID, ALGOLIA_SEARCH_API_KEY)
INDEX_NAME = 'changple-q'


def parse_algolia_results(response):
    """
    Algolia 검색 결과를 파싱하여 필요한 정보만 추출합니다.
    """
    try:
        parsed_hits = []
        for hit in response.hits:
            parsed_hits.append({
                'object_id': hit.object_id,
                'proximity_distance': hit.ranking_info.proximity_distance,
                'user_score': hit.ranking_info.user_score,
                'data': hit.structData
            })

        parsed_results = {
            'query': response.query,
            'parsed_query': response.parsed_query,
            'params': response.params,
            'nb_hits': response.nb_hits,
            'page': response.page,
            'nb_pages': response.nb_pages,
            'hits_per_page': response.hits_per_page,
            'facets': response.facets,
            'hits': parsed_hits,
        }

        return parsed_results
    
    except Exception as e:
        print(e)
        return None


def algolia_search(query):
   
    if not query:
        print("error : 검색어(query)가 필요합니다.")
        return None
    
    try:
        # Algolia 검색 실행
        response = algolia_client.search_single_index(
            INDEX_NAME,
            {"query" : query,
             "getRankingInfo": True}
        )

        # 사용 가능한 속성 목록 출력
        # print("--- Available attributes for response object ---")
        # print(dir(response))
        # print("---------------------------------------------")

        parsed_results = parse_algolia_results(response)    
        
        return parsed_results
        

    except Exception as e:
        print(e)
        return None
    

# if __name__ == "__main__":
#     import pprint

#     result = algolia_search("치킨집 창업")

#     print('query : ', result['query'])
#     print('parsed_query : ', result['parsed_query'])
#     print('params : ', result['params'])
#     print('nb_hits : ', result['nb_hits'])
#     print('page : ', result['page'])
#     print('nb_pages : ', result['nb_pages'])
#     print('hits_per_page : ', result['hits_per_page'])
#     print('facets : ', result['facets'])

#     for hit in result['hits']:
#         print('--------------------------------')
#         print('object_id : ', hit['object_id'])
#         print('proximity_distance : ', hit['proximity_distance'])
#         print('user_score : ', hit['user_score'])

#         hit['data']['full_content'] = hit['data']['full_content'][:300] + '...'
#         pprint.pprint(hit['data'])
#         print('--------------------------------')
