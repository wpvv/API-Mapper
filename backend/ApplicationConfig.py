import json

import pymongo
import requests
import validators
from bson.objectid import ObjectId
from flask import jsonify, request, Blueprint
from requests.auth import HTTPBasicAuth

import ConnectionConfig
import clientSDK
import openAPI

application_config = Blueprint(
    "ApplicationConfig", __name__, template_folder="templates"
)

mongo_client = pymongo.MongoClient("mongodb://database:27017/")
db = mongo_client["APIMapping"]
collection = db["applications"]


def get_auth(application_id: str) -> tuple[dict, str] | tuple[dict, HTTPBasicAuth]:
    """Returns the authentication

    This functions returns the authentication for an API in a specific format.
    This format is headers first, basic second, if there is no authentication needed both headers and basic
    authentication are empty.

    :param application_id: id of application in string format
    :return: headers, basic
    """
    config = get_application_config(application_id, internal=True)
    if "securityScheme" in config:
        if config["securityScheme"] == "ApiKeyAuth":
            return config["headerItems"], ""
        elif config["securityScheme"] == "BasicAuth":
            return {}, HTTPBasicAuth(config["basicUsername"], config["basicPassword"])
    return {}, ""


def array_to_dict(data: list) -> tuple[bool, dict]:
    """Returns dict of headers with their keys as key of the dict

    This helper function converts an array of dicts with a key and value to a single dict with keys set as the
    dict keys with their value.

    :param data: array of dicts containing key and value,
    for example: [{"key": "exampleKey", "value": "exampleValue"}, {}]
    :return: a dict, for example return_dict["exampleKey"] gives exampleValue
    """
    return_dict = {}
    for item in data:
        key = item["key"]
        if key not in return_dict:
            return_dict[key] = item["value"]
        else:
            return False, {}
    return True, return_dict


def set_state(application_id: ObjectId) -> bool:
    """Returns boolean if status of the application is set correctly.

    This function check if the required elements in an application config are set. If all are set the status
    of the application is updated from "Incomplete" to "Complete".

    :param application_id: id of application in OBJECT format
    :return: boolean if state is set
    """
    config = get_application_config(str(application_id), internal=True)
    required = ["name", "description", "baseUrl", "securityScheme", "specs", "version"]
    if all(name in config for name in required):
        update = collection.update_one(
            {"_id": application_id}, {"$set": {"state": "Complete"}}
        )
        return update.acknowledged
    return False


def set_sdk(application_id: ObjectId) -> bool:
    """Returns boolean if the SDK of the application is set correctly.

    This function double-checks the existence of the SDK and updates it.
    This function is useful when the configuration is changed.

    :param application_id: id of application in OBJECT format
    :return: boolean if state is set
    """
    if clientSDK.double_check_sdk(application_id):
        if clientSDK.update_sdk(application_id):
            return True
    return False


@application_config.route("/api/application/save/", methods=["POST"])
def save_application_config() -> tuple:
    """Returns the application id after saving the new application config

    This function saves a new application config. It checks all the fields in the new config.
    It also imports and parses OpenAPI documents if present.

    :return: an JSON object if the saving was successful and the application is of the new application
    """
    config = request.get_json()
    if not validators.url(config["baseUrl"]):
        return (
            jsonify({"success": False, "message": "API Base URL is invalid"}),
            400,
            {"ContentType": "application/json"},
        )

    if config["automaticImport"]:
        if config["automaticImportURL"] != "":
            if validators.url(config["automaticImportURL"]):
                config.pop("automaticImportFileName")
                if not openAPI.get_openapi(config, url=config["automaticImportURL"]):
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "The OpenAPI specifications are invalid",
                            }
                        ),
                        400,
                        {"ContentType": "application/json"},
                    )
            else:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "URL for OpenAPI specifications is invalid",
                        }
                    ),
                    400,
                    {"ContentType": "application/json"},
                )
        elif config["automaticImportFile"] != "":
            if not openAPI.get_openapi(config, specs=config["automaticImportFile"]):
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "The OpenAPI specifications are invalid",
                        }
                    ),
                    400,
                    {"ContentType": "application/json"},
                )
            else:
                config.pop("automaticImportURL")

    config["state"] = "Incomplete"
    config.pop("automaticImportFile")
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


