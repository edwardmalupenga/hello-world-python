import urllib.request, urllib.parse
import http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

resp = opener.open('http://127.0.0.1:5000/login')
print('GET login', resp.status)

params = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123'}).encode()
resp = opener.open('http://127.0.0.1:5000/login', data=params)
body = resp.read().decode('utf-8', errors='ignore')
print('POST login', resp.status, resp.geturl())
print('Has session cookie:', any(c.name == 'session' for c in cj))
print('Contains internal error:', 'Internal error during login' in body)
print('Contains invalid credentials:', 'Invalid credentials' in body)
print('Contains Dashboard title:', '<title>SMS - Dashboard</title>' in body)
print('Body length:', len(body))
print('--- body snippet ---')
print(body[:1200])
