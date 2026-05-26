#!/usr/bin/env python3
import http.cookiejar
import base64
import hashlib
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from cryptography.hazmat.primitives.asymmetric import ec, utils as ec_utils
from cryptography.hazmat.primitives import hashes


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


def _post_json(opener, url, payload, headers=None, timeout=35):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(',', ':')).encode('utf-8'),
        headers=headers or HEADERS,
        method='POST',
    )
    with opener.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8', errors='ignore') or '{}')


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


def _generate_pkce():
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
    verifier = ''.join(alphabet[b % len(alphabet)] for b in os.urandom(64))
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
    return verifier, challenge


def _b64url(data):
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def _make_ec_key():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        'key_ops': ['verify'],
        'ext': True,
        'kty': 'EC',
        'x': _b64url(public_numbers.x.to_bytes(32, 'big')),
        'y': _b64url(public_numbers.y.to_bytes(32, 'big')),
        'crv': 'P-256',
    }
    public_key = _b64url(json.dumps(jwk, separators=(',', ':')).encode('utf-8'))
    return private_key, public_key


def _sign_login_data(private_key, text):
    signature_der = private_key.sign(text.encode('utf-8'), ec.ECDSA(hashes.SHA256()))
    r, s = ec_utils.decode_dss_signature(signature_der)
    return _b64url(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))


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


def _grant_token(opener, kso_authcode, code_verifier, private_key, public_key):
    return _post_json(
        opener,
        ACCOUNT_BASE + '/passport/secure/api/grant_token',
        {
            'grant_type': 'authorization_code',
            'code': kso_authcode,
            'code_verifier': code_verifier,
            'code_sign': _sign_login_data(private_key, kso_authcode),
            'public_key': public_key,
            'is_append': False,
            'slv': 'ecdsa_itk',
        },
        headers={
            **HEADERS,
            'Content-Type': 'application/json',
        },
        timeout=20,
    )


def main():
    opener, cookie_jar = _make_opener()
    code_verifier, code_challenge = _generate_pkce()
    private_key, public_key = _make_ec_key()
    login = _read_jsonp(
        opener,
        QR_BASE + '/api/v3/login_qrcode?' + urllib.parse.urlencode({
            '_jsonp': 'cb',
            'code_challenge': code_challenge,
        }),
    )
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
            kso_authcode = result.get('kso_authcode')
            if kso_authcode:
                granted = _grant_token(opener, kso_authcode, code_verifier, private_key, public_key)
                if granted.get('result') not in (None, 'ok') and not granted.get('data'):
                    raise RuntimeError('金山登录授权失败：' + json.dumps(granted, ensure_ascii=False))
            elif authcode:
                exchanged = _exchange_authcode(opener, authcode)
                if exchanged.get('result') not in (None, 'ok'):
                    raise RuntimeError('金山登录换取 Cookie 失败：' + json.dumps(exchanged, ensure_ascii=False))
            else:
                raise RuntimeError('已扫码登录，但没有拿到 authcode。')
            cookie = _cookie_header(cookie_jar)
            if not cookie:
                raise RuntimeError('已扫码登录，但没有拿到 Cookie。')
            _save_cookie(cookie)
            print(f'成功保存金山 Cookie：{COOKIE_PATH}')
            return

    raise RuntimeError('等待扫码超时，请重新运行脚本。')


if __name__ == '__main__':
    main()
