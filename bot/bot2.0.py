import telebot
from telebot import types

import sys
import os
import json
from flask import Flask, jsonify, request
import requests
from requests.exceptions import ConnectionError
import secrets

import time
import datetime

import psycopg2
from psycopg2 import Error
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

sys.path.append('../blindSignature')
from tools import *


bot = telebot.TeleBot('5282719860:AAHTNQczBJvgGJdHzk69ICJLsNnrUmiT8b8')

# Postgres stuff

# Connect to db
connection = psycopg2.connect(user="admin",
								  password="admin",
								  host="127.0.0.1",
								  port="5432",
								  database="botdata")

cursor = connection.cursor()


# Blockchain stuff

nodes = ["127.0.0.1:5002", "127.0.0.1:5003"]

def ping(node):
	try:
		answer = requests.get(f'http://{node}/nodes/ping')

		if (answer.status_code == 200):
			return True
	except ConnectionError:
		return False

def selectNode():
	global nodes
	while True:
		if (nodes == []):
			data = 'All nodes are unavailable!'
			bot.send_message(97781168, data)
			raise RuntimeError('All nodes are unavailable!')

		node = secrets.choice(nodes)

		if (ping(node)):
			return node
		else:
			nodes.remove(node)
			data = 'Node ' + node + ' is unavailable!'
			bot.send_message(97781168, data)



def addData(node, data):
	headers = {'Content-Type': 'application/json'}

	json_data = {'data': data}
	answer = requests.post(f'http://{node}/currentBlockData/new', json=json_data)

	if (answer.status_code == 201):
		print(answer.json()['message'])
		print(answer.json()['mempoolMessage'])

		return answer.json()['mempoolLoadBool']

	else:
		print('Something went wrong.')
		return False


def getChain(node):
	answer = requests.get(f'http://{node}/chain')

	if (answer.status_code == 200):
		print(answer.json()['chain'])
		return answer.json()['chain']

for i in range(len(nodes)):
	for j in range(len(nodes)):
		if (i != j):
			json_data = {'nodes': [f'http://{nodes[j]}']}
			response = requests.post(f'http://{nodes[i]}/nodes/register', json=json_data)


validatorAddress = "127.0.0.1:5010"
answer = requests.get(f'http://{validatorAddress}/getPublicKey')
if (answer.status_code == 200):
	publicKey = tuple(answer.json()['publicKey'])
else:
	raise RuntimeError('Something went wrong while getting validator`s public key')


explorerAddress = "127.0.0.1:5020"

# Blockchain stuff 


currentCreatingPollID = 0
creatingPollPositionsNumber = 6

creatingVotePositionsNumber = 5

monthIntToStr = {1 : 'Jan', 2 : 'Feb', 3 : 'Mar', 4 : 'Apr', 5 : 'May', 6 : 'Jun', 7 : 'Jul', 8 : 'Aug', 9 : 'Sep', 10 : 'Oct', 11 : 'Nov', 12 : 'Dec'}
monthStrToInt = {'Jan' : '01', 'Feb' : '02', 'Mar' : '03', 'Apr' : '04', 'May' : '05', 'Jun' : '06', 'Jul' : '07', 'Aug' : '08', 'Sep' : '09', 'Oct' : '10', 'Nov' : '11', 'Dec' : '12'}


def findActivePollsForUser(user):
	pollsForUser = []

	cursor.execute("SELECT * from activeVoters where id = %s", (user, ))
	
	if (cursor.rowcount > 0):
		cursor.execute("SELECT ID, THEME from activePolls where %s = ANY(VOTERS)", (user, ))
		dataFromDB = cursor.fetchall()

		for i in dataFromDB:
			pollsForUser.append(list(i))
	
	return pollsForUser


