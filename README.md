# Decentralized voting platform using blind signature and blockchain

This is a telegram bot voting platform, that uses decentralized blockchain to store data and blind signature to sign votes.

To run this project Python, Docker, PostgreSQL and some python packages.

System makes backups of nodes every time block is mined. It allows to reduce possible data loss to the mempool size in case of emergency situations in the system operation.\
System uses PostgreSQL database to store user variables, active polls and active voters lists for bot operations.

Running in several terminal windows looks like:\
FOLDER : COMMAND
________________
postgres			  : docker-compose up\
postgres		 	  : python3 create.py\

blockchain			: python3 main.py --port 5002\
blockchain			: python3 main.py --port 5003\
...\
blockchain			: python3 main.py --port n

blindSignature  : python3 validator.py

blockExplorer		: python3 resultsExplorer.py

bot					    : python3 bot2.0.py\
or \
bot		    			: python3 bot2.0.py --backupChain 		? to backup chain from last session\
or\
bot				    	: python3 bot2.0.py --cleanDB     		? to clean databases before start

Currently this bot is unavailable to reach in Telegram due to lack of servers, where it can be stored :). 
