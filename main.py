import config
from nanogateway import NanoGateway

print("\nSetup LORAWAN gateway\n")

if __name__ == '__main__':
    nanogw = NanoGateway(
        id=config.GATEWAY_ID,
        frequency=config.LORA_FREQUENCY,
        datarate=config.LORA_GW_DR,
        ssid=config.WIFI_SSID,
        password=config.WIFI_PASS,
        server=config.SERVER,
        port=config.PORT,
        ntp_server=config.NTP,
        ntp_period=config.NTP_PERIOD_S
        )

nanogw.start()   

print("Main script\n")

import binascii
import machine
import micropython
import pycom
import socket
import struct
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

lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.EU868, sf=7, tx_retries=2, power_mode=LoRa.ALWAYS_ON)

# create an OTA authentication params


app_eui = binascii.unhexlify('70B3D54990286DB7')
app_key = binascii.unhexlify('130025DF47244226668667E64DD49EE1')
dev_eui = binascii.unhexlify('70B3D54990286DB7')

print("OTAA settings\n")
print("app_eui " + str(app_eui))
print("app_key " + str(app_key))
print("dev_eui " + str(dev_eui))

dev_addr = struct.unpack(">l", binascii.unhexlify('260BF093'))[0]
nwk_swkey = binascii.unhexlify('EFC7DB420ACADAFA5EBD7CDC6B38B0A6')
app_swkey = binascii.unhexlify('8534995EB04A13B3F760CD6B77E32C9C')

print("\nABP settings\n")
print("dev_addr  " + str(dev_addr))
print("nwk_swkey " + str(nwk_swkey))
print("app_swkey " + str(app_swkey))

#pycom-pysense-wipy-lopy4@ttn
#NNSXS.OAB6LKM4C2FURWSWO5UBO72Q5PVG6XHJX6RFT3I.EZ76DNNNB3S6UOQ6FQGFSW43REBG3DOZ7PHICCWKMC3UNHTBNEMQ

print("\nInit Lora\n")

# set the 3 default channels to the same frequency (must be before sending the OTAA join request)
lora.add_channel(0, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
lora.add_channel(1, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
lora.add_channel(2, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)


# join a network using OTAA
#lora.join(activation=LoRa.OTAA, auth=(dev_eui, app_eui, app_key), timeout=0, dr=config.LORA_NODE_DR)
# join a network using ABP
lora.join(activation=LoRa.ABP, auth=(dev_addr, nwk_swkey, app_swkey))

join_wait = 0
while True:
    time.sleep(10.5)
    if not lora.has_joined():
        print('Not joined yet...')
        join_wait += 1
        if join_wait == 5:
            join_wait = 0
    else:
        break

# remove all the non-default channels
for i in range(3, 16):
    lora.remove_channel(i)

# create a LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

# set the LoRaWAN data rate
s.setsockopt(socket.SOL_LORA, socket.SO_DR, config.LORA_NODE_DR)

# make the socket non-blocking
s.setblocking(False)

time.sleep(5.0)

print("Start reading sensors\n")

pysense = Pysense()
mpl3115a2 = MPL3115A2()     # Barometric Pressure Sensor with Altimeter
ltr329als01 = LTR329ALS01() # Digital Ambient Light Sensor
si7006a20 = SI7006A20()     # Humidity and Temperature sensor
lis2hh12 = LIS2HH12() #     3-Axis Accelerometer


count = 1
while (count < 60):
    print('Count is', count)
    print('\n*** Main loop\nPyCom PySense 2.0 WiPy LoPy 4.0\n')
    print("Reading sensors data en send to TTN\n")
    pycom.rgbled(0x007f00) # Make the LED light up in green
    time.sleep(0.2)
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
    print('send clean_bytes')
    s.send(clean_bytes)

    payload = struct.pack(">iiiiiii",
        int(temperature * 100), # Temperature in celcius
        int(pressure * 100), # Atmospheric pressure in bar
        int(light * 100), # Light in lux
        int(humidity * 100), # Humidity in percentages
        int(roll * 100), # Roll in degrees in the range -180 to 180
        int(pitch * 100), # Pitch in degrees in the range -90 to 90
        int(voltage * 100)) # Battery voltage

    print('send payload')
    s.send(payload)

    data = s.recv(64)
    print(data)

    lora.nvram_save()


    # reading sensors data and send to pybytes
    pycom.rgbled(0x007ff33) # Make the LED light up in yellow
    time.sleep(0.2)
    print("\nReading sensors data en send to PyBytes\n")

    from LIS2HH12 import LIS2HH12
    from SI7006A20 import SI7006A20
    from LTR329ALS01 import LTR329ALS01
    from MPL3115A2 import MPL3115A2,ALTITUDE,PRESSURE

    pycom.heartbeat(False)
    pycom.rgbled(0x0A0A08) # white

    py = Pysense()

    mp = MPL3115A2(py,mode=ALTITUDE) # Returns height in meters. Mode may also be set to PRESSURE, returning a value in Pascals
    print("Temperature: " + str(mp.temperature()))
    print("Altitude: " + str(mp.altitude()))
    mpp = MPL3115A2(py,mode=PRESSURE) # Returns pressure in Pa. Mode may also be set to ALTITUDE, returning a value in meters
    print("Pressure: " + str(mpp.pressure()))

    si = SI7006A20(py)
    print("Temperature: " + str(si.temperature())+ " deg C and Relative Humidity: " + str(si.humidity()) + " %RH")
    print("Dew point: "+ str(si.dew_point()) + " deg C")
    t_ambient = 24.4
    print("Humidity Ambient for " + str(t_ambient) + " deg C is " + str(si.humid_ambient(t_ambient)) + "%RH")

    lt = LTR329ALS01(py)
    print("Light (channel Blue lux, channel Red lux): " + str(lt.light()))

    li = LIS2HH12(py)
    print("Acceleration: " + str(li.acceleration()))
    print("Roll: " + str(li.roll()))
    print("Pitch: " + str(li.pitch()))

    print("Battery voltage: " + str(py.read_battery_voltage()))

    pybytes.send_signal(0, str(mp.temperature()))
    pybytes.send_signal(1, str(si.temperature()))
    pybytes.send_signal(2, str(mp.altitude()))
    pybytes.send_signal(3, str(mpp.pressure()))
    pybytes.send_signal(4, str(si.humidity()))
    pybytes.send_signal(5, str(si.dew_point()))
    pybytes.send_signal(6, str(si.humid_ambient(t_ambient)))
    pybytes.send_signal(7, str(lt.light()))
    pybytes.send_signal(8, str(py.read_battery_voltage()))

    print("PyCom4_PySense_2.0_LoPy_4.0\n")

    # Wait for 60 seconds before moving to the next iteration
    count = count + 1 
    print("Sleep 60 seconds\n")
    time.sleep(60)
machine.reset()
