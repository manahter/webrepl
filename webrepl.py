#!/usr/bin/env python
import os
import re
import time
import struct
import socket
from threading import Thread
from noter import Noter

noter = Noter(module="WebRepl",
              module_path=os.path.dirname(__file__),
              mode=1,
              keep=True
              )

# Treat this remote directory as a root for file transfers
SANDBOX = ""
# SANDBOX = "/tmp/webrepl/"

WEBREPL_REQ_S = "<2sBBQLH64s"
WEBREPL_PUT_FILE = 1
WEBREPL_GET_FILE = 2
WEBREPL_GET_VER = 3

# Karşı cihaza yükleyeceğimiz dosyanın adı SETUP_FILENAME.py
SETUP_FILENAME = "bilen"

# Karşı cihaza yükleyeceğimiz dosyanın içeriği
SETUP_CONTENT = rb"""
from machine import Pin

pins = []

for i in (0, 2):
    p = Pin(i, Pin.OUT)
    p.off()
    pins.append(p)
"""


HANDSHAKE_TEXT = b"""\
GET / HTTP/1.1\r
Host: localhost\r
Connection: Upgrade\r
Upgrade: websocket\r
Sec-WebSocket-Key: foo\r
\r
"""
# from ctypes import int


class websocket:
    timeout = 3

    def __init__(self, s):
        self.s = s
        self.buf = b""

    def writetext(self, data):
        self.write(data, istext=True)

    def write(self, data, istext=False):
        ll = len(data)
        if ll < 126:
            # TODO: hardcoded "binary" type
            hdr = struct.pack(">BB", (0x82, 0x81)[istext], ll)
        else:
            hdr = struct.pack(">BBH", (0x82, 0x81)[istext], 126, ll)
        self.s.send(hdr)
        self.s.send(data)

    def recvexactly(self, sz):
        res = b""
        st = time.time()
        while sz:
            data = self.s.recv(sz)
            if time.time() - st > self.timeout:
                noter.warning(Webrepl.client_handshake.__name__, f"Timeout ; {self.timeout}")
                return False

            if not data:
                break
            res += data
            sz -= len(data)
        return res

    def read(self, size, text_ok=False, size_match=True):
        if not self.buf:
            while True:
                hdr = self.recvexactly(2)
                assert len(hdr) == 2
                fl, sz = struct.unpack(">BB", hdr)
                if sz == 126:
                    hdr = self.recvexactly(2)
                    assert len(hdr) == 2
                    (sz,) = struct.unpack(">H", hdr)
                if fl == 0x82:
                    break
                if text_ok and fl == 0x81:
                    break

                noter.info_grey(websocket.read.__name__, f"Got unexpected websocket record of type, skipping it {fl}")

                while sz:
                    skip = self.s.recv(sz)

                    noter.info_grey(websocket.read.__name__, f"Skip data ; {skip}")
                    sz -= len(skip)
            data = self.recvexactly(sz)
            assert len(data) == sz
            self.buf = data

        d = self.buf[:size]
        self.buf = self.buf[size:]
        if size_match:
            assert len(d) == size, len(d)
        return d

    @staticmethod
    def ioctl(req, val):
        assert req == 9 and val == 2


