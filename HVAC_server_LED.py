#####################################################################
# This program is used as a server to interface with HVAC Controller
# It is listening for TCP connection on port 60606 by default
#####################################################################

import socket
import sys
import smbus
import time
import RPi.GPIO as GPIO
bus = smbus.SMBus(1)

ADC_addr = 0x1D # Address of the ADC chip on the ADDA board
DAC_addr = 0x1F # Address of the ADC chip on the ADDA board 

RLED = 35   # Pin number (on board) of the red LED
GLED = 37   # Pin number (on board) of the green LED

ON = GPIO.HIGH # Voltage level to turn on a LED
OFF = GPIO.LOW # Voltage level to turn off a LED

###########################################
# Initialize indicator LEDs on the ADDA
# board                          
#                                         
# Parameter: None                         
# Return value: None                      
###########################################
def init_LED():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)

    GPIO.setup(RLED, GPIO.OUT)
    GPIO.setup(GLED, GPIO.OUT)
    GPIO.output(RLED, OFF)
    GPIO.output(GLED, OFF)

###########################################
# Initialize AD chip on the ADDA board    
# to mode 1 with external VREF and enable 
# channel 1 only                          
#                                         
# Parameter: None                         
# Return value: None                      
###########################################
def init_ADC():
	while bus.read_byte_data(ADC_addr, 0x0C) & 0x02: 	# Wait for device to get ready
		pass
	bus.write_byte_data(ADC_addr, 0x0B, 0x03) 			# Mode 1 with external reference voltage
	bus.write_byte_data(ADC_addr, 0x08, 0xFE)			# Disable all channels except channel 1

###########################################
# Initialize DA chip on the ADDA board    
# to external VREF                        
#                                         
# Parameter: None                         
# Return value: None                      
###########################################
def init_DAC():
    bus.write_i2c_block_data(DAC_addr, 0b00100000, [  0,   0]) # External reference (5V)
    bus.write_i2c_block_data(DAC_addr, 0b11000000, [127, 127]) # Write data to all registers
    bus.write_i2c_block_data(DAC_addr, 0b11000001, [  0,   0]) # Update all DAC latches with current register

###########################################
# Start an AD conversion on given channel 
# and return the reading                  
#                                         
# Parameter: channel number               
# Return value: AD reading, (-1 when      
#               conversion failed)        
###########################################
def get_ADC(channel):
    try:
        print("Reading analog signal from channel ", channel, "...", sep='')
        channel_base = 0x20
        bus.write_byte_data(ADC_addr, 0x09, 0x01) 			# Start a conversion
        while bus.read_byte_data(ADC_addr, 0x0C) & 0x01: 	# Wait for ADC conversion
            pass
        return bus.read_byte_data(ADC_addr, channel_base+channel) * 5 / 255
    except:
        print("ADC Error:", sys.exc_info()[1])
        return -1

###########################################
# Start a DA conversion on a given output 
# channel                                 
#                                         
# Parameter: channel number, voltage value
# Return value: 0 if success, -1 if failed
###########################################
def set_DAC(channel, value):
    try:
        print("Setting ", value, "V to channel ", channel, "...", sep='')
        channel_base = 0b10110000
        bus.write_i2c_block_data(DAC_addr, channel_base+channel, [int(value*255/5), 0]) # Write data to first output (5V/255)*100 = 1.96V
        return 0
    except:
        print("DAC Error:", sys.exc_info()[1])
        return -1

###########################################
# Check if a set command is valid         
#                                 
# Parameter: command                      
# Return value: A truple with controller
#               ID and desired voltage
#               value if the command is 
#               valid. Return (-1, -1) if
#				it is not valid                      
###########################################
def valid_set_cmd(cmd):
    controllers = ["temp", "fan", "dummy", "ep1", "ep2", "ep3", "ep4"]
    fan_levels = ["off", "low", "medium", "high"]
    
    try:
        if len(cmd) == 3:
            if cmd[1] in controllers and cmd[1] != "dummy":
                controller = controllers.index(cmd[1])
                if controller == 1 and cmd[2] in fan_levels:
                    value = fan_levels.index(cmd[2])
                elif controller == 0:
                    value = float(cmd[2]) * 5 / 11 - 80 / 11
                elif controller < len(controllers) and controller > 1:
                    value = float(cmd[2])
                else:
                    value = -1
                
                if value >= 0 and value <= 5:
                    return (controller, value)
    except:
        pass     
    return (-1, -1)

