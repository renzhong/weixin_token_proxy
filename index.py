from flask import Flask
from flask import request, Response

import MySQLdb
import urllib.request
import urllib.parse
import json
import time
import logging
import redis

redis_host = 'r-2ze42bfc8884f694.redis.rds.aliyuncs.com'
redis_port = 6379
redis_pwd = 'zhangrz@915'

mysql_host = 'rm-2zer7cl9103bs9k90125010.mysql.rds.aliyuncs.com'
mysql_port = 3306
mysql_user = 'control'
mysql_pwd = 'zhangrz@915'
mysql_database = 'lucky_user'

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

    if js['errcode'] != 0:
        rsp['status'] = -1
        rsp['errmsg'] = js['errmsg']

    rsp['status'] = 0
    rsp['ticket'] = js['ticket']
    rsp['expire'] = js['expires_in']
    return rsp

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

word_index = [
    '抗击新冠',
    '复工复产',
    '直播带货',
    '小康生活',
    '十三五收官',
    '十九届五中全会',
    '故宫600年',
    '核心区控规',
    '崇文争先',
    '东城社工',
    '紫金服务',
    '对口帮扶',
    '文明城区',
    '垃圾分类',
    '光盘行动',
    '美丽院落',
    '接诉即办',
    '物业管理',
    '留白增绿',
    '王府井品牌节',
    '网红打卡地',
    '大戏东望',
    '老字号新生活',
]
@app.route("/get_lucky_ticket", methods=['POST'])
def get_lucky_ticket():
    info = {}
    name = request.json.get('name', None)
    key_word = request.json.get('key_word', None)

    if name is None:
        info['msg'] = 'name is miss'
        rsp = Response(json.dumps(info),  mimetype='application/json')
        return rsp

    if key_word is None:
        info['msg'] = 'key_word is miss'
        rsp = Response(json.dumps(info),  mimetype='application/json')
        return rsp

    word_index_array = sorted(key_word.split(','))
    key_words = []
    for index in word_index_array:
        index = int(index)
        if index >0 and index < len(word_index):
            key_words.append(word_index[int(index)])

    user_key = "%s_%s"%(name, '_'.join(key_words))
    print("user_key %s"%user_key)

    lucky_index = hash(user_key)%5

    info['lucky_index'] = lucky_index
    rsp = Response(json.dumps(info),  mimetype='application/json')
    return rsp

@app.route('/upload_info', methods=['POST'])
def upload_info():
    info = {}
    name = request.json.get('name', None)
    phone = request.json.get('phone', None)
    addr = request.json.get('addr', None)

    if name is None:
        info['msg'] = 'name is miss'
        rsp = Response(json.dumps(info),  mimetype='application/json')
        return rsp
    if phone is None:
        info['msg'] = 'phone is miss'
        rsp = Response(json.dumps(info),  mimetype='application/json')
        return rsp
    if addr is None:
        info['msg'] = 'addr is miss'
        rsp = Response(json.dumps(info),  mimetype='application/json')
        return rsp

    try:
        db = MySQLdb.connect(host=mysql_host, port=mysql_port, user=mysql_user, passwd=mysql_pwd, database=mysql_database, charset='utf8' )

        cursor = db.cursor()
        sql = "insert into `user` (name, phone, addr) VALUES('%s', '%s', '%s')"%(name, phone, addr)
        print(sql)
        ret = cursor.execute(sql)
        print("execute ret:", ret)
        db.commit()
        db.close()
    except Exception as e:
        print(e)
        info['msg'] = 'mysql error'
        rsp = Response(json.dumps(info),  mimetype='application/json')
        return rsp

    info['msg'] = 'ok'
    rsp = Response(json.dumps(info),  mimetype='application/json')
    return rsp

@app.route('/get_lucky_user')
def get_lucky_user():
    info = {}

    offset = request.args.get("offset", '0')
    count = request.args.get("count", '10')

    if offset is None:
        info['msg'] = 'offset is miss'
        rsp = Response(json.dumps(info),  mimetype='application/json')
        return rsp

    if count is None:
        info['msg'] = 'count is miss'
        rsp = Response(json.dumps(info),  mimetype='application/json')
        return rsp

    try:
        db = MySQLdb.connect(host=mysql_host, port=mysql_port, user=mysql_user, passwd=mysql_pwd, database=mysql_database, charset='utf8' )
        cursor = db.cursor()
        sql = "select name, phone, addr from user limit %s,%s"%(offset, count)
        print(sql)
        cursor.execute(sql)

        results = cursor.fetchall()
        info['data'] = []
        for row in results:
            user = row[0]
            phone = row[1]
            addr = row[2]
            obj = {"name":user, "phone": phone, "addr": addr}
            info['data'].append(obj)

        db.close()
    except Exception as e:
        print(e)
        info['msg'] = 'mysql error'
        rsp = Response(json.dumps(info),  mimetype='application/json')
        return rsp

    rsp = Response(json.dumps(info),  mimetype='application/json')
    return rsp

if __name__ == '__main__':
    app.run(debug=True, threaded=True)

application = app
