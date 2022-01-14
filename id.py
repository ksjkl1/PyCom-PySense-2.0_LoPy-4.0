from network import WLAN
import binascii
wl = WLAN()
binascii.hexlify(wl.mac())[:6] + 'FFFE' + binascii.hexlify(wl.mac())[6:]

