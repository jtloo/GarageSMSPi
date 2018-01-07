#! /usr/bin/env python

from googlevoice import Voice
import sys
from bs4 import BeautifulSoup
import re
import time
import logging
import config
import RPi.GPIO as GPIO

"""###########################################################
	Support Functions
   ###########################################################"""

def getCurrTime():
	return time.strftime('%Y-%m-%d %I_%M_%S_%p', time.localtime())

"""###########################################################
	GPIO Initialization
   ###########################################################"""
GPIO.cleanup()
garageSensorPins = {config.door1Name:17, config.door2Name:21}
garageRelayPins = {config.door1Name:23, config.door2Name:24}

# set up GPIO
GPIO.setmode(GPIO.BCM)

def setupGPIO(sensorPin, relayPin):
	GPIO.setup(sensorPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	GPIO.setup(relayPin, GPIO.OUT)

GPIO.setup(17, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(23,GPIO.OUT)

"""###########################################################
	Logging Info
   ###########################################################"""

# set up logging to file - see previous section for more details
name = "./Logs/" + str(getCurrTime()) + ".log"
logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] [%(levelname)-8s] [%(name)-18s] --- %(message)s',
                    datefmt = '%Y-%m-%d %I:%M:%S %p',
                    filename= name,
                    filemode='w')

logger_base = logging.getLogger('Garage Pi')
logger_googleVoice = logging.getLogger('Google Voice Class')
logger_garageDoor = logging.getLogger('Garage Door Class')

"""###########################################################
	Vacation Mode
   ###########################################################"""
vacationStat = False
vacationNumber = ""

def vacationMode(turnOn, phoneNum):
	global vacationNumber, vacationStat
	mess = ""
	if vacationStat == turnOn:
		mess = "Vacation mode is already on"
	if turnOn == True:
		vacationNumber = phoneNum
		vacationStat = True
		mess = "Vacation mode now on"
	else:
		vacationNumber = "" 
		mess = "Vacation mode now off"
		vacationStat = False
	print(mess)
	print(vacationStat)
	logMess = mess + " for " + phoneNum
	logger_base.info(logMess)
	return mess


"""###########################################################
	Google Voice Class for messaging
   ###########################################################"""
