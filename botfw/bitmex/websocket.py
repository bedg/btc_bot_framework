import time
import json
import traceback
import hmac
import hashlib

from ..base.websocket import WebsocketBase


class BitmexWebsocket(WebsocketBase):
    def __init__(self, key=None, secret=None):
        super().__init__('wss://www.bitmex.com/realtime',
                         bool(key and secret))
        self.__key = key
        self.__secret = secret
        self.__auth_id = None
        self.__request_tabl = {}

    def command(self, op, args=[], description=None):
        msg = {"op": op, "args": args}
        self.send(msg)

        id_ = json.dumps(msg)
        self.__request_tabl[id_] = description or msg
        return id_

    def _authenticate(self):
        expires = int(time.time() * 1000)
        sign = hmac.new(
            self.__secret.encode(), f'GET/realtime{expires}'.encode(),
            hashlib.sha256).hexdigest()
        id_ = self.command('authKeyExpires', [self.__key, expires, sign])
        self.__auth_id = id_

    def _subscribe(self, ch):
        self.command('subscribe', [ch])

    def _on_message(self, msg):
        try:
            msg = json.loads(msg)
            table = msg.get('table')
            if table:
                self._handle_channel_message(table, msg)
            else:
                self.log.debug(f'revc: {msg}')
                req = msg.get('request')
                if req:
                    id_ = json.dumps(req)
                    req = self.__request_tabl[id_]
                    if 'success' in msg:
                        res = msg['success']
                        self.log.info(f'{req} => {res}')

                        if id_ == self.__auth_id:
                            self.is_auth = True
                    elif 'error' in msg:
                        status, error = msg['status'], msg['error']
                        self.log.error(f'{req} => {status}, {error}')

                        if id_ == self.__auth_id:
                            self.is_auth = False
        except Exception:
            self.log.debug(traceback.format_exc())