@application_config.route("/api/application/", methods=["GET"])
def get_application_configs(internal: bool = False) -> tuple | list:
    """Returns the configurations for all the applications in teh database

    This function gets all the configs and returns it as an JSON object.

    :param internal: bool to change return from Flask to python dict
    :return: JSON with all the configs
    """
    applications = []
    if collection.find({}):
        for item in collection.find({}).sort("name"):
            applications.append(
                {
                    "id": str(item["_id"]),
                    "name": item["name"],
                    "version": item["version"],
                    "description": item["description"],
                    "state": item["state"],
                }
            )
    if internal:
        return applications
    else:
        return (
            jsonify({"success": True, "applications": applications}),
            200,
            {"ContentType": "application/json"},
        )


@application_config.route("/api/application/<application_id>", methods=["GET"])
def get_application_config(application_id: str, internal: bool = False) -> tuple | dict:
    """Returns the application config for a specific application

    This function gets the application config form the database and returns it as an JSON object.
    :param internal: bool to change return from Flask to python dict
    :param application_id: id of application in string format
    :return: An JSON object containing the config of the application
    """
    application_id = ObjectId(application_id)
    config = collection.find_one({"_id": application_id})
    if config:
        config["id"] = str(config["_id"])
        config.pop("_id")
        if internal:
            return config
        else:
            return (
                jsonify({"success": True, "config": config}),
                200,
                {"ContentType": "application/json"},
            )
    else:
        print("Application not found, id:" + str(application_id))
        return {}


@application_config.route("/api/application/save/<application_id>", methods=["POST"])
def update_application_config(application_id: str, config: dict = None, check_sdk: bool = True) -> tuple:
    """Returns the application id after updating the application with a given config

    This function updates a application config with the given config. The config can be either given by function call
    or as an POST request. It also validates the automaticImport of the OpenAPI doc
    :param check_sdk: bool to override the automatic sdk check
    :param application_id: id of application in string format
    :param config: the new configuration that needs to be saved
    :return: an JSON object if the update was successful, and the application id for future reference
    """
    application_id = ObjectId(application_id)
    if config is None:
        config = request.get_json()
    if "id" in config:
        config.pop("id")
    if "automaticImportFile" in config:
        if config["automaticImportFile"] != "":
            state = openAPI.get_openapi(config, specs=config["automaticImportFile"])
            if state:
                config.pop("automaticImportFile")
            else:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "OpenAPI specifications file is invalid",
                        }
                    ),
                    400,
                    {"ContentType": "application/json"},
                )
    if "automaticImportURL" in config:
        if config["automaticImportURL"] != "":
            if validators.url(config["automaticImportURL"]):
                if not openAPI.get_openapi(config, url=config["automaticImportURL"]):
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "The OpenAPI specifications are invalid",
                            }
                        ),
                        400,
                        {"ContentType": "application/json"},
                    )
            else:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "URL for OpenAPI specifications is invalid",
                        }
                    ),
                    400,
                    {"ContentType": "application/json"},
                )
    updated = collection.update_one({"_id": application_id}, {"$set": config})
    if updated.acknowledged:
        set_state(application_id)
        if check_sdk:
            set_sdk(application_id)
        return (
            jsonify({"success": True, "id": str(application_id)}),
            200,
            {"ContentType": "application/json"},
        )
    else:
        jsonify({"success": False, "message": "Updating application failed"}), 500, {
            "ContentType": "application/json"
        }


@application_config.route("/api/application/<application_id>", methods=["DELETE"])
def delete_application_config(application_id: str) -> tuple:
    """Returns teh result after deleting an application from the database

    This function deletes the given application.

    :param application_id: id of application in string format
    :return: an JSON object if removal of the application from the database was successful
    """
    config = get_application_config(application_id, internal=True)
    if "sdkGenerated" in config and config["sdkGenerated"]:
        if not clientSDK.delete_sdk(application_id):
            jsonify(
                {"success": False, "message": "Deleting application's SDK failed"}
            ), 500, {"ContentType": "application/json"}
    ConnectionConfig.delete_connections_with_application(application_id)
    application_id = ObjectId(application_id)
    deleted = collection.delete_one({"_id": application_id})
    if deleted.acknowledged:
        return jsonify({"success": True}), 200, {"ContentType": "application/json"}
    else:
        jsonify({"success": False, "message": "Deleting application failed"}), 500, {
            "ContentType": "application/json"
        }


