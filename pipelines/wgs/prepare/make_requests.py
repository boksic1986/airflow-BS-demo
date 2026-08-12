import base64
import hmac
import hashlib
import json
import time
import uuid
from urllib.parse import quote

import requests
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

GCM_IV_LENGTH = 12        # 96-bit IV
GCM_TAG_LENGTH = 16       # 128-bit authentication tag

# ---------- 工具函数 ----------
def encrypt(data: str, key: str) -> bytes:
    """
    AES-GCM 加密，返回结构: IV(12字节) || ciphertext+tag
    """
    iv =  get_random_bytes(GCM_IV_LENGTH)
    cipher = AES.new(base64.b64decode(key), AES.MODE_GCM, nonce=iv)
    ciphertext, tag = cipher.encrypt_and_digest(data.encode("utf-8"))

    # 拼接：IV + 密文 + 认证标签
    return base64.b64encode(iv + ciphertext + tag).decode("utf-8")


def decrypt(data: str, key: str) -> bytes:
    """
    AES-GCM 解密，输入结构: IV(12字节) || ciphertext || tag
    返回明文
    """
    data_b64 = base64.b64decode(data)
    iv = data_b64[:GCM_IV_LENGTH]
    ct_and_tag = data_b64[GCM_IV_LENGTH:]

    cipher = AES.new(base64.b64decode(key), AES.MODE_GCM, nonce=iv)
    # 把密文和认证标签一起交给 decrypt_and_verify
    return cipher.decrypt_and_verify(ct_and_tag[:-GCM_TAG_LENGTH],
                                      ct_and_tag[-GCM_TAG_LENGTH:])


def hmac_sha256_sign(message: str, key: str) -> str:
    """HmacSHA256 签名并做 base64"""
    return base64.b64encode(hmac.new(
                key.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256
            ).digest()).decode("utf-8")


def build_sorted_query(body_dict: dict) -> str:
    """
    按字典序拼接「有值」参数，数组用 .[index]=value 形式
    例：sampleNoList.[0]=s1;sampleNoList.[1]=s2
    """
    pieces = []
    for k, v in sorted(body_dict.items()):
        if v is None:
            continue
        if isinstance(v, list):
            for idx, item in enumerate(v):
                pieces.append(f'{k}.[{idx}]={quote(str(item), safe="")}')
        else:
            pieces.append(f'{k}={quote(str(v), safe="")}')
    return ';'.join(pieces)


def make_requests(data: dict, url: str, access_key: str="test", secret_key: str="wbfFC6IthAKlVqR3RvnnSq19Aa3IbGztxbn/aXVltzE="):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    nonce = str(uuid.uuid4())
    # AES 加密 nonce
    encrypted_nonce = encrypt(nonce, secret_key)

    # 签名：只对「有值」参数按字典序拼接
    sign_str = build_sorted_query(data)
    signature = hmac_sha256_sign(sign_str, secret_key)

    headers = {
        'Content-Type': 'application/json',
        'biosan_timestamp': timestamp,
        'biosan_access_key': access_key,
        'biosan_nonce': encrypted_nonce,
        'biosan_signature': signature
    }
    
    res = requests.post(url, data=json.dumps(data), headers=headers, timeout=15)
    # print(url, json.dumps(data), headers, res.json(), sign_str,secret_key, sep="\n")
    return res

def task_callback(data: dict, url: str, access_key: str="test", secret_key: str="wbfFC6IthAKlVqR3RvnnSq19Aa3IbGztxbn/aXVltzE="):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    nonce = str(uuid.uuid4())
    # AES 加密 nonce
    encrypted_nonce = encrypt(nonce, secret_key)

    # 签名：只对「有值」参数按字典序拼接
    sign_str = build_sorted_query(data)
    signature = hmac_sha256_sign(sign_str, secret_key)

    headers = {
        'Content-Type': 'application/json',
        'biosan_timestamp': timestamp,
        'biosan_access_key': access_key,
        'biosan_nonce': encrypted_nonce,
        'biosan_signature': signature
    }

    get_url = f"{url}?{sign_str}"
    res = requests.get(get_url, headers=headers, timeout=15)
    return res
