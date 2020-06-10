from flask import current_app
from flask_login import current_user

from app import db

from datetime import datetime

class ApiKey(db.Model):
	__table_args__ = {'sqlite_autoincrement': True}
	id = db.Column(db.Integer, primary_key=True)
	created = db.Column(db.DateTime, default=datetime.now())
	key = db.Column(db.String(64))
	description = db.Column(db.String(280))
	
	def __repr__(self):
		return '<API Key {}>'.format(self.key)

def validate_api_key (key):
	if ApiKey.query.filter_by(key=key).first() == None: return False
	else: return True

def create_new_api_key (key, description):
	api_key = ApiKey(key = key,
					 description = description,
					 created = datetime.now())
	db.session.add(api_key)
	db.session.commit()
	return api_key
	
def delete_api_key (id):
	try:
		api_key = ApiKey.query.get(id)
		db.session.delete(api_key)
		db.session.commit()
		return True
	except:
		return False
	
