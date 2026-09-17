modules = ['sqlalchemy','pandas','sklearn','numpy','redis','pydantic']
for m in modules:
    try:
        __import__(m)
        print(m, 'OK')
    except Exception as e:
        print(m, 'ERR', e)
