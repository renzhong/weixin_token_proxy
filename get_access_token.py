# -*- coding: utf-8 -*-

import urllib.request
import urllib.parse
import json
import time
import redis
import logging

app_index = {
        'wx53df963e29e4a7a9': '5ddf4191851dba79da4d290225484c9b'
        }

redis_host = 'r-2ze42bfc8884f694.redis.rds.aliyuncs.com'
redis_port = 6379
redis_pwd = 'zhangrz@915'

def get_access_token(appid, secret):
    url = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s"%(appid, secret)
    f = urllib.request.urlopen(url)
    rsp = {}
    data = None
    try:
        data = f.read()
    except:
        rsp['status'] = -1
        rsp['errmsg'] = 'exception'
        return rsp

    if data is None:
        rsp['status'] = -1
        rsp['errmsg'] = 'rsp is none'
        return rsp

    js = None

    try:
        js = json.loads(data)
    except:
        rsp['status'] = -1
        rsp['errmsg'] = 'json parse error'
        return rsp

    if 'errcode' in js:
        rsp['status'] = -1
        rsp['errmsg'] = js['errmsg']
        return rsp

    rsp['status'] = 0
    rsp['access_token'] = js['access_token']
    rsp['expire'] = js['expires_in']

    return rsp

def set_to_redis(app_id, data, expire):
    r = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_pwd)
    r.setex(app_id, expire, data)
    logging.info("app_id:%s set redis data:%s", app_id, data)

def get_from_redis(app_id, now):
    r = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_pwd)
    data_str = r.get(app_id)
    if data_str is None:
        logging.error("token is not in redis or is expire:%s", app_id)
        return False, None

    data = None
    try:
        data = json.loads(data_str)
    except:
        logging.error("json loads token error:%s %s", app_id, data_str)
        return False, None

    expire_time = data['expire_time']
    if now > expire_time - 60*3:
        logging.error("now %ld + 180 > expire_time %ld",now, expire_time)
        return False, None
    else:
        return True, data['access_token']

def main():
    now = int(time.time())
    for app_id, secret in app_list:
        ret, old_token = get_from_redis(app_id, now)
        if ret:
            logging.info("app_id:%s will not get new access_token old_token:%s", app_id, old_token)
            continue

        rsp = get_access_token(app_id, secret)
        if 'status' not in rsp:
            logging.error("app_id:%s status not in rsp:%s", app_id, json.dumps(rsp))
            continue

        if rsp['status'] != 0:
            logging.error("appid:%s status error :%s", app_id, json.dumps(rsp))
            continue

        data = {}
        data['access_token'] = rsp['access_token']
        data['expire_time'] = now + rsp['expire']
        expire = rsp['expire']
        data_str = None
        try:
            data_str = json.dumps(data)
        except:
            logging.error("app_id:%s json dump error", app_id)
            continue

        set_to_redis(app_id, data_str, expire)

if __name__ == '__main__':
    logging.basicConfig(filename='/var/log/token_cron.log', level=logging.DEBUG, format='%(asctime)s %(message)s')
    main()