###########################################
# Parse the command into a list of commands      
#                                 
# Parameter: command                      
# Return value: A truple with list of the
#               commands and the device
#               the command controls/readss                   
###########################################
def compile_cmd(cmd):
    msg = []
    device = 0
    
    if len(cmd) != 0:
        cmd = cmd.strip().lower().split()
    
        if cmd[0] == "read":
            if len(cmd) == 2:
                sensors = ["t1", "t2", "t3", "t4", "t5", "rh", "co2"]
                if cmd[1] in sensors and cmd[1] != "dummy":
                    vol = 0.5+sensors.index(cmd[1])*0.4
                    if sensors.index(cmd[1]) == 0:
                        vol = 0.6
                    msg.extend(["set", 2, vol])


                    ################################################################
                    ################################################################
                    ##                                                            ## 
                    ##  Uncomment the folloing lines if you want a delay between  ##
                    ##  set the out put voltage and get the sensor reading        ##
                    ##                                                            ##          
                    ################################################################
                    ################################################################
                    delay_time_in_second = 5
                    msg.extend(["sleep", delay_time_in_second, 0])


                    msg.extend(["get", 0, 0])
                    msg.extend(["set", 2, 0])
                    device = sensors.index(cmd[1])
        
        elif cmd[0] == "set":
            (controller, value) = valid_set_cmd(cmd)
            if controller != -1:
                msg.extend(["set", 1, value])
                msg.extend(["set", 0, 0.75+controller*0.5])
				# delay_time_in_second = 10
                # msg.extend(["sleep", delay_time_in_second, 0])
                msg.extend(["set", 0, 0])
                device = controller
                
    return (msg, device)
    
###########################################
# Parse the data to readable value with
# proper units      
#                                 
# Parameter: sensor number, reading recieved                      
# Return value: parsed messaged                  
###########################################
def compile_data(device, data):
    if device < 5:
        reading = str(round(16 + data * 2.2, 2)) + " degree"
    elif device == 5:
        reading = str(round(data * 20, 2)) + " RH"
    elif device == 6:
        reading = str(round(data * 20, 2)) + " PPM"
    else:
        reading = "Error"
    return reading

###########################################
# Construct help message
#                                
# Parameter: None                      
# Return value: the help message                  
###########################################
def print_help():
    msg = ''
    msg += "Read sensor:\t\tread t1|t2|t3|t4|t5|rh|co2\r\n"
    msg += "Set temperature:\tset temp [temperature from 0 to 50 degree]\r\n"
    msg += "Set fan speed:\t\tset fan off|low|medium|high\r\n"
    msg += "Set EP level:\t\tset ep1|ep2|ep3|ep4 [EP value from 0 to 5]\r\n"
    msg += "Quit:\t\t\tquit\r\n"
    return msg

###########################################
# Interfacing with ADDA board to excute 
# commands in givec command list
#                                
# Parameter: command list                     
# Return value: return value list from 
#				command excuted                  
###########################################
def HVAC(cmd):
    print(cmd)
    try:
        if (len(cmd)-1)%3 == 2:
            msg = []
            for i in range(0, len(cmd), 3):
                print(i);
                if cmd[i] == "set":
                    msg.append(set_DAC(cmd[i+1], cmd[i+2]))
                elif cmd[i] == "get":
                    msg.append(get_ADC(cmd[i+1]))
                elif cmd[i] == "sleep":
                    time.sleep(cmd[i+1])
                else:
                    raise Exception("Unkown Command")
        else:
            raise Exception("Unkown Command")
    except:
        print("Unkown Commands")
        print("Unexpected error:", sys.exc_info()[1])
        msg = "Unkown Commands"
        
    return msg


ip = '0.0.0.0' 
if len(sys.argv) == 2:
	port = int(sys.argv[1])
else:
	port = 60606

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((ip, port))
    
    init_DAC()
    init_ADC()
    init_LED()
    
    print("Server successfully started on port", port)
    GPIO.output(RLED, ON)

except:
    print("Fatal Error: Server initialization failed")
    print("Unexpected error:", sys.exc_info()[1])
    sys.exit(1)

while 1:
    try:
        s.listen(1)
        print("Server is waiting for new connetion...")
    except:
        print("Fatal Error: Failed to listen for new connction")
        print("Unexpected error:", sys.exc_info()[1])
        GPIO.output(RLED, OFF)
        sys.exit(1)
        
    try:
        (client, address) = s.accept()
        print("Accepted client from", address)
        GPIO.output(GLED, ON)
        connected = True
    except:
        print("Failed to make connction with client")
        print("Unexpected error:", sys.exc_info()[1])
        connected = False
       
    while connected:
        try:
            cmd = client.recv(1024).decode('ASCII').strip()
            recieved = True
        except:
            print("Failed to recieve command, closing connection...")
            connected = False
            recieved = False
            print("Unexpected error:", sys.exc_info()[1])
            

        if recieved:
            print(cmd)
            if cmd == "quit":
                connected = False
            else:
                (cmds, device) = compile_cmd(cmd)
                if len(cmds) != 0:
                    recv = HVAC(cmds)
                    if recv == "Unkown Commands" :
                        msg = print_help()
                            
                    elif len(recv) > 0:
                        if -1 not in recv:
                            cmd = cmd.strip().split()
                            if cmd[0] == "read":
                                msg = cmd[1] + " reading is " + compile_data(device, float(recv[-2])) + "\r\n"
                            else:
                                msg = cmd[1] + " is set to " + cmd[2] + "\r\n"
                        else:
                            msg = "ADDA error\r\n"
                    else:
                        msg = "Nothing recieved\r\n" 
                else:
                    msg = print_help()
                try: 
                    client.sendall(msg.encode("ASCII"))
                except:
                    print("Failed to send massage, closing connections...")
                    connected = False

    GPIO.output(GLED, OFF)
    try:
        client.close()
        print("Server connction with current client is closed\r\n")
    except:
        print("Close connection with current client failed\r\n")
        print("Unexpected error:", sys.exc_info()[1])
