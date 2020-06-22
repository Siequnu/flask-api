from flask_marshmallow import Marshmallow
from app.models import LibraryUpload
from app.consultations.models import Consultation
from app import ma

class LibraryUploadSchema (ma.SQLAlchemySchema):
	class Meta:
		fields = ('id', 'title', 'description', 'filename')
		
class ConsultationSchema (ma.SQLAlchemySchema):
	class Meta:
		fields = ('id', 'date', 'start_time', 'end_time', 'teacher_id', 'student_id')

class ConsultationSchedulingSchema (ma.SQLAlchemySchema):
	class Meta:
		fields = ('id', 'consultation_id', 'date', 'start_time', 'end_time')

class ChecklistSchema (ma.SQLAlchemySchema):
	class Meta:
		fields = ('id', 'title', 'description', 'user_id', 'completed_percentage')

class ChecklistItemSchema (ma.SQLAlchemySchema):
	class Meta:
		fields = ('id', 'title', 'description', 'completed', 'user_id')

