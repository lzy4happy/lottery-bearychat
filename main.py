#coding=utf-8

import os
from bearychat import openapi
from difflib  import SequenceMatcher
import random
import util


import re
import json

from urllib import urlencode
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.httpclient import AsyncHTTPClient
from tornado import gen
from tornado.websocket import websocket_connect

KEY_WHO = 'who'

class Handler():
    handle_register = {}

    def __init__(self, func):
        Handler.handle_register[func.__name__] = func

    @classmethod
    def get(cls, k):
        for i in cls.handle_register.keys():
            if re.search(i, k):
                return cls.handle_register.get(i)
        return False

    def __call__(self, func):
        return func


@Handler
def test(client):
    return "Hello,World"

@Handler
def who(client):
    usrs = client.user.list()
    usrnames = []
    for u in usrs:
        if u['type'] == u'normal':
            usrnames.append('@<=' + u['id'] + '=>')
    return ','.join(usrnames)


def checkWho(text):
    if text.find(KEY_WHO) != -1:
        return True
    else:
        return False
def checkRule(text, database, client):
    if (text.find(u"抽") != -1) and util.getResultForDigit(text) > 0:
        num = util.getResultForDigit(text)
        print 'number == ' + str(num)
        who = randomWho(client, num)
        if(who.find(u"@") != -1):
            return u"恭喜中奖啦!>_<" + who
        else:
            return u'人员不足，程序员都被祭天了吗?'
    an = database(text)
    if an:
        who = randomWho(client, 1)
        an = an.decode('utf-8').replace("@", who)
        return an
    else:
        return u"今天天气真好，不是嘛" + who

def randomWho(client, num):
    usrs = client.user.list()

    usrsNormal = []
    for u in usrs:
        if u['type'] == u'normal':
            usrsNormal.append(u)
    size = len(usrsNormal)
    if (num > size):
        return 'person not enough'

    usrnames = []
    resultList = random.sample(range(0, size), num)
    for i in resultList:
        if usrsNormal[i]['type'] == u'normal':
            usrnames.append('@<=' + usrsNormal[i]['id'] + '=>')
    return ','.join(usrnames)

# def randomWho(client):
#     usrs = client.user.list()
#     usrnames = []
#     for u in usrs:
#         if u['type'] == u'normal':
#             usrnames.append('@<=' + u['id'] + '=>')
#     size = len(usrnames)
#     index = random.randint(0,size-1)
#     return usrnames[index]


class Client(object):
    def __init__(self):
        self.ioloop = IOLoop.instance()
        self.database = util.getSmailarDatabase()
        self.openapi = openapi.Client("d50245610146e046325d6d8f7e588421")
        self.me = '@<=' + self.openapi.user.me()['id'] + '=>'
        self.ws = None
        self.connect()
        PeriodicCallback(self.keep_alive, 20000, io_loop=self.ioloop).start()
        self.ioloop.start()

    @gen.coroutine
    def connect(self):
        print("trying to connect")
        try:
            post_data = {'token': "d50245610146e046325d6d8f7e588421"}
            get_url = yield AsyncHTTPClient().fetch("https://rtm.bearychat.com/start", method="POST",
                                                    body=urlencode(post_data), connect_timeout=5, request_timeout=5)
            url = json.loads(get_url.body.decode()).get('result', {}).get('ws_host')
            print url
            self.ws = yield websocket_connect(url, connect_timeout=5)
        except Exception as e:
            print("connection error,{}".format(e))
        else:
            print("connected")
            self.run()

    @gen.coroutine
    def run(self):
        while True:
            msg = yield self.ws.read_message()
            if msg is None:
                self.ws = None
                break
            try:
                msg = json.loads(msg)
            except:
                self.ws = None
                break
            print(msg)
            if msg.get('type') != "channel_message":
                continue
            print(msg)
            #replay_func = Handler.get(msg.get("text"))
            text = msg.get('text')
            if self.me in text:
                text = text.replace(self.me, '')
                #print text
                #print self.me

                #raw_text = replay_func(self.openapi)
                #raw_text = randomWho(self.openapi)

                raw_text = checkRule(text, self.database, self.openapi)
                #print raw_text
                finish_text = json.dumps(
                    {"text": raw_text,
                     "vchannel_id": msg.get("vchannel_id"),
                     "call_id": 23,
                     # "refer_key": msg.get("key"),
                     "refer_key": '',
                     "type": "channel_message",
                     "channel_id": msg.get("channel_id")}
                )
                self.ws.write_message(finish_text)

    def keep_alive(self):
        if self.ws is None:
            self.connect()
        else:
            self.ws.write_message('{"call_id": 29, "type": "ping"}')


if __name__ == "__main__":
    Client()
