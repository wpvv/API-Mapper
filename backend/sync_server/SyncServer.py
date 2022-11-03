import logging
import time
import traceback
from threading import Thread

from flask import jsonify, request, Blueprint

from backend.sync_server import SyncServerHelpers

sync_server_log = logging.getLogger("sync_server")
sync_server_log_handler = logging.StreamHandler()
sync_server_log_file = logging.FileHandler("backend/sync_server.log", mode="w")
sync_server_log_format = logging.Formatter(
    fmt=str("[Sync Server] ") + "%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
sync_server_log_file.setFormatter(sync_server_log_format)
sync_server_log.addHandler(sync_server_log_handler)
sync_server_log.addHandler(sync_server_log_file)
sync_server_log.setLevel(logging.INFO)

background_thread = None
stop_thread = False
clear_cache = True

sync_server = Blueprint("SyncServer", __name__)

@sync_server.route("/api/server/start/", methods=["GET"])
def start_sync_server() -> tuple:
    """ Function to initialise the sync server. It will gather all configs format them and check if everything is ready
    for the sync to start. If so the background tread global is set and the background process, that will sync APIs
    is started.

    :return: Flask responses with errors if they occur in the initialisation phase
    """
    sync_server_log.info(
        "=================== Initializing Sync Server ==================="
    )
    args = request.args
    connection_id = args.get("id", default=None, type=str)
    polling_interval = args.get("interval", default=5, type=int)
    global clear_cache
    clear_cache = args.get("cache", default=True, type=bool)
    connection_config, application_configs = SyncServerHelpers.format_configs(
        connection_id
    )
    if connection_config["state"] != "Complete":
        return (
            jsonify(
                {"success": False, "reason": "Mapped connection config is incomplete"}
            ),
            400,
            {"ContentType": "application/json"},
        )
    if connection_id is None:
        return (
            jsonify({"success": False, "reason": "Connection ID is not valid"}),
            500,
            {"ContentType": "application/json"},
        )
    refresh_sdk, emergency_stop = SyncServerHelpers.handle_sdk_state(connection_config, application_configs)
    if emergency_stop:
        return (
            jsonify(
                {"success": False, "reason": "An error occurred during the SDK handling"}
            ),
            500,
            {"ContentType": "application/json"},
        )
    if refresh_sdk:
        # if true configs need to be refreshed because sdks are generated and that changes the configs
        connection_config, application_configs = SyncServerHelpers.format_configs(
            connection_id
        )
    connection_config["id"] = connection_id
    mapping_config = SyncServerHelpers.get_mapping_config(
        connection_config, application_configs
    )
    if not mapping_config:
        return (
            jsonify(
                {
                    "success": False,
                    "reason": "The connection does not contain any GET requests, making it impossible to sync the "
                              "applications",
                }
            ),
            500,
            {"ContentType": "application/json"},
        )

    sync_server_log.info("Syncing the following applications: ")
    for application_id in connection_config["applicationIds"]:
        sync_server_log.info(application_configs[application_id]["name"])

    state, sdks = SyncServerHelpers.get_sdks_as_import(
        connection_config, application_configs
    )
    if not state:
        return (
            jsonify({"success": False, "reason": "There was an error importing SDKs"}),
            500,
            {"ContentType": "application/json"},
        )
    global background_thread
    global stop_thread
    stop_thread = False
    if not get_state_sync_server():
        sync_server_log.info(
            "=================== Started Sync Server ==================="
        )
        background_thread = Thread(
            target=background_process,
            args=[connection_config, polling_interval, sdks, mapping_config],
        )
        background_thread.start()
        return jsonify({"success": True}), 200, {"ContentType": "application/json"}
    else:
        sync_server_log.error("Sync Server is already running")
        return (
            jsonify({"success": False, "reason": "server is already running"}),
            500,
            {"ContentType": "application/json"},
        )


@sync_server.route("/api/server/stop/", methods=["GET"])
def stop_sync_server(emergency_stop: bool = False) -> tuple | None:
    """ Function to stop the background process. This function is used by the frontend to stop the sync process. But also
    when an error occurs it is called as an emergency stop

    :param emergency_stop: indication of return type, emergency stop is only used internally
    :return: None if internal, a flask response in case of it being called by the frontend
    """
    global stop_thread
    global clear_cache
    if get_state_sync_server() and not stop_thread:
        sync_server_log.info(
            "=================== Stopping Sync Server ==================="
        )
        stop_thread = True
        sync_server_log.info("Clearing cache...")
        time.sleep(5)  # To make sure the thread and background process are stopped
        if clear_cache:
            SyncServerHelpers.empty_cache()
        sync_server_log.info(
            "=================== Stopped Sync Server ==================="
        )
        sync_server_log_file.close()
        if not emergency_stop:
            return jsonify({"success": True}), 200, {"ContentType": "application/json"}
        else:
            return
    else:
        sync_server_log.error("Sync Server was not running")
        if not emergency_stop:
            return (
                jsonify({"success": False, "reason": "server not running"}),
                500,
                {"ContentType": "application/json"},
            )
        else:
            return


@sync_server.route("/api/server/log")
def get_sync_server_log() -> tuple:
    """ Function to get the latest server logs

    :return: Flask response containing the server logs
    """
    args = request.args
    previous_messages = args.get("messages", default=0, type=int)
    with open("backend/sync_server.log") as f:
        messages = f.readlines()
    if len(messages) > previous_messages:
        return (
            jsonify(
                {
                    "success": True,
                    "syncServer": get_state_sync_server(),
                    "data": messages[previous_messages:],
                }
            ),
            200,
            {"ContentType": "application/json"},
        )
    else:
        return (
            jsonify({"success": True, "syncServer": get_state_sync_server()}),
            200,
            {"ContentType": "application/json"},
        )


def get_state_sync_server() -> bool:
    """ Function check the state of the background process, primarily used by the state API that gets called by the
    frontend every 5 seconds

    :return: bool if sync server is running
    """
    if background_thread is not None:
        if background_thread.is_alive():
            return True
    return False


def background_process(
        connection_config: dict, polling_interval: int, sdks: dict, mapping_config: dict
) -> None:
    """ Function that does the actual syncing of APIs by calling the function to sync a specific connection between APIs

    :param connection_config: configuration of the connection between applications
    :param polling_interval: integer of interval to wait between sync runs
    :param sdks: a dict containing the imported SDKs of the applications
    :param mapping_config: list of connections of APIs that need syncing
    """
    while not stop_thread:
        for endpoint in mapping_config:
            try:
                SyncServerHelpers.find_call_type(
                    connection_config, sdks, endpoint, polling_interval
                )
            except Exception as e:
                sync_server_log.error("Unknown error: " + str(e))
                sync_server_log.error(traceback.format_exc())
                stop_sync_server(emergency_stop=True)
                break
        time.sleep(polling_interval)
