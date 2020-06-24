from flask import Blueprint
from flask_restful import Api

bp = Blueprint('api', __name__, template_folder='templates')
api = Api (bp)

from app.api import routes, schemas

api.add_resource(routes.LibraryListApi, '/api/v1/library')
api.add_resource(routes.LibraryUploadApi, '/api/v1/library/<int:id>')

api.add_resource(routes.ConsultationListApi, '/api/v1/consultation/list')
api.add_resource(routes.ConsultationApi, '/api/v1/consultation/', '/api/v1/consultation/<int:id>')
api.add_resource(routes.ConsultationSchedulingApi, '/api/v1/consultation/schedule')

api.add_resource(routes.ChecklistApi, '/api/v1/checklist/<int:id>')
api.add_resource(routes.ChecklistColourApi, '/api/v1/checklist/colour/<int:id>')
api.add_resource(routes.ChecklistItemsApi, '/api/v1/checklist/item/<int:id>')