def updateActiveLists(poll, user):

	cursor.execute("SELECT * from activePolls where id = %s", (str(poll), ))
	dataFromDB = cursor.fetchall()[0]
	pollIDFromDB = dataFromDB[0]
	votersFromDB = dataFromDB[3]

	votersFromDB.remove(user)
	cursor.execute("UPDATE activePolls SET VOTERS = %s WHERE id = %s", (votersFromDB, str(poll)))
	connection.commit()

	if (votersFromDB == []):
		node = selectNode()
		isItTimeToMine = addData(node, [f'Poll {pollIDFromDB} is finished'])
		if (isItTimeToMine):
			for i in nodes:
				backupChain(i)

		cursor.execute("DELETE from activePolls where id = %s", (str(poll), ))
		connection.commit()

	cursor.execute("SELECT * from activePolls where %s = ANY(VOTERS)", (user, ))

	if (cursor.rowcount == 0):
		cursor.execute("DELETE from activeVoters where id = %s", (user, ))
		connection.commit()


def pollTimeEnded(poll, isRecreating):
	cursor.execute("SELECT * from activePolls where id = %s", (str(poll), ))
	dataFromDB = cursor.fetchall()[0]
	pollIDFromDB = dataFromDB[0]
	votersFromDB = dataFromDB[3]

	for user in votersFromDB:
		votersFromDB.remove(user)
		cursor.execute("UPDATE activePolls SET VOTERS = %s WHERE id = %s", (votersFromDB, str(poll)))
		connection.commit()

		cursor.execute("SELECT * from activePolls where %s = ANY(VOTERS)", (user, ))

		if (cursor.rowcount == 0):
			cursor.execute("DELETE from activeVoters where id = %s", (user, ))
			connection.commit()

	if (isRecreating == False):
		node = selectNode()
		isItTimeToMine = addData(node, [f'Poll {pollIDFromDB} is finished'])
		if (isItTimeToMine):
			for i in nodes:
				backupChain(i)

	cursor.execute("DELETE from activePolls where id = %s", (str(poll), ))
	connection.commit()


def recreateDatabasesFromChain():
	cursor.execute("DELETE from activePolls")
	connection.commit()
	cursor.execute("DELETE from activeVoters")
	connection.commit()

	node = selectNode()
	chain = getChain(node)
	blocksNumber = len(chain)

	print('Started recreating databases from chain')

	for block in range(blocksNumber):
		blockData = chain[block]['data']
		print(f'In block {block}')

		for i in range(len(blockData)):
			if (len(blockData[i]) == 1 and type(blockData[i]) == list):						# [f'Poll {activePolls[i][0]} is finished']
				print('Found poll ending')
				pollTimeEnded(int(blockData[i][0].split()[1]), True)

			elif (len(blockData[i]) == 6 and type(blockData[i]) == list):						# ['poll', index, theme, answers, voters, finishTime]
				print('Found poll')																# '18/03/2022 09:31:19'
				
				cursor.execute("INSERT INTO activePolls VALUES (%s, %s, %s, %s, %s)", (str(blockData[i][1]), blockData[i][2], blockData[i][3], blockData[i][4], blockData[i][5]))
				connection.commit()

				voters = blockData[i][4]

				for i in voters:
					cursor.execute("SELECT * FROM activeVoters WHERE id = %s", (i, ))
					if (cursor.fetchall() == []):
						cursor.execute("INSERT INTO activeVoters (ID) VALUES (%s)", (i, ))
						connection.commit()

	print('Finished recreating databases from chain')


def backupChain(node):
	chain = str(getChain(node))

	hashFromData = sha256(chain.encode('utf-8')).hexdigest()
	intFromHash = int(hashFromData, 16)
	blindedData, blindingFactor = blindData(intFromHash, publicKey)


	json_data = {'data': blindedData}
	answer = requests.post(f'http://{validatorAddress}/signData', json=json_data)
	if (answer.status_code == 201):
		signedBlindedData = answer.json()['signedData']
	else:
		raise RuntimeError('Something went wrong while getting validator`s sign')


	signature = unblindData(signedBlindedData, blindingFactor, publicKey)

	backupFile = open(f'backups/chain{node}.txt', 'w')
	backupFile.write(chain + '\n' + str(signature) + '\n' + str(publicKey))
	backupFile.close()


if ('--cleanDB' in sys.argv):
	cursor.execute("DELETE from activePolls")
	connection.commit()
	cursor.execute("DELETE from creatingPoll")
	connection.commit()
	cursor.execute("DELETE from activeVoters")
	connection.commit()
	cursor.execute("DELETE from personalVariables")
	connection.commit()