@application_config.route(
    "/api/application/auth/save/<application_id>", methods=["POST"]
)
def save_application_auth(application_id: str) -> tuple:
    """Returns the application id after getting and saving the authentication type and configuration

    This function gets the authentication type and settings of an application and saves them.

    :param application_id: id of application in string format
    :return: an JSON object if saving of the auth was successful and the application id for future reference
    """
    application_id = ObjectId(application_id)
    auth_config = request.get_json()
    if auth_config["securityScheme"] == "BasicAuth":
        auth = collection.update_one(
            {"_id": application_id},
            [
                {
                    "$set": {
                        "securityScheme": auth_config["securityScheme"],
                        "basicUsername": auth_config["basicUsername"],
                        "basicPassword": auth_config["basicPassword"],
                    }
                },
                {"$unset": ["headerItems"]},
            ],
        )

    elif auth_config["securityScheme"] == "ApiKeyAuth":
        header_status, headers = array_to_dict(auth_config["headerItems"])
        if header_status:
            auth = collection.update_one(
                {"_id": application_id},
                [
                    {
                        "$set": {
                            "securityScheme": auth_config["securityScheme"],
                            "headerItems": headers,
                        }
                    },
                    {"$unset": ["basicUsername", "basicPassword"]},
                ],
            )
        else:
            return (
                jsonify({"success": False, "message": "Header keys need to be unique"}),
                400,
                {"ContentType": "application/json"},
            )

    else:  # non type
        auth = collection.update_one(
            {"_id": application_id},
            [
                {"$set": {"securityScheme": auth_config["securityScheme"]}},
                {"$unset": ["basicUsername", "basicPassword", "headerItems"]},
            ],
        )
    if auth.acknowledged:
        set_state(application_id)
        return (
            jsonify({"success": True, "id": str(application_id)}),
            200,
            {"ContentType": "application/json"},
        )
    else:
        return (
            jsonify({"success": False, "message": "Saving authentication failed"}),
            500,
            {"ContentType": "application/json"},
        )


@application_config.route(
    "/api/application/endpoint/crawl/<application_id>", methods=["POST"]
)
def crawl_application_endpoint(application_id: str) -> tuple:
    """Returns a response from teh crawled API endpoint

    This function safely crawls an API endpoint with the given operation, url and requestBody. If present in the
    application config, an authentication header or basic authentication object is added to the request.

    :param application_id: id of application in string format
    :return: an JSON object containing the endpoint's response or an error message
    """
    endpoint = request.get_json()
    headers, auth = get_auth(application_id)  # get authentication to crawl endpoint
    body = ""
    if validators.url(endpoint["url"]):
        try:
            if endpoint["operation"] == "get":
                valid, _ = openAPI.find_api_type(endpoint["url"])
                if not valid:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "API endpoint should be either JSON or XML",
                            }
                        ),
                        400,
                        {"ContentType": "application/json"},
                    )
            else:
                if endpoint["body"] != "":
                    try:
                        body = json.loads(endpoint["body"])
                    except ValueError:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "message": "Body needs to be valid json",
                                }
                            ),
                            400,
                            {"ContentType": "application/json"},
                        )
            response = requests.request(
                endpoint["operation"],
                endpoint["url"],
                timeout=3600,
                auth=auth,
                headers=headers,
                json=body,
            )
        except requests.exceptions.Timeout:
            return (
                jsonify({"success": False, "message": "Try again later"}),
                500,
                {"ContentType": "application/json"},
            )
        except requests.exceptions.TooManyRedirects:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Too many redirects try a different URL",
                    }
                ),
                500,
                {"ContentType": "application/json"},
            )
        except requests.exceptions.RequestException:
            return (
                jsonify({"success": False, "message": "Endpoint is not reachable"}),
                500,
                {"ContentType": "application/json"},
            )
        if response.text != "":
            try:
                response.json()
                return (
                    jsonify(
                        {
                            "success": True,
                            "response": response.json(),
                            "header": dict(response.headers),
                            "status": response.status_code,
                        }
                    ),
                    200,
                    {"ContentType": "application/json"},
                )
            except json.decoder.JSONDecodeError:
                return (
                    jsonify(
                        {
                            "success": True,
                            "response": response.text,
                            "header": dict(response.headers),
                            "status": response.status_code,
                        }
                    ),
                    200,
                    {"ContentType": "application/json"},
                )
        else:
            if response.ok:
                return (
                    jsonify(
                        {
                            "success": True,
                            "response": "The server responded correctly but with an empty response",
                            "header": dict(response.headers),
                            "status": response.status_code,
                        }
                    ),
                    200,
                    {"ContentType": "application/json"},
                )

    else:
        return (
            jsonify({"success": False, "message": "Endpoint URL is invalid"}),
            400,
            {"ContentType": "application/json"},
        )


