from urllib.request import urlopen
def health(url):
    with urlopen(url, timeout=3) as response:
        return response.status
