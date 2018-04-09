#!/bin/bash

# This script should be run on the host machine (i.e. NOT in the docker container) before
# launching the docker container.

# Essentially, the result of running this script should be a /dev/rfcomm0 device file representing
# a serial connection ove bluetooth to the RFID reader unit.

# NOTE 1: The name of the device /dev/rfcomm0 must match the name in the stocky serverconfig file.
# NOTE 2: Determine the bluetooth address of your reader with 'sudo hcitool scan' and
# change the address to connecte to here

# NOTE 3: TO connect to the RFID reader, activate the trigger so that the blue LED is flashing,
# then run this script. The devices (i.e. reader and computer) must have been previously
# paired to allow this connection.

sudo rfcomm connect /dev/rfcomm0 88:6B:0F:86:4D:F9

