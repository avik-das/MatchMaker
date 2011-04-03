#!/usr/bin/env python

import cgi
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import json

import pyRserve
import uuid
import csv
import re
import string

import os

CSV_HEADERS = ["uid", "messages"] # TODO: add more
CSV_FIELD_SIZE_LIMIT = csv.field_size_limit()

CWD = os.path.abspath(os.curdir)
CSV_DIR = CWD + "/csv"
print "Working in '%s'" % CWD
print "Will place CSV files in '%s'" % CSV_DIR

def process_json_data(data):
    pdata = json.loads(data)

    row = {"uid": pdata["id"], "messages": ""}
    for feed in pdata["feed"]["data"]:
        if feed["from"]["id"] != pdata["id"]: continue
        if "message" not in feed: continue

        msg = feed["message"].replace("\n", "") + '~!MSG SEPARATOR!~'
        if len(row["messages"]) + len(msg) < CSV_FIELD_SIZE_LIMIT:
            row["messages"] += msg
        else:
            break

    return row

class OpenDataRecord(object):
    def __init__(self, fname):
        self.filename = fname
        self.openfile = open(fname, 'wb')
        self.csvwriter = csv.DictWriter(self.openfile, CSV_HEADERS)
        self.frienddata = []
        self.wroteself = False

    def add_self_data(self, jsondata):
        row = process_json_data(jsondata)
        self.csvwriter.writerow(row)
        self.wroteself = True

        for fd in self.frienddata:
            self.add_friend_data(fd)
        self.frienddata = []

    def add_friend_data(self, jsondata):
        if self.wroteself:
            row = process_json_data(jsondata)
            self.csvwriter.writerow(row)
        else:
            self.frienddata.append(jsondata)

    def close(self):
        print self.openfile
        self.openfile.close()
        self.openfile = None
        self.csvwriter = None

class PyRComm(BaseHTTPRequestHandler):
    opendatarecords = {}

    ADD_SELF_DATA   = re.compile(r'/add-self-data/(\S+)')
    ADD_FRIEND_DATA = re.compile(r'/add-friend-data/(\S+)')
    SEND_DATA       = re.compile(r'/send-data/(\S+)')

    def do_POST(self):
        if self.path.startswith("/start-record"):
            self.start_record()
            return

        res = self.ADD_SELF_DATA.match(self.path)
        if res:
            self.add_self_data(res.group(1))
            return

        res = self.ADD_FRIEND_DATA.match(self.path)
        if res:
            self.add_friend_data(res.group(1))
            return

        res = self.SEND_DATA.match(self.path)
        if res:
            self.send_data(res.group(1))
            return

        self.send_error(404, 'Invalid action: %s' % self.path)

    def start_record(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        try:
            recid = str(uuid.uuid1())
            odr = OpenDataRecord(CSV_DIR + "/%s.csv" % recid)
            self.opendatarecords[recid] = odr

            resp = {'uuid': recid}
            self.wfile.write(json.dumps(resp))
        except IOError:
            self.send_error(500, 'Unable to start new record')

    def add_self_data(self, odrid):
        odr = self.__getodr(odrid)
        odr.add_self_data(self.__getrdata())
        self.send_response(204)

    def add_friend_data(self, odrid):
        odr = self.__getodr(odrid)
        odr.add_friend_data(self.__getrdata())
        self.send_response(204)

    def send_data(self, odrid):
        try:
            odr = self.__getodr(odrid)
            fname = odr.filename
            odr.close()

            rconn = pyRserve.rconnect()
            rconn.r.source("/home/avik/Desktop/yourMatch.R")
            resp = rconn.r.classifyThis(fname)
            respreader = csv.reader(open(fname + ".out.csv", 'rb'))

            resp = {}
            first = True
            for row in respreader:
                if first:
                    first = False
                    continue
                resp[row[1]] = row[0]
            self.wfile.write(json.dumps(resp))

            del self.opendatarecords[odrid]
        except IOError:
            self.send_error(500, 'Unable to send/receive data to Rserve')

    def __getodr(self, odrid):
        if odrid not in self.opendatarecords:
            self.send_error(404, 'Given UUID not in use: %s' % odrid)

        return self.opendatarecords[odrid]

    def __getrdata(self):
        datalen = string.atoi(self.headers.getheader('content-length'))
        data = self.rfile.read(datalen)
        print data
        return data

def main():
    try:
        server = HTTPServer(('', 6543), PyRComm)
        print 'started HTTP server'
        server.serve_forever()
    except KeyboardInterrupt:
        print 'shutting down server'
        server.socket.close()

if __name__ == '__main__':
    main()