#@yapio
class Webrepl:
    isconnected = False
    timeout = 3

    # (Sent, read)
    queue = []
    messages = {}

    def __init__(self, host="", port=8266, password="", auto=True):
        """"""
        self.host = host
        self.port = port
        self.password = password
        self.auto = auto

        self.s = None
        self.ws = None

        if self.auto:
            self.connect()
            self.login()

    thread = None

    def start_with_thread(self):
        self.thread = Thread(target=self.loop)
        self.thread.daemon = True
        self.thread.start()

    def loop(self):
        while self.thread:
            if len(self.queue):
                send_msg = self.queue.pop(0)
                read_msg = self.send(send_msg[0], send_msg[1], on_thread=True)
                read_cod = send_msg[-1]
                self.messages[read_cod] = (send_msg[0], read_msg)

    def client_handshake(self, sock):
        cl = sock.makefile("rwb", 0)
        cl.write(HANDSHAKE_TEXT, )

        st = time.time()
        while cl.readline() != b"\r\n":
            if time.time() - st > self.timeout:
                noter.warning(Webrepl.client_handshake.__name__, f"Timeout ; {self.timeout}")
                return False

        return True

    def connect(self, host=None, port=None):
        if host:
            self.host = host
        if port:
            self.port = port

        if not self.host:
            self.isconnected = False
            return

        noter.notice(Webrepl.connect.__name__, f"Trying connecting to {self.host} {self.port}")

        self.s = socket.socket()

        addr = socket.getaddrinfo(self.host, self.port)[0][4]

        self.s.settimeout(self.timeout)

        try:
            self.s.connect(addr)
        except:
            noter.notice(Webrepl.connect.__name__, f"Connection failed")
            return

        noter.info(Webrepl.connect.__name__, "Handshake")

        if self.client_handshake(self.s):
            self.ws = websocket(self.s)

    def disconnect(self):
        if self.s:
            self.s.close()
        self.s = None
        self.ws = None
        self.thread = None
        noter.info_grey(Webrepl.disconnect.__name__, "Disconnected")

    def login(self, passwd=""):
        if passwd:
            self.password = passwd

        if not (self.password and self.ws):
            self.isconnected = False
            return

        noter.info_grey(Webrepl.login.__name__, f"Started")

        while True:
            c = self.ws.read(1, text_ok=True)
            if c == b":":
                assert self.ws.read(1, text_ok=True) == b" "
                break
        self.ws.write(self.password.encode("utf-8") + b"\r")

        noter.info_grey(Webrepl.login.__name__, f"Send Password ; {self.password}")

        resp = self.ws.read(64, text_ok=True, size_match=False)
        # b'\r\nWebREPL connected\r\n>>> '
        # b'\r\nAccess denied\r\n'
        if b"WebREPL connected" in resp:
            self.isconnected = True

        noter.info(Webrepl.login.__name__, f"Response ; {resp.decode('utf-8').strip().strip('>')}")

    def send(self, cmd, size=1024, on_thread=False):
        if not self.isconnected:
            return b""

        if self.thread and not on_thread:
            read_cod = max(self.messages) + 1 if self.messages else 1
            self.queue.append((cmd, size, read_cod))
            return read_cod

        noter.info(Webrepl.send.__name__, f"Sending Command ; {cmd}")
        self.ws.writetext(cmd.encode("utf-8") + b"\r\n")

        noter.info_grey(Webrepl.send.__name__, "Getting Response")
        resp = self.read(size)

        noter.info_grey(Webrepl.send.__name__, f"Got Response ; {resp}")
        return resp

    def read(self, size):
        resp = b''
        newline = False
        while True:
            r = self.ws.read(size, text_ok=True, size_match=False)

            if r == b'>>> ' and newline:
                break
            if r == b'\r\n':
                newline = True
            else:
                newline = False
            resp = resp + r

        noter.info(Webrepl.read.__name__, f"{resp}")
        return resp.decode("utf-8")

    def read_resp(self):
        data = self.ws.read(4)
        sig, code = struct.unpack("<2sH", data)
        assert sig == b"WB"
        return code

    def send_req(self, op, sz=0, fname=b""):
        rec = struct.pack(WEBREPL_REQ_S, b"WA", op, 0, 0, sz, len(fname), fname)

        noter.info_grey(Webrepl.put_file.__name__, f"Send request {rec if len(rec) < 10 else rec[:10]}... len: {len(rec)}")

        self.ws.write(rec)

    def set_binary(self):
        # Set websocket to send data marked as "binary"
        self.ws.ioctl(9, 2)

    def get_version(self):
        if self.isconnected:
            self.send_req(WEBREPL_GET_VER)
            d = self.ws.read(3)
            d = struct.unpack("<BBB", d)
            noter.notice(Webrepl.get_version.__name__, f"{d}")
            return d

    def put_file(self, local_file, remote_file):
        sz = os.stat(local_file)[6]
        dest_fname = (SANDBOX + remote_file).encode("utf-8")
        rec = struct.pack(WEBREPL_REQ_S, b"WA", WEBREPL_PUT_FILE, 0, 0, sz, len(dest_fname), dest_fname)

        noter.info(Webrepl.put_file.__name__, f"Put file struct {rec} {len(rec)}")

        self.ws.write(rec[:10])
        self.ws.write(rec[10:])
        assert self.read_resp() == 0
        cnt = 0
        with open(local_file, "rb") as f:
            while True:
                noter.info_grey(Webrepl.put_file.__name__, f"Sent {cnt} of {sz}")
                buf = f.read(1024)
                if not buf:
                    break
                self.ws.write(buf)
                cnt += len(buf)
        assert self.read_resp() == 0

    def put_file_content(self, file_content, remote_file):
        with open(remote_file, "wb") as f:
            f.write(file_content)

        self.put_file(remote_file, remote_file)
        os.remove(remote_file)

    def get_file_content(self, remote_file):
        content = b''
        src_fname = (SANDBOX + remote_file).encode("utf-8")
        rec = struct.pack(WEBREPL_REQ_S, b"WA", WEBREPL_GET_FILE, 0, 0, 0, len(src_fname), src_fname)

        noter.info(Webrepl.get_file_content.__name__, f"Get file content struct {rec} {len(rec)}")

        self.ws.write(rec)
        assert self.read_resp() == 0
        cnt = 0
        while True:
            self.ws.write(b"\0")
            (sz,) = struct.unpack("<H", self.ws.read(2))
            if sz == 0:
                break
            while sz:
                buf = self.ws.read(sz)
                if not buf:
                    raise OSError()
                cnt += len(buf)
                content += buf
                sz -= len(buf)

                noter.info_grey(Webrepl.get_file_content.__name__, f"Received {cnt} bytes")

        assert self.read_resp() == 0
        return content.decode("utf-8")

    def get_file(self, remote_file, local_file):
        with open(local_file, "w") as f:
            f.write(self.get_file_content(remote_file))
            noter.info_grey(Webrepl.get_file.__name__, f"Finished; {local_file}")

    def listdir(self, dirname=""):
        resp = self.send(f"uos.listdir('{dirname}')").split("\r\n")
        if len(resp) > 1:
            return re.findall(r"'([^']*)'", resp[1])

    def remove_file(self, remote_file):
        return self.send(f"uos.remove('{remote_file}')").split("\r\n")

    def mkdir(self, dirname="new_dir"):
        return self.send(f"uos.mkdir('{dirname}')")

    def rmdir(self, dirname="new_dir"):
        return self.send(f"uos.rmdir('{dirname}')")

    def setup_files(self):
        file_name = f"{SETUP_FILENAME}.py"
        if file_name not in self.listdir():
            self.put_file_content(SETUP_CONTENT, file_name)

        isexist = False
        boot_file_name = "boot.py"
        boot_content = self.get_file_content(boot_file_name)
        boot_append_import = f"from {SETUP_FILENAME} import *"

        for line in boot_content.split("\n"):
            if line.startswith(boot_append_import):
                isexist = True
                break

        if not isexist:
            boot_content = boot_content.encode("utf-8") + b"\r\n" + boot_append_import.encode("utf-8")
            self.put_file_content(boot_content, boot_file_name)

        return self.reset()

    def reset(self, hard=True):
        if hard:
            self.ws.write(b"machine.reset()")
            noter.notice(Webrepl.reset.__name__, "Hard Reset")
        else:
            # self.ws.write(b'\x0d')
            self.ws.write(b'\x04')
            noter.notice(Webrepl.reset.__name__, "Soft Reboot")

    def baudrate(self):
        pass
        # def baudrate(rate):
        #     machine.mem32[0x60000014] = int(80000000 / rate)