@application_config.route(
    "/api/application/endpoint/spec/<application_id>", methods=["POST"]
)
def generate_spec(application_id: str) -> tuple:
    """Returns generated OpenAPI specs to show in the frontend Swagger UI

    This function generates specs on the fly for presentation in the frontend.
    These OpenAPI specs are generated but not SAVED.

    :param application_id: id of application in string format
    :return: JSON object with the specs or an error message
    """
    endpoints = request.get_json()
    config = get_application_config(application_id, internal=True)
    state = openAPI.generate_openapi(config, endpoints)
    if not state:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "There was an error during the parsing of endpoints",
                }
            ),
            500,
            {"ContentType": "application/json"},
        )
    else:
        return (
            jsonify({"success": True, "specs": config["specs"]}),
            200,
            {"ContentType": "application/json"},
        )


@application_config.route(
    "/api/application/endpoint/save/<application_id>", methods=["POST"]
)
def save_endpoints(application_id: str) -> tuple:
    """Returns success or an error when generating and saving an OpenAPI specs document

    This function generates the final OpenAPI spec document and saves it with the appropriate application.
    it gets the needed configuration as an POST request.

    :param application_id: id of application in string format
    :return: JSON object if the saving was successful
    """
    endpoints = request.get_json()
    config = get_application_config(application_id, internal=True)
    specs = openAPI.generate_openapi(config, endpoints)
    config["endpointsBackup"] = endpoints["endpoints"]
    if not specs:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "There was an error during the parsing of endpoints",
                }
            ),
            500,
            {"ContentType": "application/json"},
        )
    updated, _, _ = update_application_config(str(application_id), config)
    if updated.get_json()["success"]:
        return (
            jsonify({"success": True, "message": "saved"}),
            200,
            {"ContentType": "application/json"},
        )
    else:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "There was an error during the saving of the endpoints",
                }
            ),
            500,
            {"ContentType": "application/json"},
        )


@application_config.route(
    "/api/application/sdk/generate/<application_id>", methods=["GET"]
)
def generate_sdk(application_id: str) -> tuple:
    """Returns status after requesting, downloading and unzipping an application sdk

    This function is an api wrapper for clientSDK.generate_sdk. This function gets the config and calls the generate_sdk
    function, in order to generate, download and unzip a client SDK for tha application given in application_id.

    :param application_id: id of application in string format
    :return: bool if generation of the sdk was successful
    """
    config = get_application_config(application_id, internal=True)

    if "sdkGenerated" in config and config["sdkGenerated"]:
        if clientSDK.update_sdk(application_id):
            return (
                jsonify({"success": True, "message": "updated and saved"}),
                200,
                {"ContentType": "application/json"},
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "There was an error during the update of the client SDK",
                    }
                ),
                500,
                {"ContentType": "application/json"},
            )

    if clientSDK.generate_sdk(application_id):
        return (
            jsonify({"success": True, "message": "generated and saved"}),
            200,
            {"ContentType": "application/json"},
        )
    else:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "There was an error during the generation of the client SDK",
                }
            ),
            500,
            {"ContentType": "application/json"},
        )


@application_config.route(
    "/api/application/sdk/<application_id>", methods=["DELETE"]
)
def delete_sdk(application_id: str) -> tuple:
    """Returns status after deleting an application sdk

    This function is an api wrapper for clientSDK.delete_sdk. This function gets the config and calls the delete_sdk
    function, in order to delete a certain application's client SDK.

    :param application_id: id of application in string format
    :return: bool if deletion of the sdk was successful
    """
    if clientSDK.delete_sdk(application_id):
        return (
            jsonify({"success": True, "message": "SDK deleted"}),
            200,
            {"ContentType": "application/json"},
        )
    else:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "There was an error during the removal of the client SDK",
                }
            ),
            500,
            {"ContentType": "application/json"},
        )


@application_config.route(
    "/api/application/download/<application_id>", methods=["GET"]
)
def download_openapi(application_id: str) -> tuple:
    """ Function to serve the OpenAPI document

    This function serves as a download API for the OpenAPI document of a given application

    :param application_id: identifier of application
    :return: Flask response object either with application not found or the OpenAPI file as JSON body
    """
    config = get_application_config(application_id, internal=True)
    if "specs" in config:
        return (
            jsonify(config["specs"]),
            200,
            {"ContentType": "application/json"},
        )
    else:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "This application does not have a OpenAPI document",
                }
            ),
            400,
            {"ContentType": "application/json"},
        )
