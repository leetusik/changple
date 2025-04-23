from django.test import TestCase
from services.algolia_search import algolia_search

# 검색어를 입력하세요
SEARCH_QUERY = "치킨집 창업"

# Create your tests here.
if __name__ == "__main__":
    import pprint

    result = algolia_search(SEARCH_QUERY)

    print('query : ', result['query'])
    print('parsed_query : ', result['parsed_query'])
    print('params : ', result['params'])
    print('nb_hits : ', result['nb_hits'])
    print('page : ', result['page'])
    print('nb_pages : ', result['nb_pages'])
    print('hits_per_page : ', result['hits_per_page'])
    print('facets : ', result['facets'])

    for hit in result['hits']:
        print('--------------------------------')
        print('object_id : ', hit['object_id'])
        print('proximity_distance : ', hit['proximity_distance'])
        print('user_score : ', hit['user_score'])

        hit['data']['full_content'] = hit['data']['full_content'][:300] + '...'
        pprint.pprint(hit['data'])
        print('--------------------------------')