# SCR_HVAC-controller
Code for Raspberry pi, who controlls HVAC
# HVAC Server

## Prequired Package
- python3
- python3-smbus
- python3-rpi.gpio

## Installation:

### Single time use
- In the same folder with HVAC_server.py
- excute: sudo python3 HVAC_server.py

### Install as server with startup
- add "python3 absolute_name_of_HVAC_server >> absolute_name_of_log_file" to end of /etc/rc.local before "exit 0"
- reboot to start the server

## Usage
- type any thing to get help message once connected

### LED Indicator
- Red on: 	Server is running
- Green on:	Connected to a client

### Help Message
- Read sensor:      read t1|t2|t3|t4|t5|rh|co2
- Set temperature:  set temp [temperature from 16 to 27 degree]
- Set fan speed:    set fan off|low|medium|high
- Set EP level:     set ep1|ep2|ep3|ep4 [EP value from 0 to 5]
- Quit:             quit

## Other
- If you want to enable a delay between set the out put voltage and get the sensor reading, please uncommnet line 143 and 144 in the HVAC_server.py file


