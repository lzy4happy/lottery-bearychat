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



THE_ROBT_TOKENT = "d50245610146e046325d6d8f7e588421"

def checkRule(text, usrs):
    if (text.find(u"抽") != -1 or text.find(u"选"))  and util.getResultForDigit(text) > 0:
        num = util.getResultForDigit(text)
        print 'number == ' + str(num)
        who = randomWho(num, usrs)

        if(who.find(u"@") != -1):
            return u"恭喜中奖啦!>_<" + who
        else:
            return u'人员不足，程序员都被祭天了吗?'
    return None


def checkDatabase(text, database,  usrs):
    an = database(text)
    if an:
        who = randomWho(1, usrs)
        an = an.decode('utf-8').replace("@", who)
        return an
    return None


def randomWho(num, usrs):
    # usrs = client.user.list()
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

def getVChennalUser(client, chnnel_id):
    usrs = []
    try:
        info = client.vchannel.info(json= {"vchannel_id" : chnnel_id})
    except Exception as e:
        print e.message
    else:
        members = info['member_uids']
        for m in members:
            try:
                u = client.user.info(json={"user_id" : m})
                usrs.append(u)
            except Exception as e:
                print e.message
    return usrs

def getUserList(client):
    usrs = []
    try:
        usrs = client.user.list()
    except Exception as e:
        print e.message
    return usrs

def getChennalUser(client, chnnel_id):
    try:
        info = client.vchannel.info(json= {"channel_id" : chnnel_id})
    except Exception as e:
        print e.message
    else:
        print info

class Client(object):
    def __init__(self):
        self.ioloop = IOLoop.instance()
        self.database = util.getSmailarDatabase()
        self.openapi = openapi.Client(THE_ROBT_TOKENT)
        self.me = '@<=' + self.openapi.user.me()['id'] + '=>'
        self.ws = None
        self.connect()
        PeriodicCallback(self.keep_alive, 20000, io_loop=self.ioloop).start()
        self.ioloop.start()

    @gen.coroutine
    def connect(self):
        print("trying to connect")
        try:
            post_data = {'token': THE_ROBT_TOKENT}
            get_url = yield AsyncHTTPClient().fetch("https://rtm.bearychat.com/start", method="POST",
                                                    body=urlencode(post_data), connect_timeout=5, request_timeout=5)
            url = json.loads(get_url.body.decode()).get('result', {}).get('ws_host')
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

            text       = msg.get('text')
            chennal_id = msg.get('vchannel_id')

            usrlist = []
            if chennal_id:
                usrlist = getVChennalUser(self.openapi, chennal_id)
            else:
                usrlist = getUserList(self.openapi)

            if text and self.me in text:
                text = text.replace(self.me, '')
                raw_text = checkRule(text, usrlist)

                finish_text = json.dumps(
                    {"text": "假装没看到",
                     "vchannel_id": msg.get("vchannel_id"),
                     "call_id": 23,
                     # "refer_key": msg.get("key"),
                     "refer_key": '',
                     "type": "channel_message",
                     "channel_id": msg.get("channel_id")}
                )

                if raw_text:
                    finish_text = json.dumps(
                        {"text": raw_text,
                         "vchannel_id": msg.get("vchannel_id"),
                         "call_id": 23,
                         # "refer_key": msg.get("key"),
                         "refer_key": '',
                         "type": "channel_message",
                         "channel_id": msg.get("channel_id")}
                    )
                raw_text = checkDatabase(text, self.database, usrlist)
                if raw_text:
                    finish_text = json.dumps(
                        {"text": raw_text,
                         "vchannel_id": msg.get("vchannel_id"),
                         "call_id": 23,
                         # "refer_key": msg.get("key"),
                         "refer_key": '',
                         "type": "channel_message",
                         "channel_id": msg.get("channel_id")}
                    )

                try:
                    self.ws.write_message(finish_text)
                except Exception as e:
                    print e.message


    def keep_alive(self):
        if self.ws is None:
            self.connect()
        else:
            self.ws.write_message('{"call_id": 29, "type": "ping"}')


if __name__ == "__main__":
    Client()
