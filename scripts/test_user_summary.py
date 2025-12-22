import sys, os
sys.path.insert(0, os.getcwd())
from app import create_app
app = create_app()
app.config['TESTING'] = True
c = app.test_client()
res = c.get('/user/summary/1')
print(res.status_code)
print(res.data.decode('utf-8'))
