import pymongo
from bson import ObjectId
from flask import Blueprint, jsonify, request

import ApplicationConfig

connection_config = Blueprint("ConnectionConfig", __name__, template_folder="templates")

mongo_client = pymongo.MongoClient("mongodb://database:27017/")

db = mongo_client["APIMapping"]
collection = db["connections"]


def set_state_helper(connection_id, state):
    """

    :param connection_id:
    :param state:
    :return:
    """
    update = collection.update_one(
        {"_id": ObjectId(connection_id)}, {"$set": {"state": state}}
    )
    return update.acknowledged


def set_state(connection_id):
    """

    :param connection_id:
    :return:
    """
    config = get_connection_config(str(connection_id), internal=True)
    required = ["applicationIds", "description", "version", "endpointMapping"]
    low_level_mapping = True
    if "endpointMapping" in config and config["endpointMapping"]:
        for item in config["endpointMapping"]:
            if "recommendation" in item and not item["recommendation"]:
                if "complete" not in item or not item["complete"]:
                    low_level_mapping = False
    if all(name in config for name in required) and low_level_mapping:
        return set_state_helper(connection_id, "Complete")
    else:
        if not all(name in config for name in required):
            missing_list = list(set(required) - set(config.keys()))
            missing_list = ["Low Level Mapping" if "endpointMapping" in element else element.capitalize() for element in
                            missing_list]
            missing_list = ', '.join(missing_list)
            return set_state_helper(connection_id, missing_list + " missing")
        elif not low_level_mapping:
            return set_state_helper(connection_id, "Low level mapping incomplete")


def get_application_name(application_id):
    """Returns name of application given its id

    This helper function gets the name of the application given the id. This is easier and cleaner than doing the
    same with a $lookup in MongoDB, that query would be around 50 lines of code
    :param application_id: Mongodb id of
    application given as a string
    :return: application name as a string
    """
    config = ApplicationConfig.get_application_config(application_id, internal=True)
    if config:
        return config["name"]
    else:
        return ""


def get_application_specs(application_id):
    """Returns OpenAPI specs of application given its id

    This helper function gets the specs of the application given the id.
    :param application_id: Mongodb id of application given as a string
    :return: application config as an object
    """
    config = ApplicationConfig.get_application_config(application_id, internal=True)
    return config["specs"]


@connection_config.route("/api/connection/", methods=["GET"])
def get_connection_configs(internal=False):
    """Returns a list of all the connections

    This function generates a list of all the connections made between applications
    :return: JSON list of dictionaries containing, application names, description, version and state
    """
    configs = []
    if collection.find({}):
        for item in collection.find().sort("name"):
            configs.append(
                {
                    "id": str(item["_id"]),
                    "application1": get_application_name(item["applicationIds"][0]),
                    "application2": get_application_name(item["applicationIds"][1]),
                    "description": item["description"] if "description" in item else "",
                    "version": item["version"] if "version" in item else "",
                    "state": item["state"],
                    "static": item["static"] if "static" in item else True,
                }
            )
    if internal:
        return configs
    else:
        return (
            jsonify({"success": True, "connections": configs}),
            200,
            {"ContentType": "application/json"},
        )


@connection_config.route("/api/connection/complete", methods=["GET"])
def get_complete_connection_configs():
    """Returns a list of all the connections that are marked as complete

    This helper function uses get_connection_configs and filters out all the incomplete connections
    :return: a JSON list of the complete connections
    """
    return (
        jsonify({"success": True,
                 "configs": [item for item in get_connection_configs(internal=True) if item["state"] == "Complete"]}),
        200,
        {"ContentType": "application/json"},
    )


@connection_config.route("/api/connection/<connection_id>", methods=["GET"])
def get_connection_config(connection_id, flow=True, internal=False):
    """

    :param connection_id:
    :param flow:
    :param internal:
    :return:
    """
    connection_id = ObjectId(connection_id)
    config = collection.find_one({"_id": connection_id})
    config["id"] = str(config["_id"])
    if flow:
        for application_id in config["applicationIds"]:
            config[application_id] = get_application_name(application_id)
    config.pop("_id")
    if internal:
        return config
    else:
        return (
            jsonify({"success": True, "config": config}),
            200,
            {"ContentType": "application/json"},
        )


@connection_config.route(
    "/api/connection/generate/<application_id1>/<application_id2>", methods=["GET"]
)
def generate_connection_id(application_id1, application_id2):
    """

    :param application_id1:
    :param application_id2:
    :return:
    """
    config = {
        "applicationIds": [application_id1, application_id2],
        "static": False,
    }
    response = collection.insert_one(config)
    if response.acknowledged:
        set_state(response.inserted_id)
        return (
            jsonify({"success": True, "id": str(response.inserted_id)}),
            200,
            {"ContentType": "application/json"},
        )
    else:
        return (
            jsonify({"success": False, "message": "Saving in database failed"}),
            500,
            {"ContentType": "application/json"},
        )


@connection_config.route("/api/connection/<connection_id>", methods=["PUT"])
def update_connection_config(connection_id, config=None, internal=False):
    """

    :param connection_id:
    :param config:
    :param internal:
    :return:
    """
    connection_id = ObjectId(connection_id)
    if config is None:
        config = request.get_json()
    if "id" in config:
        config.pop("id")
    updated = collection.update_one({"_id": connection_id}, {"$set": config})
    if updated.acknowledged:
        if "state" not in config:
            set_state(connection_id)
        if internal:
            return connection_id
        else:
            return (
                jsonify({"success": True, "id": str(connection_id)}),
                200,
                {"ContentType": "application/json"},
            )
    else:
        if internal:
            return None
        else:
            return (
                jsonify({"success": False, "message": "Saving connection details failed"}),
                500,
                {"ContentType": "application/json"},
            )


@connection_config.route("/api/connection/<connection_id>", methods=["DELETE"])
def delete_connection_config(connection_id):
    """

    :param connection_id:
    :return:
    """
    config = get_connection_config(connection_id, flow=False, internal=True)
    if "static" in config and config["static"]:
        return jsonify({"success": False, "message": "Deleting a static application is not possible"}), 400, {
            "ContentType": "application/json"
        }
    else:
        connection_id = ObjectId(connection_id)
        deleted = collection.delete_one({"_id": connection_id})
        if deleted.acknowledged:
            return jsonify({"success": True}), 200, {"ContentType": "application/json"}
        else:
            return jsonify({"success": False, "message": "Deleting connection failed"}), 500, {
                "ContentType": "application/json"
            }


def delete_connections_with_application(application_id):
    """

    :param application_id:
    """
    connections = collection.find({"applicationIds": application_id})
    for connection in connections:
        delete_connection_config(connection["_id"])
