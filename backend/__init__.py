import pymongo
from flask import Flask, jsonify

mongo_client = pymongo.MongoClient("mongodb://database:27017/")
db = mongo_client["APIMapping"]


def create_app():
    """Create and configure an instance of the Flask application."""

    # apply the blueprints to the app
    from backend.application import application
    from backend.connection import connection
    from backend.connection.high_level import connection_high_level
    from backend.connection.low_level import connection_low_level
    from backend.sync_server import server

    app = Flask(__name__)
    app.register_blueprint(application)
    app.register_blueprint(connection)
    app.register_blueprint(connection_high_level)
    app.register_blueprint(connection_low_level)
    app.register_blueprint(server)

    @app.route("/api/state/")
    def state_checker() -> tuple:
        """Returns success if called

        This function is used to check the connection between frontend and backend. It also returns the state of the sync
        server, this is in the form of a boolean, true if the server is running, false otherwise.
        :return: a json object with success and the sync server's status
        """
        from backend.sync_server.SyncServer import get_state_sync_server

        return (
            jsonify({"success": True, "syncServer": get_state_sync_server()}),
            200,
            {"ContentType": "application/json"},
        )
    return app
