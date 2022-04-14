from hashlib import sha256
from time import time
from flask import Flask, jsonify, request
import json
from uuid import uuid4
from urllib.parse import urlparse
import requests
from requests.exceptions import ConnectionError
import ast
import sys

def pingNode(node):
	try:
		answer = requests.get(f'http://{node}/nodes/ping')

		if (answer.status_code == 200):
			return True
	except ConnectionError:
		return False

class Block:

	def __init__(self, _index, _previousHash, _nonce, _time, _data):
		self.index = _index
		self.previousHash = _previousHash
		self.nonce = _nonce
		self.time = _time
		self.data = _data

	def getIndex(self):
		return self.index

	def getPreviousHash(self):
		return self.previousHash

	def getNonce(self):
		return self.nonce

	def getTime(self):
		return self.time

	def getData(self):
		return self.data

	def toDict(self):
		block = {
			'index' : self.index,
			'previousHash' : self.previousHash,
			'nonce' : self.nonce,
			'time' : self.time,
			'data' : self.data
		}

		return block



def SHA256(inputString):
	return sha256(inputString.encode()).hexdigest()

def getHash(block):
	blockData = ''
	for i in block.data:
		blockData += str(i)
	return SHA256(str(block.index) + ';' + block.previousHash + ';' + str(block.nonce) + ';' + block.time + ';' + blockData)

def getHashFromDict(block):
	blockData = ''
	for i in block['data']:
		blockData += str(i)
	return SHA256(str(block['index']) + ';' + block['previousHash'] + ';' + str(block['nonce']) + ';' + block['time'] + ';' + blockData)