if ('--backupChain' in sys.argv):
	tmp = open('backups/validatorPublicKeyFromLastSession.txt', 'r')
	validatorPublicKeyFromLastSession = tmp.read().split(', ')
	validatorPublicKeyFromLastSession = (int(validatorPublicKeyFromLastSession[0][1:]), int(validatorPublicKeyFromLastSession[1][:len(validatorPublicKeyFromLastSession[1]) - 1]))
	tmp.close()

tmp = open('backups/validatorPublicKeyFromLastSession.txt', 'w')
tmp.write(str(publicKey))
tmp.close()


if ('--backupChain' in sys.argv):

	allBackupsSuccessful = True
	publicKeyFromLastSession = ''

	backupChains = os.listdir('backups/')

	localNodes = nodes.copy()

	firstChainLength = -1

	firstMempoolLoad = -1
	allMempoolsHaveTheSameLength = True

	for file in backupChains:
		if (file[5:len(file) - 4] in localNodes):
			localNodes.remove(file[5:len(file) - 4])
			tmp = open(f'backups/{file}')
			data = tmp.read()

			dataList = data.split('\n')

			chainLength = len(dataList[0])

			if (firstChainLength == -1):
				firstChainLength = chainLength
			elif (chainLength != firstChainLength):
				allBackupsSuccessful = False

			publicKeyFromLastSession = dataList[2].split(', ')
			publicKeyFromLastSession = (int(publicKeyFromLastSession[0][1:]), int(publicKeyFromLastSession[1][:len(publicKeyFromLastSession[1]) - 1]))
			if (publicKeyFromLastSession != validatorPublicKeyFromLastSession):
				raise RuntimeError('Public keys in backups are different! It can appear when backups are made during different sessions!')

			tmp.close()

			json_data = {'data': data}
			response = requests.post(f'http://{file[5:len(file) - 4]}/backupChainFromFile', json=json_data)
			if (response.status_code == 201):
				if (response.json()['message'] == 'Chain signature is invalid'):
					allBackupsSuccessful = False
				else:
					if (firstMempoolLoad == -1):
						firstMempoolLoad = response.json()['mempoolLoad']
					elif (firstMempoolLoad != response.json()['mempoolLoad']):
						allMempoolsHaveTheSameLength = False

				print(response.json()['message'] + ' Node ' + file[5:len(file) - 4])

	if (localNodes != []):
		allBackupsSuccessful = False

	if (allBackupsSuccessful == False):
		print('Not all nodes have had backups or chains had diffent length so consensus algorithm was initiated')
		for node in nodes:
			answer = requests.get(f'http://{node}/nodes/consensus')

			if (answer.status_code == 200):
				print(answer.json()['message'] + ' Node ' + node)

	json_data = {'publicKey': publicKeyFromLastSession}
	answer = requests.post(f'http://{explorerAddress}/getResultsFromLastSession', json=json_data)

	biggestPollNumberFromChain = answer.json()['biggestPollNumber']

	currentCreatingPollID = biggestPollNumberFromChain + 1

	node = selectNode()
	chain = getChain(node)
	lastBlockTime = float(chain[len(chain) - 1]['time'])

	cursor.execute("SELECT ID from personalVariables")
	users = cursor.fetchall()

	for user in users:
		bot.send_message(user[0], f'Error had occured and nodes were backuped. In this case, votes and polls, added after {datetime.datetime.fromtimestamp(lastBlockTime).strftime("%A, %B %d, %Y %H:%M:%S")}, could be lost.\nEnter /start to restart the bot!')

	if (allMempoolsHaveTheSameLength == False):
		for node in nodes:
			answer = requests.get(f'http://{node}/nodes/cleanMempool')

	if (allBackupsSuccessful and allMempoolsHaveTheSameLength and firstMempoolLoad != 0):
		pass
	else:
		recreateDatabasesFromChain()


