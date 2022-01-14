import binascii
import ubinascii
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

lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.EU868)

# create an OTA authentication params
 
app_eui = binascii.unhexlify('70B3D57ED0042ED7')
app_key = binascii.unhexlify('8316745457492A90842017B988B5F291')
dev_eui = binascii.unhexlify('0061AFB65C88ABC9')

print("")
print("OTAA settings")
print("")
print("app_eui " + str(app_eui))
print("app_key " + str(app_key))
print("dev_eui " + str(dev_eui))

dev_addr = struct.unpack(">l", binascii.unhexlify('26011828'))[0]
nwk_swkey = binascii.unhexlify('9B8852512814BF62047B0952BBA4DF7E')
app_swkey = binascii.unhexlify('0E31DD97AE7D11EE6383245D05549297')

	
print("")
print("ABP settings")
print("")
print("dev_addr  " + str(dev_addr))
print("nwk_swkey " + str(nwk_swkey))
print("app_swkey " + str(app_swkey))
#pycom-pysense-wipy-lopy@ttn
#NNSXS.Z4KU3B7ITY266IGLLRVX2HUJMDYNAZVWR4W6V5I.7I5UX7SCZZQ53QU2NLXOZYUWW4J54GGGI7B45HSML6ORDJE2OY4A


# set the 3 default channels to the same frequency (must be before sending the OTAA join request)
lora.add_channel(0, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
lora.add_channel(1, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
lora.add_channel(2, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)

# join a network using OTAA
#lora.join(activation=LoRa.OTAA, auth=(dev_eui, app_eui, app_key), timeout=0, dr=config.LORA_NODE_DR)
# join a network using ABP
lora.join(activation=LoRa.ABP, auth=(dev_addr, nwk_swkey, app_swkey))

# wait until the module has joined the network
while not lora.has_joined():
    time.sleep(2.5)
    print('Not joined yet...')

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


# Init the libraries

pysense = Pysense()
mpl3115a2 = MPL3115A2()     # Barometric Pressure Sensor with Altimeter
ltr329als01 = LTR329ALS01() # Digital Ambient Light Sensor
si7006a20 = SI7006A20()     # Humidity and Temperature sensor
lis2hh12 = LIS2HH12() #     3-Axis Accelerometer


while True:

    print("")
    print("Reading sensors data en send to TTN")
    print("")
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


    pycom.rgbled(0x007fff) # Make the LED light up in green
    time.sleep(0.2)
    #pycom.rgbled(0x000000)
    time.sleep(2.8)


    # reading sensors data and send to pybytes
    print("")
    print("Reading sensors data en send to PyBytes")
    print("")

    from LIS2HH12 import LIS2HH12
    from SI7006A20 import SI7006A20
    from LTR329ALS01 import LTR329ALS01
    from MPL3115A2 import MPL3115A2,ALTITUDE,PRESSURE

    pycom.heartbeat(False)
    pycom.rgbled(0x0A0A08) # white

    py = Pysense()

    mp = MPL3115A2(py,mode=ALTITUDE) # Returns height in meters. Mode may also be set to PRESSURE, returning a value in Pascals
    print("MPL3115A2 temperature: " + str(mp.temperature()))
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

    print("")
    print("PyCom4_PySense_2.0_LoPy_4.0")
    print("")


    # Wait for 60 seconds before moving to the next iteration
    print("Sleep 60 seconds")
    time.sleep(60)
