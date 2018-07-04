#!/usr/bin/env python3


import requests
from requests.auth import HTTPBasicAuth

import qai_helper


def dct2str(dct) -> str:
    return "\n".join(["{}: {}".format(k, v) for k, v in dct.items()])


def old_school():
    s = requests.Session()
    s.auth = ("wscott", "abc123")
    head_dct = {'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    r = s.get("http://192.168.69.170:4567/qcs_location/list", headers=head_dct)
    print("response code: {}\n".format(r.status_code))
    print(r)
    print("to server\n", dct2str(r.request.headers), "\n\n")
    print("from server\n", dct2str(r.headers), "\n\n")
    # print("content type: {}\n\n".format(r,headers['Content-Type']))

    jj = r.json()
    print("json\n", jj, "\n\n")
    # print(r.text)
    # print(r.content)


def new_school():
    s = qai_helper.Session()
    qai_path = "http://192.168.69.170:4567"
    s.login(qai_path, 'wscott', 'abc123')
    rjson = s.get_json('/qcs_location/list')
    print("JSON IS : {}".format(rjson))
    for loc_dct in rjson:
        print("{}\n".format(loc_dct))

if __name__ == "__main__":
    new_school()