@bot.message_handler(commands=['start'])
def send_welcome(message):
	keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
	button = types.KeyboardButton("Start!")


	cursor.execute("SELECT * from personalVariables where id = %s", (str(message.chat.id), ))
	if (cursor.fetchall() == []):
		cursor.execute("INSERT INTO personalVariables (ID) VALUES (%s)", (str(message.chat.id), ))
		connection.commit()
		cursor.execute("INSERT INTO creatingPoll (ID) VALUES (%s)", (str(message.chat.id), ))
		connection.commit()
	else:
		cursor.execute("DELETE from personalVariables where id = (%s)", (str(message.chat.id), ))
		connection.commit()
		cursor.execute("DELETE from creatingPoll where id = (%s)", (str(message.chat.id), ))
		connection.commit()
		cursor.execute("INSERT INTO personalVariables (ID) VALUES (%s)", (str(message.chat.id), ))
		connection.commit()
		cursor.execute("INSERT INTO creatingPoll (ID) VALUES (%s)", (str(message.chat.id), ))
		connection.commit()

	keyboard.add(button)
	msg = bot.send_message(message.chat.id, 'Welcome to Secure Voting Bot! To start decentralized voting platform, press the button below!', reply_markup = keyboard)
	bot.register_next_step_handler(msg, get_startAnswer)


#@bot.message_handler(commands=['text'])
def get_startAnswer(message):
	if (message.text == "Start!"):
		keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
		#keyboard.add("Dev just push to blockchain", "Create poll", "Find polls waiting for my vote", "Explore poll", "Error")
		keyboard.add("Create poll", "Find polls waiting for my vote", "Explore poll", "Error")
		msg = bot.send_message(message.from_user.id, "Choose your action!", reply_markup = keyboard)
		bot.register_next_step_handler(msg, handle_action)


@bot.message_handler(commands=['text'])
def handle_action(message):

	"""
	if (message.text == "Dev just push to blockchain"):
		node = selectNode()
		isItTimeToMine = addData(node, "a")
		if (isItTimeToMine):
			for i in nodes:
				backupChain(i)
		msg = bot.send_message(message.from_user.id, "Select action")
		bot.register_next_step_handler(msg, handle_action)
	"""
	if (message.text == "Create poll"):
		msg = bot.send_message(message.from_user.id, "What is the theme of the poll?")
		bot.register_next_step_handler(msg, handle_theme)

	elif (message.text == "Find polls waiting for my vote"):

		pollsForUser = findActivePollsForUser(message.from_user.username)
		if (pollsForUser != []):
			# Explored polls for user, if not [] - need to print message and vote. Else print message to go away or wait for block to mine.

			keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
			pollsString = ''

			for i in pollsForUser:
				pollsString += f'{i[0]} : {i[1]}\n'
				keyboard.add(str(i[0]))

			msg = bot.send_message(message.from_user.id, "There are some polls waiting for your vote:\n" + pollsString + "Choose the poll to vote!", reply_markup = keyboard)
			bot.register_next_step_handler(msg, handle_poll)
		else:
			msg = bot.send_message(message.from_user.id, "There are no polls waiting for your vote! Try again later, some polls can be in mempool now.")
			bot.register_next_step_handler(msg, handle_action)
	
	elif (message.text == "Explore poll"):
		msg = bot.send_message(message.from_user.id, "Enter poll id")
		bot.register_next_step_handler(msg, handle_pollExploration)

	elif (message.text == "Error"):
		msg = bot.send_message(message.from_user.id, "What is the error?")
		bot.register_next_step_handler(msg, handle_errorReason)

	else:
		keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
		#keyboard.add("Dev just push to blockchain", "Create poll", "Find polls waiting for my vote", "Explore poll", "Error")
		keyboard.add("Create poll", "Find polls waiting for my vote", "Explore poll", "Error")
		msg = bot.send_message(message.from_user.id, "Not a command! Try again.", reply_markup = keyboard)
		bot.register_next_step_handler(msg, handle_action)


