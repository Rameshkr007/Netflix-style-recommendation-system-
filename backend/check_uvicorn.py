try:
    import uvicorn
    print("OK", getattr(uvicorn, '__version__', 'unknown'))
except Exception as e:
    print("ERR", e)
