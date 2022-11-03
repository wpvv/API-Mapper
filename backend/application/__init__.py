from flask import Blueprint

from backend.application.ApplicationConfig import application_config

application = Blueprint("Application", __name__)
application.register_blueprint(application_config)