#@bot.message_handler(commands=['text'])
def handle_theme(message):
	theme = message.text

	global currentCreatingPollID

	cursor.execute("UPDATE creatingPoll SET POLLID = %s WHERE id = %s", (currentCreatingPollID, str(message.from_user.id)))
	connection.commit()

	currentCreatingPollID += 1

	cursor.execute("UPDATE creatingPoll SET THEME = %s WHERE id = %s", (theme, str(message.from_user.id)))
	connection.commit()

	msg = bot.send_message(message.from_user.id, "What is the answer variety?\nEnter the list in format answer1, answer2, ...")
	bot.register_next_step_handler(msg, handle_answerVariety)


#@bot.message_handler(commands=['text'])
def handle_answerVariety(message):
	answerVariety = message.text
	answerVariety = answerVariety.split(',')

	for i in range(len(answerVariety)):
		answerVariety[i] = answerVariety[i].strip()

	answerVariety = set(answerVariety)

	cursor.execute("UPDATE creatingPoll SET ANSWERVARIETY = %s WHERE id = %s", (list(answerVariety), str(message.from_user.id)))
	connection.commit()

	msg = bot.send_message(message.from_user.id, "Who will paticipate in this poll?\nEnter the list in format user1, user2, ...")
	bot.register_next_step_handler(msg, handle_voters)


#@bot.message_handler(commands=['text'])
def handle_voters(message):
	voters = message.text
	voters = voters.split(',')

	for i in range(len(voters)):
		voters[i] = voters[i].strip()
		if ('@' in voters[i]):
			voters[i] = voters[i][1:]

	voters = set(voters)
	
	cursor.execute("UPDATE creatingPoll SET VOTERS = %s WHERE id = %s", (list(voters), str(message.from_user.id)))
	connection.commit()

	for i in voters:
		cursor.execute("SELECT * FROM activeVoters WHERE id = %s", (i, ))
		if (cursor.fetchall() == []):
			cursor.execute("INSERT INTO activeVoters (ID) VALUES (%s)", (i, ))
			connection.commit()


	keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
	keyboard.add("Finish time", "All participants voted")
	
	msg = bot.send_message(message.from_user.id, "Choose the way of poll end", reply_markup = keyboard)
	bot.register_next_step_handler(msg, handle_pollFinishWay)

#@bot.message_handler(commands=['text'])
def handle_pollFinishWay(message):
	#time or amount
	way = message.text

	if (way == "Finish time"):
		msg = bot.send_message(message.from_user.id, "Enter finish time in format 'dd/mm/yyyy hh:mm:ss'.")
		bot.register_next_step_handler(msg, handle_pollFinishTime)
	
	elif (way == "All participants voted"):
		finishTime = 'All participants voted'

		cursor.execute("UPDATE creatingPoll SET FINISH = %s WHERE id = %s", (finishTime, str(message.from_user.id)))
		connection.commit()

		cursor.execute("SELECT * from creatingPoll where id = %s", (str(message.from_user.id), ))

		dataFromDB = cursor.fetchall()[0]

		creatingPollFromDB = ['poll', int(dataFromDB[1]), dataFromDB[2], dataFromDB[3], dataFromDB[4], dataFromDB[5]]

		node = selectNode()
		isItTimeToMine = addData(node, creatingPollFromDB)
		if (isItTimeToMine):
			for i in nodes:
				backupChain(i)

		cursor.execute("INSERT INTO activePolls VALUES (%s, %s, %s, %s, %s)", (dataFromDB[1], dataFromDB[2], dataFromDB[3], dataFromDB[4], dataFromDB[5]))
		connection.commit()

		cursor.execute("DELETE from creatingPoll where id = %s", (str(message.from_user.id), ))
		connection.commit()
		cursor.execute("INSERT INTO creatingPoll (ID) VALUES (%s)", (str(message.chat.id), ))
		connection.commit()

		keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
		#keyboard.add("Dev just push to blockchain", "Create poll", "Find polls waiting for my vote", "Explore poll", "Error")
		keyboard.add("Create poll", "Find polls waiting for my vote", "Explore poll", "Error")
		msg = bot.send_message(message.from_user.id, "Your poll has been created. Thank you!", reply_markup = keyboard)
		bot.register_next_step_handler(msg, handle_action)

	else:
		msg = bot.send_message(message.from_user.id, "Your poll finish way is invalid! Try again.")
		bot.register_next_step_handler(msg, handle_pollFinishWay)


