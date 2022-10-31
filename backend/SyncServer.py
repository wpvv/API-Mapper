import logging
import time
import traceback
from threading import Thread

from flask import Blueprint, jsonify, request

import SyncServerHelpers

server_config = Blueprint("server", __name__, template_folder="templates")

sync_server_log = logging.getLogger("sync_server")
sync_server_log_handler = logging.StreamHandler()
sync_server_log_file = logging.FileHandler("sync_server.log", mode="w")
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


@server_config.route("/api/server/start/", methods=["GET"])
def start_sync_server():
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
    if SyncServerHelpers.handle_sdk_state(connection_config, application_configs):
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


@server_config.route("/api/server/stop/", methods=["GET"])
def stop_sync_server(emergency_stop=False):
    global stop_thread
    global clear_cache
    if get_state_sync_server() and not stop_thread:
        sync_server_log.info(
            "=================== Stopping Sync Server ==================="
        )
        stop_thread = True
        sync_server_log.info("Clearing cache...")
        time.sleep(5)
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


@server_config.route("/api/server/log")
def get_sync_server_log():
    args = request.args
    previous_messages = args.get("messages", default=0, type=int)
    with open("sync_server.log") as f:
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


def get_state_sync_server():
    if background_thread is not None:
        if background_thread.is_alive():
            return True
    else:
        return False


def background_process(connection_config, polling_interval, sdks, mapping_config):
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
