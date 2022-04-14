from flask import Flask, jsonify, request
import requests
import secrets
import sys
sys.path.append('../blindSignature')
from tools import *


def getChain(node):
	answer = requests.get(f'http://{node}/chain')

	if (answer.status_code == 200):
		return answer.json()['chain']


nodes = ["127.0.0.1:5002", "127.0.0.1:5003"]
validatorAddress = "127.0.0.1:5010"
answer = requests.get(f'http://{validatorAddress}/getPublicKey')
if (answer.status_code == 200):
	publicKey = tuple(answer.json()['publicKey'])
else:
	raise RuntimeError('Something went wrong while getting validator`s public key')

try:
	tmp = open('validatorPublicKeyFromLastSession.txt', 'r')
	validatorPublicKeyFromLastSession = tmp.read().split(', ')
	validatorPublicKeyFromLastSession = (int(validatorPublicKeyFromLastSession[0][1:]), int(validatorPublicKeyFromLastSession[1][:len(validatorPublicKeyFromLastSession[1]) - 1]))
	tmp.close()
except FileNotFoundError:
	validatorPublicKeyFromLastSession = (10, 1)

tmp = open('validatorPublicKeyFromLastSession.txt', 'w')
tmp.write(str(publicKey))
tmp.close()



pollResults = {}									# format {poll : {ans1 : amount1, ans2 : amount2, ...}, ...}
finishedPolls = set()
countedBlocksAmount = 0


app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

def verifySignatureInnerFunction(data, signature, publicKey):
	hashFromData = sha256(data.encode()).hexdigest()
	dataUnderSignature = showSignedUnblindedData(signature, publicKey).zfill(64)

	return hashFromData, dataUnderSignature

@app.route('/verifySignature', methods=['POST'])
def verifySignature():
	values = request.get_json(force=True, silent=True, cache=False)
	required = ['data', 'signature', 'publicKey']

	if not all(i in values for i in required):
		return "Some data is missing", 400

	data = values['data']
	signature = values['signature']
	publicKey_ = tuple(values['publicKey'])

	hashFromData, dataUnderSignature = verifySignatureInnerFunction(data, signature, publicKey_)
	print(hashFromData)
	print(dataUnderSignature)

	if (hashFromData == dataUnderSignature and (publicKey_ == validatorPublicKeyFromLastSession or publicKey_ == publicKey)):
		answer = {'message' : 'Data is valid'}
		return jsonify(answer), 201
	else:
		answer = {'message' : 'Data is invalid'}
		return jsonify(answer), 201


@app.route('/getResultsFromLastSession', methods=['POST'])
def getResultsFromLastSession():
	values = request.get_json(force=True, silent=True, cache=False)
	required = ['publicKey']
	if not all(i in values for i in required):
		return "Some data is missing", 400

	publicKeyFromLastSession = tuple(values['publicKey'])

	if (publicKeyFromLastSession != validatorPublicKeyFromLastSession and publicKeyFromLastSession != publicKey):
		answer = {'message' : 'Key from last session is invalid'}
		return jsonify(answer), 400

	chain = getChain(secrets.choice(nodes))
	blocksNumber = len(chain)

	global pollResults
	global countedBlocksAmount
	global finishedPolls

	pollResults = {}
	finishedPolls = set()
	countedBlocksAmount = 0

	biggestPollNumber = -1

	print('Exploring data from backuped chain')

	for block in range(blocksNumber):
		blockData = chain[block]['data']
		print(f'In block {block}')

		for i in range(len(blockData)):
			if (len(blockData[i]) == 1 and type(blockData[i]) == list):						# [f'Poll {activePolls[i][0]} is finished']
				print('Found poll ending')
				finishedPolls.add(int(blockData[i][0].split()[1]))
			
			elif (len(blockData[i]) == 5 and type(blockData[i]) == list):						# ['vote', poll, vote, signature, time]
				print('Found vote')

				if (blockData[i][1] not in finishedPolls):
					data = blockData[i][2]
					signature = blockData[i][3]

					hashFromData, dataUnderSignature = verifySignatureInnerFunction(data, signature, publicKeyFromLastSession)
					
					if (hashFromData == dataUnderSignature):
						pollResults[blockData[i][1]][data] += 1

			elif (len(blockData[i]) == 6 and type(blockData[i]) == list):						# ['poll', index, theme, answers, voters, finishTime]
				print('Found poll')																# '18/03/2022 09:31:19'

				index = blockData[i][1]

				if (index > biggestPollNumber):
					biggestPollNumber = index

				answers = {}
				for j in range(len(blockData[i][3])):
					answers.update({blockData[i][3][j] : 0})

				pollResults.update({index : answers})

	countedBlocksAmount = blocksNumber - 1


	answer = {'message' : 'Exploring data from backuped chain finished', 'biggestPollNumber' : biggestPollNumber}
	return jsonify(answer), 201




@app.route('/getResultsOfThePoll', methods=['POST'])
def getResultsOfThePoll():
	values = request.get_json(force=True, silent=True, cache=False)
	required = ['poll']
	if not all(i in values for i in required):
		return "Some data is missing", 400

	poll = values['poll']

	chain = getChain(secrets.choice(nodes))
	blocksNumber = len(chain)

	global pollResults
	global countedBlocksAmount
	global finishedPolls

	thisBlockIsTheLast = False

	for block in range(countedBlocksAmount + 1, blocksNumber):
		blockData = chain[block]['data']
		print(f'In block {block}')

		for i in range(len(blockData)):
			if (len(blockData[i]) == 1 and type(blockData[i]) == list):						# [f'Poll {activePolls[i][0]} is finished']
				print('Found poll ending')
				finishedPolls.add(int(blockData[i][0].split()[1]))
				if (blockData[i][0].split()[1] == poll):
					thisBlockIsTheLast = True
					countedBlocksAmount = block
			
			elif (len(blockData[i]) == 5 and type(blockData[i]) == list):						# ['vote', poll, vote, signature, time]
				print('Found vote')

				if (blockData[i][1] not in finishedPolls):
					data = blockData[i][2]
					signature = blockData[i][3]

					hashFromData, dataUnderSignature = verifySignatureInnerFunction(data, signature, publicKey)
					
					if (hashFromData == dataUnderSignature):
						pollResults[blockData[i][1]][data] += 1

			elif (len(blockData[i]) == 6 and type(blockData[i]) == list):						# ['poll', index, theme, answers, voters, finishTime]
				print('Found poll')																# '18/03/2022 09:31:19'

				index = blockData[i][1]
				answers = {}
				for j in range(len(blockData[i][3])):
					answers.update({blockData[i][3][j] : 0})

				pollResults.update({index : answers})

		if (thisBlockIsTheLast):
			break

	if (thisBlockIsTheLast or int(poll) in finishedPolls):
		answer = {'message' : 'Poll is finished'}
		answer.update({'results' : pollResults[int(poll)]})
		return jsonify(answer), 201

	if (int(poll) in pollResults.keys()):
		answer = {'message' : 'Poll is not finished'}
		answer.update({'results' : pollResults[int(poll)]})
		return jsonify(answer), 201
	
	else:
		answer = {'message' : 'Poll is not found'}
		return jsonify(answer), 202


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5020)