#@bot.message_handler(commands=['text'])
def handle_pollFinishTime(message):
	finishTime = message.text 							# format incoming '18/03/2022 09:31:19'

	isTimeCorrect = True

	t = finishTime.split()
	if (len(t) != 2):
		isTimeCorrect = False

	else:
		tParts = t[0].split('/')
		if (len(tParts) != 3):
			isTimeCorrect = False
		tParts.extend(t[1].split(':'))

		if (len(tParts) != 6 or len(tParts[0]) != 2 or len(tParts[1]) != 2 or len(tParts[2]) != 4 or len(tParts[3]) != 2 or len(tParts[4]) != 2 or len(tParts[5]) != 2 or int(tParts[3]) < 0 or int(tParts[3]) > 23 or int(tParts[4]) < 0 or int(tParts[4]) > 59 or int(tParts[5]) < 0 or int(tParts[5]) > 59 or t[1] == '00:00:00'):
			isTimeCorrect = False

	try:
		datetime.datetime.strptime(t[0],"%d/%m/%Y")
	except ValueError:
		isTimeCorrect = False

	if (isTimeCorrect):
		cursor.execute("UPDATE creatingPoll SET FINISH = %s WHERE id = %s", (finishTime, str(message.from_user.id)))
		connection.commit()

		cursor.execute("SELECT * from creatingPoll where id = %s", (str(message.from_user.id), ))

		dataFromDB = cursor.fetchall()[0]

		creatingPollFromDB = ['poll', int(dataFromDB[1]), dataFromDB[2], dataFromDB[3], dataFromDB[4], dataFromDB[5]]

		node = selectNode()
		isItTimeToMine = addData(node, creatingPollFromDB)
		if (isItTimeToMine):
			for i in nodes:
				backupChain(i)

		cursor.execute("INSERT INTO activePolls VALUES (%s, %s, %s, %s, %s)", (dataFromDB[1], dataFromDB[2], dataFromDB[3], dataFromDB[4], dataFromDB[5]))
		connection.commit()

		cursor.execute("DELETE from creatingPoll where id = %s", (str(message.from_user.id), ))
		connection.commit()
		cursor.execute("INSERT INTO creatingPoll (ID) VALUES (%s)", (str(message.chat.id), ))
		connection.commit()

		keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
		#keyboard.add("Dev just push to blockchain", "Create poll", "Find polls waiting for my vote", "Explore poll", "Error")
		keyboard.add("Create poll", "Find polls waiting for my vote", "Explore poll", "Error")
		msg = bot.send_message(message.from_user.id, "Your poll has been created. Thank you!", reply_markup = keyboard)
		bot.register_next_step_handler(msg, handle_action)
	
	else:
		msg = bot.send_message(message.from_user.id, "Time format is invalid! Try again.")
		bot.register_next_step_handler(msg, handle_pollFinishTime)


#@bot.message_handler(commands=['text'])
def handle_poll(message):
	data = message.text

	# Here we need to check if poll active voters list contains user and then update creating vote list
	
	cursor.execute("SELECT * FROM activePolls WHERE id = %s AND %s = ANY (VOTERS)", (data, str(message.from_user.username)))
	if (cursor.rowcount > 0):
		dataFromDB = cursor.fetchall()[0]

		cursor.execute("UPDATE personalVariables SET CREATINGVOTE = %s WHERE id = %s", ([data], str(message.from_user.id)))
		connection.commit()

		cursor.execute("UPDATE personalVariables SET CREATINGVOTEANSWERVARIETY = %s WHERE id = %s", (dataFromDB[2], str(message.from_user.id)))
		connection.commit()

		cursor.execute("UPDATE personalVariables SET CREATINGVOTEFINISHTIME = %s WHERE id = %s", (dataFromDB[4], str(message.from_user.id)))
		connection.commit()

		keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)

		for i in dataFromDB[2]:
			keyboard.add(i)

		msg = bot.send_message(message.from_user.id, "Enter your vote", reply_markup = keyboard)
		bot.register_next_step_handler(msg, handle_voting)
	else:
		msg = bot.send_message(message.from_user.id, "You entered invalid poll id. Either you aren't a participant of this poll, or this poll doesn't exist")
		bot.register_next_step_handler(msg, handle_poll)

