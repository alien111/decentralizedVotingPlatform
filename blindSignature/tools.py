import sympy
import math
import random
from hashlib import sha256

# got from cryptomath
def findModInverse(a, m):
	# Returns the modular inverse of a % m, which is
	# the number x such that a*x % m = 1

	if math.gcd(a, m) != 1:
		return None # no mod inverse if a & m aren't relatively prime

	# Calculate using the Extended Euclidean Algorithm:
	u1, u2, u3 = 1, 0, a
	v1, v2, v3 = 0, 1, m
	while v3 != 0:
		q = u3 // v3 # // is the integer division operator
		v1, v2, v3, u1, u2, u3 = (u1 - q * v1), (u2 - q * v2), (u3 - q * v3), v1, v2, v3
	return u1 % m

def keysGeneration(n):
	firstPrime = sympy.randprime(0, n)
	secondPrime = sympy.randprime(0, n)

	phi = (firstPrime - 1) * (secondPrime - 1)

	while (True):
		publicKey = random.randrange(phi)
		if (math.gcd(publicKey, phi) == 1):
			break
	privateKey = findModInverse(publicKey, phi)

	return (publicKey, firstPrime * secondPrime), (privateKey, firstPrime * secondPrime)

def blindData(intFromHash, publicKey):
	blindingFactor = random.randrange(0, publicKey[1])

	while (math.gcd(blindingFactor, publicKey[1]) != 1):
		blindingFactor += 1

	blindedIntFromHash = (pow(blindingFactor, publicKey[0], publicKey[1]) * intFromHash) % publicKey[1]

	return blindedIntFromHash, blindingFactor

def unblindData(data, blindingFactor, publicKey):
	unblindedData = (data * findModInverse(blindingFactor, publicKey[1])) % publicKey[1]
	return unblindedData

def sign(data, privateKey):
	signed = pow(data, privateKey[0], privateKey[1]) % privateKey[1]
	return signed

def showSignedUnblindedData(data, publicKey):
	showData = hex(pow(data, publicKey[0], publicKey[1]) % publicKey[1])[2:]
	return showData


'''	
publicKey, privateKey = keysGeneration(2 ** 256)

data = 'I love Ethereum!'
print(data)

blindedData, blindingFactor = blindData(data, publicKey)
print(blindedData)

signedBlindedData = sign(blindedData, privateKey)
print(signedBlindedData)

unblindedData = unblindData(signedBlindedData, blindingFactor, publicKey)
print(unblindedData)

showData = showSignedUnblindedData(unblindedData, blindingFactor, publicKey)
print(showData)
'''