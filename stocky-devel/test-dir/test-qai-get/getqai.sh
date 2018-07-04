#!/bin/bash

# this is the actual QAI
#wget https://qai.cfenet.ubc.ca:3000/qcs_reagents/json_get

# this is James N. url
wget -d --header="Accept: application/json" --user wscott --password abc123  http://192.168.69.170:4567/qcs_location/list
# curl -u wscott:abc123  http://192.168.69.170:4567/qcs_location/list
