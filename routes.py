from flask import Flask, request, abort, flash, current_app, session, Response, render_template, url_for, redirect, jsonify
from flask_login import login_required, current_user
from flask_restful import Resource, reqparse

from app import db
import app.models
from app.models import LibraryUpload, Enrollment, User
from app.consultations.models import Consultation, ConsultationSchedulingOption
from app.checklists.models import Checklist, ChecklistItem
from app.goals.models import StudentGoalTemplate
import app.checklists.models
from app.api.schemas import LibraryUploadSchema, ConsultationSchema, ConsultationSchedulingSchema, ChecklistSchema, ChecklistItemSchema, StudentGoalTemplateSchema

from app.api import bp, models
from app.api.models import ApiKey
from app.api.forms import ApiCreationForm

import json, secrets, random
from datetime import datetime

# API management GUI Routes
@bp.route("/api/manage")
@login_required
def manage_api_keys():
	if app.models.is_admin(current_user.username):
		api_keys = ApiKey.query.all()
		return render_template('api/manage_api_keys.html', api_keys=api_keys)
	abort(403)

@bp.route("/api/create", methods=['GET', 'POST'])
@login_required
def create_api_key():
	if app.models.is_admin(current_user.username):
		key = secrets.token_urlsafe(40)
		form = ApiCreationForm(key=key)
		if form.validate_on_submit():
			key = form.key.data
			description = form.description.data
			app.api.models.create_new_api_key(key, description)
			flash('API key successfully created', 'success')
			return redirect(url_for('api.manage_api_keys'))
		return render_template('api/create_api_key.html', form=form)
	abort(403)

@bp.route("/api/delete/<int:id>")
@login_required
def delete_api_key(id):
	if app.models.is_admin(current_user.username):
		if app.api.models.delete_api_key(id):
			flash('API key successfully created', 'success')
		else:
			flash('A problem occured while deleting your API key', 'error')
		return redirect(url_for('api.manage_api_keys'))
	abort(403)


# Simple API routes
# Return total library downloads
@bp.route("/api/library/stats")
@login_required
def get_library_stats():
	if app.models.is_admin(current_user.username):
		return jsonify({'download_count': app.files.models.get_total_library_downloads_count ()})
	abort(403)

# Return logged in users
@bp.route("/api/users/stats")
@login_required
def get_user_stats():
	if app.models.is_admin(current_user.username):
		return jsonify({
			'active_users': app.user.models.get_active_user_count(),
			'user_count': app.user.models.get_total_user_count()
		})
	abort(403)

# Return file stats
@bp.route("/api/files/stats")
@login_required
def get_file_stats():
	if app.models.is_admin(current_user.username):
		return jsonify({'total_uploads': app.files.models.get_all_uploads_count()})
	abort(403)

# Return random student from a class
@bp.route("/api/users/random/<int:turma_id>")
@login_required
def generate_random_student(turma_id):
	if app.models.is_admin(current_user.username):
		class_enrollments = Enrollment.query.filter_by (turma_id = turma_id).all()
		if len(class_enrollments) < 1: return False
		student = User.query.get(random.choice (class_enrollments).user_id)
		return jsonify({'random_student': student.username})
	abort(403)

# Parse a Zoom URL code
# Returns False if parsing fails
@bp.route("/api/classes/parse/", methods = ['POST'])
@login_required
def parse_zoom_invitation ():
	if app.models.is_admin (current_user.username):
		try:
			# Extract lesson data from pasted Zoom message	
			split = request.json['zoomInvitation'].split('Meeting ID: ')
			meeting_details = split[1].split('\nPasscode: ')
			meeting_id = meeting_details[0]
			meeting_passcode = meeting_details[1]

			meeting_url = request.json['zoomInvitation'].split('Join Zoom Meeting\n')
			meeting_url = meeting_url[1].split('\n\nMeeting ID:')
			meeting_url = meeting_url[0]

			return jsonify ({
				'meeting_url': meeting_url,
				'meeting_id': meeting_id,
				'meeting_passcode': meeting_passcode
			})
		except:
			return jsonify ({'error': 'Could not process the data.'})
	abort (403)
