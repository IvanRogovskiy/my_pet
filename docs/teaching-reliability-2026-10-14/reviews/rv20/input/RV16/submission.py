def check(request):
    response = request()
    if response.status != 200:
        raise ValueError("unexpected HTTP status")
    return response.status
