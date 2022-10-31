import pymongo
from flask import Flask, jsonify

from ApplicationConfig import application_config
from ConnectionConfig import connection_config
from ConnectionHighLevelFlow import connection_high_level_flow
from ConnectionLowLevelFlow import connection_low_level_flow
from ConnectionScript import connection_script
from ConnectionVariable import connection_variable
from SyncServer import server_config, get_state_sync_server

mongo_client = pymongo.MongoClient("mongodb://database:27017/")
db = mongo_client["APIMapping"]

app = Flask(__name__)
app.register_blueprint(application_config)
app.register_blueprint(connection_config)
app.register_blueprint(server_config)
app.register_blueprint(connection_high_level_flow)
app.register_blueprint(connection_low_level_flow)
app.register_blueprint(connection_variable)
app.register_blueprint(connection_script)


@app.route("/api/state/")
def state_checker() -> tuple:
    """Returns success if called

    This function is used to check the connection between frontend and backend. It also returns the state of the sync
    server, this is in the form of a boolean, true if the server is running, false otherwise.
    :return: a json object with success and the sync server's status
    """
    sync_server = get_state_sync_server()
    return (
        jsonify({"success": True, "syncServer": sync_server}),
        200,
        {"ContentType": "application/json"},
    )