class Blockchain:

	def __init__(self):
		self.nodes = set()

		self.chain = []
		self.currentBlockData = []
		self.miningDifficulty = 4
		self.mempoolSize = 10
		self.addBlock(0)

	def getChain(self):
		return self.chain

	def getCurrentBlockData(self):
		return self.currentBlockData

	def getMiningDifficulty(self):
		return self.miningDifficulty	

	@property
	def getLatestBlock(self):
		return self.chain[-1]

	def addCurrentBlockData(self, dataToAdd):
		self.currentBlockData.append(dataToAdd)

		if (len(self.currentBlockData) == self.mempoolSize):

			answer = self.mine()
			print('Hash is ' + answer['hash'])

			return True, f'Mempool workload is now 10/{self.mempoolSize}.\nMempool is full. Mining initiated.'
		else:
			return False, f'Mempool workload is now {len(self.currentBlockData)}/{self.mempoolSize}.'

	def addBlock(self, nonce):
		if (len(self.chain) > 0):
			latestBlock = self.getLatestBlock
			currentPreviousHash = getHashFromDict(latestBlock)
			time_ = time()
		else:
			currentPreviousHash = '1'
			nonce = 100
			time_ = 0

		block = Block(len(self.chain) + 1, currentPreviousHash, nonce, str(time_), self.currentBlockData)

		self.currentBlockData = []

		self.chain.append(block.toDict())

		return block

	def addSharedBlock(self, block):

		if (block['previousHash'] != getHashFromDict(self.getLatestBlock)):
			return False

		if (self.isNonceCorrect(self.getLatestBlock['nonce'], block['nonce']) == False):
			return False

		self.chain.append(block)

		self.currentBlockData = []
		return True

	def shareLatestBlock(self, block):
		headers = {'Content-Type': 'application/json'}

		processed = str(block).replace("'", '"')
		data = '{"block":' + processed + '}'

		for node in self.nodes:
			if (pingNode(node)):
				answer = requests.post(f'http://{node}/nodes/shareLatestBlock', headers=headers, data=data)

				if (answer.status_code == 201):
					print('Block shared with node ' + str(node))
				else:
					print('Problem occured while sharing block with node ' + str(node))
				print(answer.json()['message'])
			else:
				print('Node ' + str(node) + ' is unavailable!')

	def shareLatestData(self, sharedData):
		'''
		headers = {'Content-Type': 'application/json'}

		data = '{"data":"' + sharedData + '"}'
		'''
		json_data = {'data': sharedData}

		for node in self.nodes:
			if (pingNode(node)):
				answer = requests.post(f'http://{node}/nodes/shareLatestData', json=json_data)

				if (answer.status_code == 201):
					print('Data shared with node ' + str(node))
				else:
					print('Problem occured while sharing data with node ' + str(node))
				print(answer.json()['message'])
			else:
				print('Node ' + str(node) + ' is unavailable!')




	def PoWOperation(self, nonce):
		latestBlock = self.getLatestBlock
		latestNonce = latestBlock['nonce']
		return SHA256(f'{latestNonce}@{nonce}')

	def PoWValidation(self, iteration):
		return iteration[:self.miningDifficulty] == '0' * self.miningDifficulty

	def PoW(self):

		nonce = 0

		iteration = self.PoWOperation(nonce)

		while (self.PoWValidation(iteration) == False):
			nonce += 1
			iteration = self.PoWOperation(nonce)

		return nonce

	def addNode(self, url):
		if (urlparse(url).netloc not in self.nodes):
			self.nodes.add(urlparse(url).netloc)

	def isNonceCorrect(self, latestNonce, currentNonce):
		return SHA256(f'{latestNonce}@{currentNonce}')[:self.miningDifficulty] == '0' * self.miningDifficulty

	def isChainValid(self, blockchain):

		latestBlock = blockchain[0]
		currentBlock = 1

		while (currentBlock < len(blockchain)):
			block = blockchain[currentBlock]

			if (block['previousHash'] != getHashFromDict(latestBlock)):
				return False

			if (self.isNonceCorrect(latestBlock['nonce'], block['nonce']) == False):
				return False

			latestBlock = block
			currentBlock += 1

		return True

	def reachConsensus(self):
		finalChain = None

		longestChainLength = len(self.chain)

		for node in self.nodes:
			answer = requests.get(f'http://{node}/chain')
			if (answer.status_code == 200):
				chain = answer.json()['chain']

				if (len(chain) > longestChainLength and self.isChainValid(chain)):
					longestChainLength = len(chain)
					finalChain = chain

		if (finalChain):
			self.chain = finalChain
			return True

		return False

	def mine(self):
		nonce = blockchain.PoW()

		addedBlock = blockchain.addBlock(nonce)

		print()
		print()
		print(addedBlock.toDict())
		print()
		print()

		blockchain.shareLatestBlock(addedBlock.toDict())

		answer = {'message' : 'Block is mined',
				  'index' : addedBlock.getIndex(),
				  'nonce' : addedBlock.getNonce(),
				  'hash' : getHash(addedBlock),
				  'data' : addedBlock.getData()}
		return answer

if (sys.argv[1] == '--port'):
	nodePort = int(sys.argv[2])

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

nodeId = str(uuid4()).replace('-', '')

blockchain = Blockchain()

@app.route('/currentBlockData/new', methods=['POST'])
def addCurrentBlockData():
	values = request.get_json(force=True, silent=True, cache=False)
	print(values)

	required = ['data']

	if not all(i in values for i in required):
		return "Some data is missing", 400

	blockchainAnswer = blockchain.addCurrentBlockData(values['data'])

	latestBlock = blockchain.getLatestBlock
	latestIndex = latestBlock['index']
	if (blockchainAnswer[0]):
		latestIndex -= 1
	answer = {'message' : f'Data will be added to block {latestIndex + 1}', 'mempoolLoadBool' : blockchainAnswer[0], 'mempoolMessage' : blockchainAnswer[1]}

	if (not blockchainAnswer[0]):
		blockchain.shareLatestData(values['data'])

	return jsonify(answer), 201


@app.route('/mine', methods=['GET'])
def mine():
	nonce = blockchain.PoW()

	addedBlock = blockchain.addBlock(nonce)

	blockchain.shareLatestBlock(addedBlock.toDict())

	answer = {'message' : 'Block is mined',
			  'index' : addedBlock.getIndex(),
			  'nonce' : addedBlock.getNonce(),
			  'hash' : getHash(addedBlock),
			  'data' : addedBlock.getData()}

	return jsonify(answer), 200


