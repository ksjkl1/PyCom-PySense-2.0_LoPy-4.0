import binascii
import ubinascii
import machine
import micropython
import pycom
import socket
import struct
import sys
import time
import config

from network import LoRa
from pysense import Pysense
from SI7006A20 import SI7006A20 	# Humidity and Temperature Sensor
from LTR329ALS01 import LTR329ALS01 	# Digital Ambient Light Sensor
from MPL3115A2 import MPL3115A2         # Barometric Pressure/Altitude/Temperature Sensor
from LIS2HH12 import LIS2HH12           # 3-axis accelerometer

RED = 0xFF0000
YELLOW = 0xFFFF33
GREEN = 0x007F00
OFF = 0x000000

def flash_led_to(color=GREEN, t1=1):
    pycom.rgbled(color)
    time.sleep(t1)
    pycom.rgbled(OFF)



def join_lora(force_join = False):
    '''Joining The Things Network '''
    print('Joining TTN')

    # restore previous state
    if not force_join:
        lora.nvram_restore()

    if not lora.has_joined() or force_join == True:

        # create an OTA authentication params
        app_eui = ubinascii.unhexlify('70B3D57ED003C711')
        app_key = ubinascii.unhexlify('7DCBF9E69CE5845166FC2941CDE8801C')
        dev_eui = ubinascii.unhexlify('70B3D54990286DB7')
        print("app_eui = 70B3D57ED003C711")
        print("app_key = 7DCBF9E69CE5845166FC2941CDE8801C")
        print("dev_eui = 70B3D54990286DB7")
        print("") 


        #remove all channels
        for channel in range(0, 10):
            lora.remove_channel(channel)

        # set the 3 default channels to the same frequency (must be before sending the OTAA join request)
        lora.add_channel(0, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
        lora.add_channel(1, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
        lora.add_channel(2, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
        #lora.remove_channel(3)
        #lora.remove_channel(4)
        #lora.remove_channel(5)
        #lora.remove_channel(6)

        # join a network using OTAA if not previously done
        lora.join(activation=LoRa.OTAA, auth=(app_eui, app_key), timeout=0)

        # wait until the module has joined the network
        while not lora.has_joined():
            time.sleep(2.5)

        # saving the state
        lora.nvram_save()

        # returning whether the join was successful
        if lora.has_joined():
            flash_led_to(GREEN)
            print('LoRa Joined')
            return True
        else:
            flash_led_to(RED)
            print('LoRa Not Joined')
            return False

    else:
        return True

pycom.heartbeat(False) # Disable the heartbeat LED

# Getting the LoRa MAC
lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.EU868)
print("") 
print("Device LoRa MAC:", binascii.hexlify(lora.mac()))

flash_led_to(YELLOW)
# joining TTN
join_lora(True)

# create a LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

#    s.setsockopt(socket.SOL_LORA, socket.SO_DR, 0)
s.setsockopt(socket.SOL_LORA, socket.SO_DR, config.LORA_NODE_DR)

s.setblocking(False)

# Init the libraries
pysense = Pysense()
mpl3115a2 = MPL3115A2()     # Barometric Pressure Sensor with Altimeter
ltr329als01 = LTR329ALS01() # Digital Ambient Light Sensor
si7006a20 = SI7006A20()     # Humidity and Temperature sensor
lis2hh12 = LIS2HH12() #     3-Axis Accelerometer

while True:

    # Read the values from the sensors
    voltage = pysense.read_battery_voltage()
    temperature = mpl3115a2.temperature()
    pressure = mpl3115a2.pressure()
    light = ltr329als01.light()[0]
    humidity = si7006a20.humidity()
    roll = lis2hh12.roll()
    pitch = lis2hh12.pitch()

    # Debug sensor values
    print('voltage:{}, temperature:{}, pressure:{}, light:{}, humidity:{}, roll:{}, pitch:{}'.format(voltage, temperature, pressure, light, humidity, roll, pitch))

    clean_bytes = struct.pack(">iiiiiii",
        int(temperature * 100), # Temperature in celcius
        int(pressure * 100), # Atmospheric pressure in bar
        int(light * 100), # Light in lux
        int(humidity * 100), # Humidity in percentages
        int(roll * 100), # Roll in degrees in the range -180 to 180
        int(pitch * 100), # Pitch in degrees in the range -90 to 90
        int(voltage * 100)) # Battery voltage

    # send the data over LPWAN network
    s.send(clean_bytes)

    payload = struct.pack(">iiiiiii",
        int(temperature * 100), # Temperature in celcius
        int(pressure * 100), # Atmospheric pressure in bar
        int(light * 100), # Light in lux
        int(humidity * 100), # Humidity in percentages
        int(roll * 100), # Roll in degrees in the range -180 to 180
        int(pitch * 100), # Pitch in degrees in the range -90 to 90
        int(voltage * 100)) # Battery voltage

    s.send(payload)


    pycom.rgbled(0x007f00) # Make the LED light up in green
    time.sleep(0.2)
    pycom.rgbled(0x000000)
    time.sleep(2.8)

    # Wait for 60 seconds before moving to the next iteration
    time.sleep(60)