def timeDataToSeconds(t):
	t = t.split()
	dateToSeconds = time.mktime(datetime.datetime.strptime(t[0],"%d/%m/%Y").timetuple())
	tmp = time.strptime(t[1],'%H:%M:%S')
	timeToSeconds = datetime.timedelta(hours = tmp.tm_hour, minutes = tmp.tm_min, seconds = tmp.tm_sec).total_seconds()

	totalTime = dateToSeconds + timeToSeconds

	return totalTime


#@bot.message_handler(content_types=["text"])
def handle_voting(message):
	data = message.text

	currentTime = time.ctime(time.time()) # 'Fri Mar 18 09:31:19 2022'
	currentTime = currentTime.split()
	if (int(currentTime[2]) >= 1 and int(currentTime[2]) <= 9):
		currentTime[2] = '0' + currentTime[2]

	timeOfVote = currentTime[2] + '/' + monthStrToInt[currentTime[1]] + '/' + currentTime[4] + ' ' + currentTime[3] #'18/03/2022 11:20:32'

	voteTotalTime = timeDataToSeconds(timeOfVote)

	cursor.execute("SELECT * from personalVariables where id = %s", (str(message.from_user.id), ))
	dataFromDB = cursor.fetchall()[0]

	creatingVoteAnswerVarietyFromDB = dataFromDB[2]
	creatingVoteFinishTimeFromDB = dataFromDB[3]

	if (creatingVoteFinishTimeFromDB != "All participants voted"):
		creatingVoteFinishTotalTime = timeDataToSeconds(creatingVoteFinishTimeFromDB)

	if (data in creatingVoteAnswerVarietyFromDB):

		if (creatingVoteFinishTimeFromDB == "All participants voted" or voteTotalTime <= creatingVoteFinishTotalTime):

			hashFromData = sha256(data.encode('utf-8')).hexdigest()
			intFromHash = int(hashFromData, 16)
			print('Hash is:', hashFromData)
			blindedData, blindingFactor = blindData(intFromHash, publicKey)


			json_data = {'data': blindedData}
			answer = requests.post(f'http://{validatorAddress}/signData', json=json_data)
			if (answer.status_code == 201):
				signedBlindedData = answer.json()['signedData']
			else:
				raise RuntimeError('Something went wrong while getting validator`s sign')


			signature = unblindData(signedBlindedData, blindingFactor, publicKey)

			cursor.execute("UPDATE personalVariables SET CREATINGVOTE = CREATINGVOTE || %s WHERE id = %s", ([data, str(signature), timeOfVote], str(message.from_user.id)))
			connection.commit()

			cursor.execute("SELECT CREATINGVOTE from personalVariables where id = %s", (str(message.from_user.id), ))

			dataFromDB1 = cursor.fetchall()[0][0]

			creatingVoteFromDB = ['vote', int(dataFromDB1[0]), dataFromDB1[1], int(dataFromDB1[2]), dataFromDB1[3]]

			node = selectNode()
			isItTimeToMine = addData(node, creatingVoteFromDB)
			if (isItTimeToMine):
				for i in nodes:
					backupChain(i)

			updateActiveLists(creatingVoteFromDB[1], message.from_user.username)
			
			cursor.execute("UPDATE personalVariables SET CREATINGVOTE = NULL where id = %s", (str(message.from_user.id), ))
			connection.commit()
			cursor.execute("UPDATE personalVariables SET CREATINGVOTEANSWERVARIETY = NULL where id = %s", (str(message.from_user.id), ))
			connection.commit()
			cursor.execute("UPDATE personalVariables SET CREATINGVOTEFINISHTIME = NULL where id = %s", (str(message.from_user.id), ))
			connection.commit()

			keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
			#keyboard.add("Dev just push to blockchain", "Create poll", "Find polls waiting for my vote", "Explore poll", "Error")
			keyboard.add("Create poll", "Find polls waiting for my vote", "Explore poll", "Error")
			msg = bot.send_message(message.from_user.id, "Your vote has been saved. Thank you!\nPlease, delete the chat with the bot to keep your vote secure!", reply_markup = keyboard)
			bot.register_next_step_handler(msg, handle_action)

		else:
			cursor.execute("SELECT CREATINGVOTE from personalVariables where id = %s", (str(message.from_user.id), ))
			dataFromDB1 = cursor.fetchall()[0][0]
			poll = dataFromDB1[0]

			pollTimeEnded(poll, False)
			cursor.execute("UPDATE personalVariables SET CREATINGVOTE = NULL where id = %s", (str(message.from_user.id), ))
			connection.commit()
			cursor.execute("UPDATE personalVariables SET CREATINGVOTEANSWERVARIETY = NULL where id = %s", (str(message.from_user.id), ))
			connection.commit()
			cursor.execute("UPDATE personalVariables SET CREATINGVOTEFINISHTIME = NULL where id = %s", (str(message.from_user.id), ))
			connection.commit()

			keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
			#keyboard.add("Dev just push to blockchain", "Create poll", "Find polls waiting for my vote", "Explore poll", "Error")
			keyboard.add("Create poll", "Find polls waiting for my vote", "Explore poll", "Error")
			msg = bot.send_message(message.from_user.id, "Your vote is late, poll has already ended.", reply_markup = keyboard)
			bot.register_next_step_handler(msg, handle_action)

	else:
		msg = bot.send_message(message.from_user.id, "Your vote is invalid! Try again.")
		bot.register_next_step_handler(msg, handle_voting)