@app.route('/chain', methods=['GET'])
def getChain():
	answer = {'chain' : blockchain.chain}

	return jsonify(answer), 200


@app.route('/nodes/register', methods=['POST'])
def registerNodes():
	nodes = request.get_json(force=True, silent=True, cache=False).get('nodes')

	if (nodes is not None):
		for node in nodes:
			blockchain.addNode(node)

		answer = {'message' : 'Nodes added succesfully', 'listOfNodes' : list(blockchain.nodes)}

		return jsonify(answer), 201
	
	else:
		return 'Nodes list is invalid', 400


@app.route('/nodes/consensus', methods=['GET'])
def consensus():
	result = blockchain.reachConsensus()
	blockchain.currentBlockData = []

	if (result):
		answer = {'message' : 'Chain was updated', 'newChain' : blockchain.chain}

	else:
		answer = {'message' : 'Chain is the longest', 'chain' : blockchain.chain}

	return jsonify(answer), 200


@app.route('/nodes/shareLatestBlock', methods=['POST'])
def shareLatestBlock():
	block = request.get_json(force=True, silent=True, cache=False).get('block')

	if (block is not None):
		result = blockchain.addSharedBlock(block)
		if (result):
			answer = {'message' : 'Shared block has been added to the chain', 'newChain' : blockchain.chain}
			return jsonify(answer), 201
		else:
			answer = {'message' : 'Shared block is invalid or was mined before', 'chain' : blockchain.chain}
			return jsonify(answer), 400
	else:
		answer = {'message' : 'Some data is missing, shared block has not been added to the mempool', 'chain' : blockchain.currentBlockData}
		return jsonify(answer), 400


@app.route('/nodes/shareLatestData', methods=['POST'])
def shareLatestData():
	data = request.get_json(force=True, silent=True, cache=False).get('data')

	if (data is not None):
		blockchain.currentBlockData.append(data)
		answer = {'message' : 'Shared data has been added to the mempool', 'newChain' : blockchain.currentBlockData}
		return jsonify(answer), 201
	else:
		answer = {'message' : 'Some data was missing, shared data has not been added to the mempool', 'chain' : blockchain.currentBlockData}
		return jsonify(answer), 400

explorerAddress = "127.0.0.1:5020"

@app.route('/backupChainFromFile', methods=['POST'])
def backupChainFromFile():
	data = request.get_json(force=True, silent=True, cache=False).get('data')
	flag = True

	if (data is not None):
		chain, signature, publicKeyFromLastSession = data.split('\n')

		signature = int(signature)
		publicKeyFromLastSession = publicKeyFromLastSession.split(', ')
		publicKeyFromLastSession = (int(publicKeyFromLastSession[0][1:]), int(publicKeyFromLastSession[1][:len(publicKeyFromLastSession[1]) - 1]))

		json_data = {'data': chain, 'signature' : signature, 'publicKey' : publicKeyFromLastSession}
		answer = requests.post(f'http://{explorerAddress}/verifySignature', json=json_data)

		if (answer.status_code == 201):
			if (answer.json()['message'] == 'Data is valid'):
				blockchain.chain = ast.literal_eval(chain)
				answer1 = {'message' : 'Chain backuped succesfully', 'mempoolLoad' : len(blockchain.currentBlockData)}
			else:
				answer1 = {'message' : 'Chain signature is invalid'}

		return jsonify(answer1), 201
	else:

		answer = {'message' : 'Error occured while chain backuping'}
		return jsonify(answer), 400


@app.route('/nodes/cleanMempool', methods=['GET'])
def cleanMempool():
	blockchain.currentBlockData = []

	answer = {'message' : 'Mempoll was cleaned'}

	return jsonify(answer), 200


@app.route('/nodes/ping', methods=['GET'])
def ping():
	answer = {'message' : 'Working...'}
	return jsonify(answer), 200

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=nodePort)