class googleVoice:

	#The authorized numbers, as well as their corresponding names, and text responses
	authorizedNumbers = config.authorizedNumbers
	names = config.names
	
	textResponses = ["Garage is closed", 
	"Garage is Open. Would you like to close it? (Y/N)", 
	"""Please only send messages once every 10 seconds. If no immediate response, please wait 30 seconds. Thank you!

	Commands:
	Status - Ask if garage is opened or closed

	Close - Closes the garage

	Open - Opens the garage""",
	"Please enter a valid command. A list of commands is given by typing Help.", 
	"Ok garage closing now.", 
	"Garage will remain open",
	"J.A.R.V.I.S is now shutting down.",
	"Incorrect response. Would you like to close garage? (Y/N)",
	"Garage door is closed",
	"Garage door is already closed",
	"Garage door is already opened",
	"Ok garage opening now"]

	#Password to shutdown program
	__shutdownPassword = "Mouse Rat"

	def __init__ (self, usrName, pswd):
		global logger_googleVoice
		self.usrName = usrName
		self.pswd = pswd
		self.voice = Voice()
		self.numReceivedFrom = []
		self.messageReceived = []
		try:
			self.voice.login(self.usrName,self.pswd)
			logger_googleVoice.info("Successfully logged into Google Voice")
		except:
			logger_googleVoice.exception("Unable to login into Google Voice")
			exit(0)
		self.__markAsRead()
		self.__deleteMessages()
		self.__readyNotify()
		self.phoneToSend = ""
		print("Startup complete")

	def __readyNotify(self):
		"""readyMessage = "J.A.R.V.I.S ready to receive commands."
		for num in googleVoice.authorizedNumbers:
			self.__sendMessage(num,readyMessage)"""
		num = googleVoice.authorizedNumbers[1]
		person = googleVoice.names[num]

		readyMessage = "Hello " + person + ", J.A.R.V.I.S is ready to receive commands."
		self.__sendMessage(num,readyMessage)

	def __receiveSMS(self):
		global logger_googleVoice
		self.voice.sms()
		while True:
			self.numReceivedFrom = []
			self.messageReceived = []
			self.__extractSMS((self.voice.sms.html))
			if len(self.numReceivedFrom) > 0:
				break
			time.sleep(2)
		print("Got messages")
		if len(self.numReceivedFrom) != len(self.messageReceived):
			exit(1)
		recentMess = self.messageReceived[0]
		if self.__passwordCheck(recentMess):
			recentMess = "***************************"
		mess = "From " + self.numReceivedFrom[0] + ": " + recentMess
		logger_googleVoice.debug(mess)
		return

	def __extractSMS(self,htmlsms) :
	    """
	    extractsms  --  extract SMS messages from BeautifulSoup tree of Google Voice SMS HTML.
		"""
	    rawMessage = BeautifulSoup(htmlsms, "html.parser")			# parse HTML into tree

	    self.__markAsRead()

	    text = rawMessage.get_text() #remove HTML Tags
	    text = text.strip()			 #remove extra whitespace
	    newText = re.sub(r'[\r\n][\r\n]{2,}', '\n\n', text) #remove extra newlines 
	    giantList = newText.splitlines()		#put each line into a list
	    pos = 0
	    lenList = len(giantList)
	    while True:
	    	if pos >= lenList: #only run the loop for the length of the list
	    		break
	    	curr = giantList[pos]
	    	authorized, phoneNum = self.__isAuthorizedNumber(curr) #see if there is a text message from any of the authorized numbers
	    	if authorized:
	    		self.numReceivedFrom.append(phoneNum) #Keep track of who sent a message
	    		pos = pos + 2;
	    		cleanText = self.__cleanMessage(giantList[pos]) #The message received is two lines below the number
	    		self.messageReceived.append(cleanText)
	    		continue
	    	pos=pos+1

	def __isAuthorizedNumber(self,numberString):
		"""Checks the list entries above to see if they are the authorized numbers."""
		for i in range(0, len(googleVoice.authorizedNumbers)):
			num = googleVoice.authorizedNumbers[i]
			testString = num + ":"
			if testString in numberString:
				return True, num
		return False, -3

	def __cleanMessage(self,message):
		phone = ""
		stringLength = len(message)
		for i in range(0, stringLength):
			testChar = message[i]
			if testChar.isalnum():
				#print(testChar) For testing
				phone = phone + testChar
			elif testChar.isspace():
				if i == (stringLength-1):
					continue
				elif len(phone) == 0:
					continue
				else:
					phone = phone + testChar
			else:
				continue
		return phone

	def __markAsRead(self):
		for message in self.voice.sms().messages:
	   		message.mark(1)

	def __deleteMessages(self):
		listMess = self.voice.sms().messages
		for message in listMess:
			if message.isRead:
				message.delete()
		print("Finish deleting messages")
		logger_googleVoice.info("All messages deleted")

	def __sendMessage(self, phoneNum, txtmsg):
		global logger_googleVoice
		try:
			self.voice.send_sms(phoneNum,txtmsg)
			self.__deleteMessages()
			loggingMess = "Sent: " + txtmsg + " to " + phoneNum + "."
		except:
			loggingMess = "Error. Message not sent to " + phoneNum + "."
		logger_googleVoice.debug(loggingMess)


	def __interpretDefaultMessage(self,inputMessage):
		"""1 = continue conversation. 0 = end conversation """
		global door1
		message = inputMessage.lower()
		# Format : Response, continue conversation, close/open garage (0=no,1=close,2=open)
		if message == "status":
			if door1.status() == "closed":
				return googleVoice.textResponses[8],0, 0
			else:
				return googleVoice.textResponses[1], 1, 1
		elif message == "help":
			return googleVoice.textResponses[2], 0, 0
		elif message == "close":
			if door1.status() == "closed":
				return googleVoice.textResponses[9],0, 0
			else:
				return googleVoice.textResponses[4], 0, 1
		elif message == "open":
			if door1.status() == "opened":
				return googleVoice.textResponses[10], 0, 0
			else:
				return googleVoice.textResponses[11], 0, 2
		elif message == "vacation mode on":
			mess = vacationMode(True, self.phoneToSend)
			return mess, 0, 0
		elif message == "vacation mode off":
			mess = vacationMode(False, self.phoneToSend)
			return mess, 0, 0
		elif message == "shut down":
			mess, passfound = self.__shutDownProcess()
			if passfound == 2:
				self.__sendMessage(self.phoneToSend, mess)
				exit(3)
			return mess, 0, False
		else:
			return googleVoice.textResponses[3], 0, False

	def __interpretCloseGarageMessage(self, inputMessage):
		global door1
		message = inputMessage.lower()
		retMessage = ""
		closeGar = False
		while True:
			if message == "y":
				retMessage = googleVoice.textResponses[4]
				closeGar = True
				break
			elif message == "n":
				retMessage = googleVoice.textResponses[5]
				break
			else:
				self.__sendMessage(self.phoneToSend, googleVoice.textResponses[7])
				time.sleep(3)
				self.__receiveSMS()
				message = self.messageReceived[0].lower()
		return retMessage, closeGar


	def __passwordCheck(self, password):
		if password == googleVoice.__shutdownPassword:
			return True
		else:
			return False

	def __shutDownProcess(self):
		global logger_googleVoice
		print("Super Shut down")
		cnt = 0
		wrongPass = "Incorrect Password. Please try again."
		messToSend = ""
		foundPass = 0
		while True:
			if cnt == 0:
				print("Please Enter Password")
				print(self.phoneToSend)
				self.__sendMessage(self.phoneToSend, "Please enter password:")
				time.sleep(3)
				self.__receiveSMS()
			elif cnt == 3:
				messToSend = "Ay Tanga! Too many failed attempts. Exiting shutdown procedure. Resuming normal function."
				print(messToSend)
				logger_googleVoice.info("Shut down process failed. Too many failed password attempts.")
				break
			else:
				inCorrectTxt = wrongPass + " Attempt " + str(cnt) + " out of 3 attempts."
				self.__sendMessage(self.phoneToSend, inCorrectTxt)
				self.__receiveSMS()
			if self.__passwordCheck(self.messageReceived[0]):
				messToSend = "Password accepted" + ". " + googleVoice.textResponses[6]
				foundPass = 2
				logger_googleVoice.info("Shut down process completed. Correct password found.")
				break
			else:
				cnt = cnt + 1

			print(cnt)

		print(messToSend)
		return messToSend, foundPass		

	def unReadMessages(self):
		global logger_googleVoice
		try:
			numUnread = len(self.voice.sms().messages)
			return numUnread
		except:
			logger_googleVoice.exception("Failed to find unread messages")

	def sms(self,phonenum,message):
		self.__sendMessage(phonenum,message)

	def getCommands(self):
		global door1
		while True:
			defaultMessageState = 0
			self.__receiveSMS()
			if len(self.numReceivedFrom) != len(self.messageReceived):
				exit(1)
			self.phoneToSend = self.numReceivedFrom[0]
			txtmsg, contConvo, closeGarage = self.__interpretDefaultMessage(self.messageReceived[0])
			while True:
				if contConvo == 0:
					self.__sendMessage(self.phoneToSend,txtmsg)
					if closeGarage == 1:
						door1.closeDoor("close")
					elif closeGarage == 2:
						door1.closeDoor("open")
					break
				elif contConvo == 1:
					print(self.phoneToSend, " ", txtmsg)
					self.__sendMessage(self.phoneToSend,txtmsg)
					time.sleep(3)
					self.__receiveSMS()
					txtmsg, closeGarage = self.__interpretCloseGarageMessage(self.messageReceived[0])
					self.__sendMessage(self.phoneToSend, txtmsg)
					if closeGarage == True:
						door1.closeDoor()
					break
				elif contConvo == 2:
					self.__sendMessage(self.phoneToSend, txtmsg)
					print("Received shut down input ")
					exit(2)
			print("Done")
			break