# wr.send("import esp;print(esp.flash_size())")
"""
1048576
"""

# wr.send("import esp;print(esp.check_fw())")
"""
size: 588024
md5: 17262cf5ecc565744088e3238cc89447
True                                    --> Bu değer firmware'nin doğru yüklendiğini söyler.
"""

# wr.send("import machine;print(machine.freq())")
"""
80000000
"""
# wr.send("import machine;print(machine.idle())")
"""
6406678
"""

# wr.send("import micropython;print(micropython.mem_info())")
"""
stack: 2128 out of 8192
GC: total: 37952, used: 3152, free: 34800
 No. of 1-blocks: 41, 2-blocks: 10, max blk sz: 18, max free sz: 1870
None
"""

# wr.send("import micropython;print(micropython.qstr_info())")
"""
qstr pool: n_pool=1, n_qstr=7, n_str_data_bytes=67, n_total_bytes=163
None
"""

# wr.send("import micropython;print(micropython.stack_use())")
"""
2096
"""


# wr.send("import sys;print(sys.platform)")
"""
esp8266
"""


# Python language version that this implementation conforms to, as a string.
# wr.send("import sys;print(sys.version)")
"""
3.4.0
"""

# wr.send("import os;print(os.uname())")
"""
(sysname='esp8266', nodename='esp8266', release='2.0.0(5a875ba)', version='v1.13 on 2020-09-02', machine='ESP module (1M) with ESP8266')
"""