#@bot.message_handler(content_types=['text'])
def handle_pollExploration(message):
	data = message.text

	json_data = {'poll': data}
	answer = requests.post(f'http://{explorerAddress}/getResultsOfThePoll', json=json_data)

	if (answer.status_code == 201):
		results = answer.json()['results']

		resultsInProcents = {}
		resultsSum = 0
		for i in results:
			resultsSum += results[i]

		noVotes = False

		if (resultsSum == 0):
			noVotes = True
			resultsSum = 1

		resultsString = answer.json()['message'] + '\nThe results of the poll:\n'
		for i in results:					# {ans1 : amount1, ans2 : amount2, ...}
			resultsString += f'{i} : {results[i]} : {round(results[i] / resultsSum * 100, 2)}%\n'

		winner = '"' + max(results, key = results.get) + '"'

		for i in results:
			if (results[i] == max(results.values()) and i != max(results, key = results.get)):
				winner += ', "' + i + '"'

		if (noVotes != True):
			resultsString += f'The highest number of votes belongs to {winner}.'
		else:
			resultsString += f'Nobody has voted'

		keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
		#keyboard.add("Dev just push to blockchain", "Create poll", "Find polls waiting for my vote", "Explore poll", "Error")
		keyboard.add("Create poll", "Find polls waiting for my vote", "Explore poll", "Error")
		
		msg = bot.send_message(message.from_user.id, resultsString, reply_markup = keyboard)
		bot.register_next_step_handler(msg, handle_action)

	elif (answer.status_code == 202):
		msg = bot.send_message(message.from_user.id, answer.json()['message'] + '! Try again!')
		bot.register_next_step_handler(msg, handle_pollExploration)

	else:
		raise RuntimeError('Something went wrong while getting results of the poll')



#@bot.message_handler(commands=['text'])
def handle_errorReason(message):
	data = 'Error report from user @' + message.from_user.username + ':\n' + message.text

	bot.send_message(97781168, data)

	keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
	#keyboard.add("Dev just push to blockchain", "Create poll", "Find polls waiting for my vote", "Explore poll", "Error")
	keyboard.add("Create poll", "Find polls waiting for my vote", "Explore poll", "Error")

	msg = bot.send_message(message.from_user.id, 'Select action', reply_markup = keyboard)
	bot.register_next_step_handler(msg, handle_action)


bot.polling(none_stop=True, interval=0)

