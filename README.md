# SMS Controlled Garage Door Opener

Control your garage using standard text messaging

## Overview
The garage is controlled using a Raspberry Pi Zero W with a 2 channel relay board.
The Raspberry Pi can only receive commands using SMS from authorized numbers.

## Credits
Uses the [Google Voice Python API](https://github.com/pettazz/pygooglevoice) supplied by Pettazz

## Supplies

**Hardware**

The prices given are the ones at the time of writing and are subject to change. Items without the price are those that I had already.

- [Raspberry Pi Zero W Bundle](https://www.amazon.com/gp/product/B0748MBFTS/ref=oh_aui_detailpage_o00_s00?ie=UTF8&psc=1) - $25.99 (The bundle comes with a power supply, case, GPIO headers, and a heatsink)
- [2 Channel Relay Module](https://www.amazon.com/gp/product/B0057OC6D8/ref=oh_aui_detailpage_o00_s01?ie=UTF8&psc=1) - $7.49
- [Magnetic Switch](https://www.amazon.com/gp/product/B0009SUF08/ref=oh_aui_detailpage_o00_s00?ie=UTF8&psc=1) - $4.73
- [Jumper Wires](https://www.amazon.com/gp/product/B077NH83CJ/ref=oh_aui_detailpage_o00_s00?ie=UTF8&psc=1) - $4.99
- 2 Conductor Wire
- Soldering Iron and Solder (To solder GPIO header to Raspberry Pi Zero W)
- Garage Door Remote - Optional (I needed to use one since my garage opener had a powered LCD control panel which would short if I connected the relay module to the garage terminals.)

**Software**

- [Google Voice Python API](https://github.com/pettazz/pygooglevoice)
- [Raspian](https://www.raspberrypi.org/downloads/raspbian/)
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)

## Notes

To run the garageSMSPi.py file, you need to create a config.py file with the following variables:

- gVoiceUsrName
- gVoicePswd
- door1Name 
- door2Name 
- authorizedNumbers
- names

If the config.py file does not have these variables, the script will **NOT** run.

You will also need to create a Logs directory where the error logs will be stored.

I have my Pi run this script at start up using crontab.
