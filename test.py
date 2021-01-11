from flask import Flask
from flask import request

import urllib.request
import urllib.parse
import json
import time
import logging
import redis

redis_host = 'r-2ze42bfc8884f694.redis.rds.aliyuncs.com'
redis_port = 6379
redis_pwd = 'zhangrz@915'

app_index = {
        'wx53df963e29e4a7a9': '5ddf4191851dba79da4d290225484c9b'
        }

app = Flask(__name__)

def get_access_token_api(appid, secret):
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

def get_ticket_api(token):
    url = "https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token=%s&type=jsapi"%token
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

    if 'errcode' not in js:
        rsp['status'] = -1
        rsp['errmsg'] = 'miss errcode'
        return rsp

    if rsp['errcode'] != 0:
        rsp['status'] = -1
        rsp['errmsg'] = js['errmsg']

    rsp['status'] = 0
    rsp['ticket'] = js['ticket']
    rsp['expire'] = js['expires_in']

@app.route("/")
def hello():
    return "<h1 style='color:blue'>Hello There!</h1>"

@app.route("/get_access_token")
def get_access_token():
    app_id = request.args.get("app_id")
    if app_id is None:
        return "{'msg':'app_id is miss'}"
    r = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_pwd)
    data = r.get(app_id)
    return data

@app.route("/get_ticket")
def get_ticket():
    now = int(time.time())
    app_id = request.args.get("app_id")
    if app_id is None:
        return "{'msg':'app_id is miss'}"

    if app_id not in app_index:
        return "{'msg':'can not find secret'}"

    secret = app_index[app_id]
    token_rsp = get_access_token_api(app_id, secret)
    if 'status' not in token_rsp:
        return "{'msg':'status not in rsp'}"
    if token_rsp['status'] != 0:
        return "{'msg':'gettoken status error:%s'}"%json.dumps(token_rsp)

    access_token = token_rsp['access_token']
    ticket_rsp = get_ticket_api(access_token)
    if 'status' not in ticket_rsp:
        return "{'msg':'status not in ticket_rsp'}"
    if ticket_rsp['status'] != 0:
        return "{'msg':'getticket status error:%s'}"%json.dumps(ticket_rsp)

    data = {}
    data['ticket'] = ticket_rsp['ticket']
    data['expire_time'] = now + ticket_rsp['expire']
    data_str = None
    try:
        data_str = json.dumps(data)
    except:
        return "{'msg':'json dump error'}"

    return data_str

@app.route("/data_ack")
def data_ack():
    now = int(time.time())
    app_id = request.args.get("app_id")
    if app_id is None:
        return "{'msg':'app_id is miss'}"

    if app_id not in app_index:
        return "{'msg':'can not find secret'}"

    count_name = request.args.get("name")
    if count_name is None:
        return "{'msg':'name is miss'}"

    r = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_pwd)
    r.incr(count_name)
    return "{'msg': 'ok'}"

if __name__ == '__main__':
    app.run(debug=True, threaded=True)

application = app
