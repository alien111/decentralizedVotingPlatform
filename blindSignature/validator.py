from tools import *
import json
from flask import Flask, jsonify, request
import requests


app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False


@app.route('/getPublicKey', methods=['GET'])
def getPublicKey():
	answer = {'publicKey' : publicKey}
	return jsonify(answer), 200


@app.route('/signData', methods=['POST'])
def signData():
	values = request.get_json(force=True, silent=True, cache=False)
	required = ['data']

	if not all(i in values for i in required):
		return "Some data is missing", 400

	data = values['data']

	signedData = sign(data, privateKey)
	answer = {'signedData' : signedData}

	return jsonify(answer), 201



if __name__ == '__main__':
	publicKey, privateKey = keysGeneration(2 ** 256)
	app.run(host='0.0.0.0', port=5010)