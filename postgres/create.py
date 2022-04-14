import psycopg2
from psycopg2 import Error
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


try:
	connection = psycopg2.connect(user="admin",
								  password="admin",
								  host="127.0.0.1",
								  port="5432")
	connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
	cursor = connection.cursor()
	sql_create_database = 'create database botData'
	cursor.execute(sql_create_database)
	cursor.close()
	connection.close()

except (Exception, Error) as error:
	print("Error occured while working with PostgreSQL", error)


try:
	connection = psycopg2.connect(user="admin",
								  password="admin",
								  host="127.0.0.1",
								  port="5432",
								  database="botdata")

	cursor = connection.cursor()

	create_table_query = '''CREATE TABLE personalVariables
						  (ID 						TEXT		NOT NULL,
						  CREATINGVOTE 				TEXT[],
						  CREATINGVOTEANSWERVARIETY TEXT[],
						  CREATINGVOTEFINISHTIME 	TEXT); '''

	cursor.execute(create_table_query)
	connection.commit()
	print("personalVariables table created in PostgreSQL")

except (Exception, Error) as error:
	print("Error occured while creating personalVariables table in PostgreSQL", error)


try:
	create_table_query = '''CREATE TABLE creatingPoll
						  (ID 						TEXT		NOT NULL,
						  POLLID 					TEXT,
						  THEME						TEXT,
						  ANSWERVARIETY 			TEXT[],
						  VOTERS 					TEXT[],
						  FINISH 					TEXT); '''

	cursor.execute(create_table_query)
	connection.commit()
	print("creatingPoll table created in PostgreSQL")

except (Exception, Error) as error:
	print("Error occured while creating creatingPoll table in PostgreSQL", error)


try:
	create_table_query = '''CREATE TABLE activePolls
						  (ID					TEXT		NOT NULL,
						  THEME					TEXT,
						  ANSWERVARIETY 		TEXT[],
						  VOTERS 				TEXT[],
						  FINISH 				TEXT); '''

	cursor.execute(create_table_query)
	connection.commit()
	print("activePolls table created in PostgreSQL")

except (Exception, Error) as error:
	print("Error occured while creating activePolls table in PostgreSQL", error)


try:
	create_table_query = '''CREATE TABLE activeVoters
						  (ID					TEXT 		NOT NULL); '''

	cursor.execute(create_table_query)
	connection.commit()
	print("activeVoters table created in PostgreSQL")

	cursor.close()
	connection.close()


except (Exception, Error) as error:
	print("Error occured while creating activeVoters table in PostgreSQL", error)