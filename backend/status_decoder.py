import json
import sys
from whatsapp import HKDF,AESUnpad;
import base64;
import urllib2;
import time;
from Crypto.Cipher import AES;
query = json.loads(sys.argv[1])
mediaK= query['mediakey']
if query['mimetype'] == "video/mp4":
    mediaKeyExpanded=HKDF(base64.b64decode(mediaK),112,"WhatsApp Video Keys")
else:
    mediaKeyExpanded=HKDF(base64.b64decode(mediaK),112,"WhatsApp Image Keys")

mediaData= urllib2.urlopen(query['url']).read()
file= mediaData[:-10]
iv=mediaKeyExpanded[:16]
cipherKey= mediaKeyExpanded[16:48]
decryptor = AES.new(cipherKey, AES.MODE_CBC, iv)
fileData=AESUnpad(decryptor.decrypt(file))
print(base64.b64encode(fileData))