# API schemas
library_uploads_schema = LibraryUploadSchema(many=True)
library_upload_schema = LibraryUploadSchema()

consultations_schema = ConsultationSchema(many=True)
consultation_schema = ConsultationSchema()
consultation_scheduling_schema = ConsultationSchedulingSchema()

checklist_schema = ChecklistSchema ()
checklist_item_schema = ChecklistItemSchema ()

student_goal_template_schema = StudentGoalTemplateSchema ()

class StudentGoalTemplateApi (Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('title', type=str, location='json')
		self.reqparse.add_argument('template_data', type=str, location='json')
		super(StudentGoalTemplateApi, self).__init__()

	def post(self):
		args = self.reqparse.parse_args()
		if models.validate_api_key(request.headers.get('key')):
			student_goal_template = StudentGoalTemplate()
			student_goal_template.title = args['title']
			student_goal_template.template_data = args['template_data']

			db.session.add(student_goal_template)
			db.session.flush()
			db.session.commit()

			result = student_goal_template_schema.dump(student_goal_template)

			return result, 200
		else:
			return {}, 401


class ChecklistApi (Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		super(ChecklistApi, self).__init__()

	def get(self, id):
		args = self.reqparse.parse_args()
		if models.validate_api_key(request.headers.get('key')):
			checklist = Checklist.query.get(id)
			if not checklist:
				return {'message': 'Checklist does not exist'}, 400
			checklist_dict = checklist.__dict__
			checklist_dict['completed_percentage'] = checklist.get_completed_progress_percentage ()
			checklist_dict['items_remaining'] = checklist.get_remaining_items_count ()
			checklist = checklist_schema.dump(checklist_dict)
			return checklist, 200
		else:
			return {}, 401


class ChecklistItemsApi (Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('completed', type=bool, location='json')
		super(ChecklistItemsApi, self).__init__()

	def put(self, id):
		args = self.reqparse.parse_args()
		if models.validate_api_key(request.headers.get('key')):
			checklist_item = ChecklistItem.query.filter_by(id=id).first()
			if not checklist_item:
				return {'message': 'Checklist item does not exist'}, 400
			checklist_item.completed = args['completed']
			db.session.commit()
			result = checklist_item_schema.dump(checklist_item)

			return result, 200
		else:
			return {}, 401

class ChecklistColourApi (Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('hue', type=int, location='json')
		self.reqparse.add_argument('saturation', type=int, location='json')
		self.reqparse.add_argument('lightness', type=int, location='json')
		super(ChecklistColourApi, self).__init__()

	def put(self, id):
		args = self.reqparse.parse_args()
		if models.validate_api_key(request.headers.get('key')):
			checklist = Checklist.query.get(id)
			if not checklist:
				return {'message': 'Checklist does not exist'}, 400
			
			hue = args['hue']
			saturation = args['saturation']
			lightness = args['lightness']
			
			checklist.set_hsl (hue, saturation, lightness)
			db.session.commit()
			
			result = checklist_schema.dump(checklist)
			return result, 200
		else:
			return {}, 401


class ConsultationListApi (Resource):
	def get(self):
		if models.validate_api_key(request.headers.get('key')):
			consultations = consultations_schema.dump(Consultation.query.all())
			return consultations, 200
		else:
			return {}, 401


class ConsultationApi (Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('date', type=str, location='json')
		self.reqparse.add_argument('start_time', type=str, location='json')
		self.reqparse.add_argument('end_time', type=str, location='json')
		self.reqparse.add_argument('teacher_id', type=str, location='json')
		self.reqparse.add_argument('student_id', type=str, location='json')
		super(ConsultationApi, self).__init__()

	def get(self, id):
		args = self.reqparse.parse_args()
		if models.validate_api_key(request.headers.get('key')):
			consultation = consultation_schema.dump(Consultation.query.get(id))
			return consultation, 200
		else:
			return {}, 401

	def post(self):
		args = self.reqparse.parse_args()
		if models.validate_api_key(request.headers.get('key')):
			consultation = Consultation()
			consultation.date = args['date']
			consultation.start_time = args['start_time']
			consultation.end_time = args['end_time']
			consultation.teacher_id = args['teacher_id']
			consultation.student_id = args['student_id']

			db.session.add(consultation)
			db.session.flush()
			db.session.commit()

			result = consultation_schema.dump(consultation)

			return result, 200
		else:
			return {}, 401

	def put(self, id):
		args = self.reqparse.parse_args()
		if models.validate_api_key(request.headers.get('key')):
			consultation = Consultation.query.filter_by(id=id).first()
			if not consultation:
				return {'message': 'Consultation does not exist'}, 400
			consultation.date = args['date']
			consultation.start_time = args['start_time']
			consultation.end_time = args['end_time']
			consultation.teacher_id = args['teacher_id']
			consultation.student_id = args['student_id']

			db.session.commit()
			result = consultation_schema.dump(consultation)

			return result, 200
		else:
			return {}, 401


class ConsultationSchedulingApi (Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument(
			'consultation_id', type=str, location='json')
		self.reqparse.add_argument('date', type=str, location='json')
		self.reqparse.add_argument('start_time', type=str, location='json')
		self.reqparse.add_argument('end_time', type=str, location='json')
		super(ConsultationSchedulingApi, self).__init__()

	def get(self, id):
		args = self.reqparse.parse_args()
		if models.validate_api_key(request.headers.get('key')):
			consultation_schedule = consultation_scheduling_schema.dump(
				ConsultationSchedulingOption.query.get(id))
			return consultation_schedule, 200
		else:
			return {}, 401

	def post(self):
		args = self.reqparse.parse_args()
		if models.validate_api_key(request.headers.get('key')):
			if Consultation.query.get(args['consultation_id']) is None:
				return {'error': 'Could not locate the consultation you requested.'}, 401
			consultation_schedule = ConsultationSchedulingOption()
			consultation_schedule.consultation_id = args['consultation_id']
			
			# Convert the form strings into DateTime objects
			date_object = datetime.strptime(args['date'], '%Y-%m-%d').date()
			consultation_schedule.date = date_object

			# Combine the date with the start and end times to make full DateTime object
			start_time_object = datetime.strptime(args['start_time'], '%H:%M').time()
			consultation_schedule.start_time = datetime.combine(
				date_object, start_time_object)
			
			end_time_object = datetime.strptime(args['end_time'], '%H:%M').time()
			consultation_schedule.end_time = datetime.combine(
				date_object, end_time_object)
			
			db.session.add(consultation_schedule)
			db.session.flush()
			db.session.commit()

			result = consultation_scheduling_schema.dump(consultation_schedule)

			return result, 200
		else:
			return {}, 401


class LibraryListApi (Resource):
	def get(self):
		if models.validate_api_key(request.headers.get('key')):
			library_uploads = library_uploads_schema.dump(
				LibraryUpload.query.all())
			return library_uploads, 200
		else:
			return {}, 401


class LibraryUploadApi (Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('title', type=str, location='json')
		self.reqparse.add_argument('description', type=str, location='json')
		super(LibraryUploadApi, self).__init__()

	def get(self, id):
		args = self.reqparse.parse_args()
		if models.validate_api_key(request.headers.get('key')):
			library_upload = library_upload_schema.dump(
				LibraryUpload.query.get(id))
			return library_upload, 200
		else:
			return {}, 401

	def put(self, id):
		args = self.reqparse.parse_args()
		if models.validate_api_key(request.headers.get('key')):
			library_upload = LibraryUpload.query.filter_by(id=id).first()
			if not library_upload:
				return {'message': 'Upload does not exist'}, 400
			library_upload.title = args['title']
			library_upload.description = args['description']
			db.session.commit()
			result = library_upload_schema.dump(library_upload)

			return result, 200
		else:
			return {}, 401