# Kaynak; https://forum.micropython.org/viewtopic.php?t=2078
# veya  buradan araştır;
# https://github.com/espressif/esptool/blob/b96df73ba75cccd38ed6730829d8d01c0205e508/espressif/efuse/emulate_efuse_controller_base.py#L58
# https://github.com/espressif/esptool/blob/master/esptool.py#L1071
# wr.send("import machine;print(machine.mem32[0x60000014])")
"694"

# print(wr.get_file_content("boot.py"))
"""
#import esp
#esp.osdebug(None)
import uos, machine
#uos.dupterm(None, 1) # disable REPL on UART(0)
import gc
import webrepl
webrepl.start()
gc.collect()

from bilen import *

Process finished with exit code 0

"""
# wr.get_file("bilen.py", "bilen_bizde.py")

# Get wifi strength
# a = network.WLAN(network.STA_IF)
# a.status('rssi')
# -> -70

if __name__ == "__main__":
    wr = Webrepl(host="192.168.1.38", password="123456")
    wr.send("import os;os.listdir()")
    wr.get_version()


"""
Output:

[NOTICE ] WebRepl   > Loaded       : /home/ova/0-Work/WebReplCli
[NOTICE ] WebRepl   > connect      : Trying connecting to 192.168.1.38 8266
[ INFO  ] WebRepl   > connect      : Handshake
[ iNFO  ] WebRepl   > login        : Started
[ iNFO  ] WebRepl   > login        : Send Password ; 123456
[ INFO  ] WebRepl   > login        : Response ; WebREPL connected

[ INFO  ] WebRepl   > send         : Sending Command ; import os;os.listdir()
[ iNFO  ] WebRepl   > send         : Getting Response
[ INFO  ] WebRepl   > read         : b"import os;os.listdir()\r\n['bilen.py', 'boot.py', 'webrepl_cfg.py']\r\n"
[ iNFO  ] WebRepl   > send         : Got Response ; import os;os.listdir()
['bilen.py', 'boot.py', 'webrepl_cfg.py']

[ iNFO  ] WebRepl   > put_file     : Send request b'WA\x03\x00\x00\x00\x00\x00\x00\x00'... len: 82
[NOTICE ] WebRepl   > get_version  : (1, 13, 0)

Process finished with exit code 0

"""