"""###########################################################
	Garage Door Class
   ###########################################################"""

class garageDoor:
	def __init__(self, garageName):
		global garageSensorPins, garageRelayPins
		try:
			self.garageName = garageName
			self.sensorPin = garageSensorPins[self.garageName]
			self.relayPin = garageRelayPins[self.garageName]
			self.state = self.status() #change to get from sensor
			self.prevState = self.state
			self.timeStateChange = getCurrTime()
			logger_garageDoor.info("".join(["Successfully created garage door: ",self.garageName]))
		except:
			logger_garageDoor.exception("Unable to create Garage Door Class")

	def status(self):
		cnt = 0
		firstRead = GPIO.input(self.sensorPin)
		#Makes sure the reading is consistent to prevent false readings
		while True:
			if cnt == 3:
				if firstRead == True:
					state = "closed"
				else:
					state = "opened"
				break
			if GPIO.input(self.sensorPin) == firstRead:
				cnt = cnt + 1
				continue
			elif cnt > 0 and GPIO.input(self.sensorPin) != firstRead:
				cnt = 0
				firstRead = GPIO.input(self.sensorPin)
				continue
			time.sleep(0.5)
		return state

	def changeState(self, newState):
		self.prevState = self.state
		self.state = newState
		self.timeStateChange = str(getCurrTime())
		mess = self.garageName + " was " + self.state
		print(mess)
		logger_garageDoor.info(mess)
		return mess

	def closeDoor(self, closeOpen):
		global gv
		closeMess = "Opening"
		if closeOpen == "close":
			closeMess = "Closing"
		try:
			mess = closeMess + " " + self.garageName
			logger_garageDoor.info(mess)
			GPIO.output(self.relayPin, True)
			time.sleep(0.3)
			GPIO.output(self.relayPin, False)
			if closeOpen == "close":
				while True:
					closedState = self.status()
					if closedState == "closed":
						mess = self.changeState(closedState)
						gv.sms(gv.phoneToSend,mess)
						break
					time.sleep(1)
			else:
				time.sleep(2)
				closedState = self.status()
				mess = self.changeState(closedState)
				gv.sms(gv.phoneToSend,mess)
		except KeyboardInterrupt:
			messToSend = "Failed to " + closeOpen + " garage. Please try again."
			gv.sms(gv.phoneToSend, messToSend)
			errMess = "Unable to " + closeOpen + " garage door"
			logger_garageDoor.exception("Unable to close/open garage door")

	def monitorCloseOpen(self):
		global gv, vacationNumber
		inputSense = self.status()
		if inputSense != self.state:
			mess = self.changeState(inputSense) + " at " + str(getCurrTime())
			gv.sms(vacationNumber, mess)

			
"""###########################################################"""

gv = googleVoice(config.gVoiceUsrName, config.gVoicePswd)
door1 = garageDoor(config.door1Name)

while True:
	try:
		if vacationStat == True:
			door1.monitorCloseOpen()
		i = gv.unReadMessages()
		if i > 0:
			gv.getCommands()
			i = 0
		time.sleep(0.5)
	except KeyboardInterrupt:
		logger_base.critical("J.A.R.V.I.S stopped due to keyboard interrupt")
		GPIO.cleanup()
		exit(1)
