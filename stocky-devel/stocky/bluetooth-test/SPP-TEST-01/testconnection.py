#!/usr/bin/env python3


# make sure the 1128 RFID reader can be communicated with and is set up properly for stocky




import bluetooth  as bt


def find_services():
    print("looking for services...")
    srv_lst = bt.discover_devices()
    print("GOOOT {}".format(srv_lst))





if __name__ == "__main__":
    find_services()
