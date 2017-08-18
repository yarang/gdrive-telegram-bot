def get_telegram_info(cursor, id):
	query="select * from services where service_name='telegram' and id=" + str(id)
	cursor.execute(query)
	res = cursor.fetchone()
	return res

def get_google_info(cursor, id):
	query="select * from services where service_name='google' and selected=true and id=" + str(id)
	cursor.execute(query)
	res = cursor.fetchone()
	return res

def get_user_info(cursor, id):
	query="select * from users where id=" + str(id)
	cursor.execute(query)
	res = cursor.fetchone()
	return res

def add_google_info(cursor, id):
	query="select * from services where service_name='google' and selected=true and id=" + str(id)
	cursor.execute(query)
	res = cursor.fetchone()
	return res
