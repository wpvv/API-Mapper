from flask import Blueprint

from backend.connection.ConnectionConfig import connection_config
from backend.connection.ConnectionVariable import connection_variable

connection = Blueprint("Connection", __name__)
connection.register_blueprint(connection_config)
connection.register_blueprint(connection_variable)