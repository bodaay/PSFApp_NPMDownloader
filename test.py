import requests
import string
from urllib.parse import urlparse
import random
def download_file(url):
    local_filename = url.split('/')[-1]
    # NOTE the stream=True parameter below
    try:
        with requests.get(url, stream=True) as r:
            if not r.status_code==200:#with cloudflar shit, there is a trick that work when we get 500 error, change the url, I still don't why it works
                parsedurl=urlparse(url)
                newlink = parsedurl[0] + "://" + parsedurl[1] + "/" + random.choice(string.ascii_letters)  + random.choice(string.ascii_letters)  + random.choice(string.ascii_letters) + parsedurl[2]
                print (newlink)
                # break
            # with open(local_filename, 'wb') as f:
            #     for chunk in r.iter_content(chunk_size=8192): 
            #         if chunk: # filter out keep-alive new chunks
            #             f.write(chunk)
            #             # f.flush()
        return local_filename
    except requests.exceptions.RequestException as ex:
        print (ex.errno)

download_file("https://registry.npmjs.org/@middy/http-security-header/-/1http-security-header-1.0.0-alpha.48.tgz")