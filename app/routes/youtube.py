"""YouTube search and GuitarModels famous-users helpers."""
import csv
import os

import requests

YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')


def search_youtube_videos(query, max_results=2):
    if not YOUTUBE_API_KEY:
        print('⚠️ YouTube API Key가 설정되지 않았습니다!')
        return []

    url = 'https://www.googleapis.com/youtube/v3/search'

    params = {
        'part': 'snippet',
        'q': f'{query} guitar tone review demo',
        'type': 'video',
        'key': YOUTUBE_API_KEY,
        'maxResults': max_results,
    }
    try:
        print(f'🔍 YouTube 검색 (한국어): {query}')
        response = requests.get(url, params=params, timeout=5)
        print(f'📡 YouTube API 상태 코드: {response.status_code}')

        if response.status_code != 200:
            print(f'❌ YouTube API 에러 응답: {response.text}')
            return []

        response.raise_for_status()
        results = response.json().get('items', [])
        print(f'✅ YouTube 검색 결과: {len(results)}개')

        if len(results) == 0:
            print('🔄 영어로 재검색 시도...')
            params_en = {
                'part': 'snippet',
                'q': f'{query} guitar tutorial',
                'type': 'video',
                'key': YOUTUBE_API_KEY,
                'maxResults': max_results,
                'relevanceLanguage': 'en',
            }
            response_en = requests.get(url, params=params_en, timeout=5)
            if response_en.status_code == 200:
                results = response_en.json().get('items', [])
                print(f'✅ 영어 검색 결과: {len(results)}개')

        return [
            f"https://www.youtube.com/embed/{item['id']['videoId']}"
            for item in results
            if 'id' in item and 'videoId' in item['id']
        ]
    except Exception as e:
        print(f'❌ YouTube API Error: {e}')
        return []


def get_model_famous_users():
    famous_users_map = {}
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'GuitarModels.csv')
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            brand = row.get('Maker', '').strip()
            model = row.get('Model', '').strip()
            users = [
                row.get('NotableUser1', '').strip(),
                row.get('NotableUser2', '').strip(),
                row.get('NotableUser3', '').strip(),
            ]
            users = [u for u in users if u]
            if brand and model and users:
                famous_users_map[(brand, model)] = ', '.join(users)
    return famous_users_map
