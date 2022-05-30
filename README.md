# Decentralized voting platform using blind signature and blockchain

This is a telegram bot voting platform, that uses decentralized blockchain to store data and blind signature to sign votes.

Another version of this bot with several improvements is available [here](https://github.com/alien111/decentralizedVotingPlatform2.0).

To run this project Python, Docker, PostgreSQL and some python packages are required.

System makes backups of nodes every time block is mined. It allows to reduce possible data loss to the mempool size in case of emergency situations in the system operation.\
System uses PostgreSQL database to store user variables, active polls and active voters lists for bot operations.

Scheme of nodes connection
![scheme11_2](/pics/scheme11_2.jpg "")

Scheme of voting process
![scheme2](/pics/scheme2.jpg "")

Using this bot is simple! Check the screenshots.

Buttons which help user to interact with system
![1](/pics/1.png "")

Poll creating
![2](/pics/2.png "")
![3](/pics/3.png "")

Voting
![4](/pics/4.png "")
![5](/pics/5.png "")
![6](/pics/6.png "")

Poll results exploring
![7](/pics/7.png "")
![8](/pics/8.png "")

Error report from user
![9](/pics/9.png "")

When a report is sent, I(developer) receive a message from bot with this error report.
![10](/pics/10.png "")


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
