#!/usr/bin/env python3
import http.cookiejar
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COOKIE_PATH = os.path.join(BASE_DIR, 'data', 'kdocs_cookie.txt')
QR_PNG_PATH = os.path.join(BASE_DIR, 'data', 'kdocs_login_qr.png')

ACCOUNT_BASE = 'https://account.wps.cn'
QR_BASE = 'https://qr.wps.cn'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
    'Referer': 'https://account.wps.cn/wpspersonallogin',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
}


def _make_opener():
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl._create_unverified_context()),
        urllib.request.HTTPCookieProcessor(cookie_jar),
    )
    return opener, cookie_jar


def _read_text(opener, url, data=None, headers=None, timeout=35):
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers=headers or HEADERS)
    with opener.open(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore')


def _read_json(opener, url, data=None, headers=None, timeout=35):
    text = _read_text(opener, url, data=data, headers=headers, timeout=timeout)
    return json.loads(text or '{}')


def _read_jsonp(opener, url, callback='cb', timeout=35):
    text = _read_text(opener, url, timeout=timeout)
    match = re.search(r'^[^(]+\((.*)\)\s*;?\s*$', text, re.S)
    if not match:
        raise RuntimeError('金山二维码接口返回格式异常：' + text[:120])
    return json.loads(match.group(1) or '{}')


def _cookie_header(cookie_jar):
    return '; '.join(f'{c.name}={c.value}' for c in cookie_jar if c.value)


def _save_cookie(cookie):
    os.makedirs(os.path.dirname(COOKIE_PATH), exist_ok=True)
    with open(COOKIE_PATH, 'w', encoding='utf-8') as f:
        f.write(cookie)
    try:
        os.chmod(COOKIE_PATH, 0o600)
    except Exception:
        pass


def _download_qr(opener, url):
    req = urllib.request.Request(url, headers=HEADERS)
    with opener.open(req, timeout=20) as resp:
        content = resp.read()
    os.makedirs(os.path.dirname(QR_PNG_PATH), exist_ok=True)
    with open(QR_PNG_PATH, 'wb') as f:
        f.write(content)


def _exchange_authcode(opener, authcode):
    return _read_json(
        opener,
        ACCOUNT_BASE + '/api/session/exchange/login',
        data={'authcode': authcode},
        headers={
            **HEADERS,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
        },
        timeout=20,
    )


def main():
    opener, cookie_jar = _make_opener()
    login = _read_jsonp(opener, QR_BASE + '/api/v3/login_qrcode?_jsonp=cb')
    loginid = login.get('loginid')
    if not loginid:
        raise RuntimeError('没有拿到金山登录二维码 ID：' + json.dumps(login, ensure_ascii=False))

    qr_info = _read_json(
        opener,
        QR_BASE + '/api/v3/login_qrcode/url?' + urllib.parse.urlencode({
            'loginid': loginid,
        }),
        timeout=20,
    )
    qr_url = qr_info.get('url')
    if not qr_url:
        raise RuntimeError('没有拿到金山二维码图片：' + json.dumps(qr_info, ensure_ascii=False))

    print('金山登录二维码已生成。')
    print('1. 打开下面这个二维码图片地址，或把 PNG 下载到本地查看：')
    print(qr_url)
    try:
        _download_qr(opener, qr_url)
        print(f'2. 服务器本地 PNG：{QR_PNG_PATH}')
    except Exception as exc:
        print(f'2. PNG 保存失败也不影响扫码，直接打开上面的地址即可：{exc}')
    print('3. 用手机 WPS 扫码并确认登录。脚本会等待最多 5 分钟。')

    state = 'scan'
    deadline = time.time() + 300
    while time.time() < deadline:
        poll_url = QR_BASE + '/api/v3/login_qrcode/login?' + urllib.parse.urlencode({
            'loginid': loginid,
            'state': state,
            '_jsonp': 'cb',
        })
        try:
            result = _read_jsonp(opener, poll_url, timeout=45)
        except TimeoutError:
            continue
        except urllib.error.URLError:
            continue

        code = result.get('result')
        if code and code != 'ok':
            raise RuntimeError('金山扫码登录失败：' + json.dumps(result, ensure_ascii=False))

        next_state = result.get('state')
        if next_state == 'pending':
            continue
        if next_state == 'scan':
            state = 'confirm'
            print('已扫码，请在手机上确认登录。')
            continue
        if next_state == 'logined':
            authcode = result.get('authcode')
            if authcode:
                exchanged = _exchange_authcode(opener, authcode)
                if exchanged.get('result') not in (None, 'ok'):
                    raise RuntimeError('金山登录换取 Cookie 失败：' + json.dumps(exchanged, ensure_ascii=False))
            cookie = _cookie_header(cookie_jar)
            if not cookie:
                raise RuntimeError('已扫码登录，但没有拿到 Cookie。')
            _save_cookie(cookie)
            print(f'成功保存金山 Cookie：{COOKIE_PATH}')
            return

    raise RuntimeError('等待扫码超时，请重新运行脚本。')


if __name__ == '__main__':
    main()
