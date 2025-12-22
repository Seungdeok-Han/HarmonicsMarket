from app import create_app
app = create_app()
app.config['TESTING'] = True
with app.test_client() as c:
    r = c.get('/')
    data = r.data.decode('utf-8')
    print('SNS in index:', 'SNS' in data)
    print('SNS emoji in index:', '📸' in data)
    print('snippet around SNS:')
    idx = data.find('SNS')
    if idx!=-1:
        print(data[max(0, idx-80):idx+80])
    else:
        print('not found')
