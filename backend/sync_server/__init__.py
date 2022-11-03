from flask import Blueprint

from backend.sync_server.SyncServer import sync_server

server = Blueprint("Server", __name__)
server.register_blueprint(sync_server)