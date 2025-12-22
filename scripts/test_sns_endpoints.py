import sys, os, json
sys.path.insert(0, os.getcwd())
from app import create_app
app = create_app()
app.config['TESTING'] = True
c = app.test_client()
print('GET /sns ->', c.get('/sns').status_code)
# load posts file to get id
pfile = os.path.join(os.getcwd(),'data','sns_posts.json')
if os.path.exists(pfile):
    with open(pfile,encoding='utf-8') as f:
        posts = json.load(f)
    if posts:
        pid = posts[0]['id']
        r=c.get(f'/sns/{pid}')
        print(f'GET /sns/{pid} ->', r.status_code, r.data.decode('utf-8')[:200])
    else:
        print('no posts')
else:
    print('no data file')
