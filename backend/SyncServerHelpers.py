import importlib
import re
import sys
import traceback
from copy import deepcopy

import pymongo
from bson import ObjectId

import ApplicationConfig
import ConnectionConfig
import ConnectionVariable
import SyncServer
import SyncServerDataHandler
import clientSDK

mongo_client = pymongo.MongoClient("mongodb://database:27017/")
db = mongo_client["APIMapping"]
collection = db["cache"]


def format_configs(connection_id):
    connection_config = ConnectionConfig.get_connection_config(
        connection_id, internal=True, flow=False
    )
    application_configs = {}
    for application_id in connection_config["applicationIds"]:
        application_configs[application_id] = ApplicationConfig.get_application_config(
            application_id, internal=True
        )
    return connection_config, application_configs


def convert_camelcase_to_snakecase(camelcase):
    return re.sub("(?!^)([A-Z]+)", r"_\1", camelcase).lower()


def handle_sdk_state(connection_config, application_configs):
    configs_need_refresh = False
    for application_id in connection_config["applicationIds"]:
        if not clientSDK.double_check_sdk(application_id):
            if not clientSDK.generate_sdk(application_id):
                SyncServer.sync_server_log.error(
                    "There is an error generating the SDK for this application: "
                    + application_configs[application_id]["name"]
                )
                SyncServer.stop_sync_server()
            else:
                SyncServer.sync_server_log.info(
                    "An SDK is generated for this application: "
                    + application_configs[application_id]["name"]
                )
                configs_need_refresh = True
        else:
            SyncServer.sync_server_log.info(
                "An SDK already existed for this application: "
                + application_configs[application_id]["name"]
            )
    return configs_need_refresh


def convert_parameters(parameterItems):
    converted_parameters = []
    for parameter in parameterItems:
        parameter["name"] = convert_camelcase_to_snakecase(parameter["name"])
        converted_parameters.append(parameter)
    return converted_parameters


def get_mapping_config(connection_config, application_configs):
    mapping_config = []
    for connection in connection_config["endpointMapping"]:
        if "complete" in connection and connection["complete"]:
            if connection["source"]["label"] != "Variables":
                SyncServer.sync_server_log.info(
                    "Found endpoint in application "
                    + application_configs[connection["source"]["applicationId"]]["name"]
                    + ", endpoint: "
                    + connection["source"]["path"]
                )
            else:
                SyncServer.sync_server_log.info(
                    "Using variables to provide data to the target API"
                )
            connection_copy = deepcopy(connection)
            for connection_end in ["source", "target"]:
                if "applicationId" in connection[connection_end]:
                    connection_copy[connection_end]["type"] = "function"
                    if connection[connection_end]["serverOverride"] != "":
                        connection_copy[connection_end]["url"] = (
                            connection[connection_end]["serverOverride"]
                            + connection[connection_end]["path"]
                        )
                    else:
                        try:
                            connection_copy[connection_end]["url"] = (
                                application_configs[
                                    connection[connection_end]["applicationId"]
                                ]["specs"]["servers"][0]["url"]
                                + connection[connection_end]["path"]
                            )
                        except KeyError:
                            SyncServer.sync_server_log.error(
                                "No server url defined in the OpenAPI servers section"
                            )
                            SyncServer.stop_sync_server()
                    if connection[connection_end]["parameterItems"]:
                        connection_copy[connection_end][
                            "parameterItems"
                        ] = convert_parameters(
                            connection[connection_end]["parameterItems"]
                        )
                    connection_copy[connection_end]["sdkId"] = application_configs[
                        connection[connection_end]["applicationId"]
                    ]["sdkId"]
                    connection_copy[connection_end][
                        "function"
                    ] = get_endpoint_function_name(
                        connection[connection_end]["path"],
                        connection[connection_end]["operation"],
                    )
                    connection_copy[connection_end].pop("path")
                    connection_copy[connection_end][
                        "apiInstanceConfig"
                    ] = generate_api_instance_configurations(
                        application_configs[connection[connection_end]["applicationId"]]
                    )
                elif connection[connection_end]["label"] == "Variables":
                    connection_copy[connection_end]["type"] = "variables"
            mapping_config.append(connection_copy)
        else:
            SyncServer.sync_server_log.info(
                "Found endpoint with an incomplete mapping in application "
                + application_configs[connection["source"]["applicationId"]]["name"]
                + ", endpoint: "
                + connection["source"]["path"]
                + " skipping this endpoint..."
            )
    # print(mapping_config)
    return mapping_config


def get_endpoint_function_name(endpoint_path, endpoint_operation):
    endpoint_function_name = endpoint_path
    endpoint_function_name = convert_camelcase_to_snakecase(
        endpoint_function_name
    )  # convert any CamelCase to snake_case
    endpoint_function_name = endpoint_function_name.replace("/", "_")
    endpoint_function_name = endpoint_function_name.replace(
        "{", ""
    )  # to filter for path variables
    endpoint_function_name = endpoint_function_name.replace(
        "}", ""
    )  # to filter for path variables
    if not endpoint_function_name.endswith("_"):
        endpoint_function_name += "_"
    endpoint_function_name += endpoint_operation
    if endpoint_function_name.startswith("_"):
        endpoint_function_name = endpoint_function_name[1:]
    if endpoint_function_name.endswith("_"):
        endpoint_function_name = endpoint_function_name[:1]
    return endpoint_function_name


def get_sdks_as_import(connection_config, application_configs):
    sdk = {}
    for application_id in connection_config["applicationIds"]:
        if (
            "sdkGenerated" in application_configs[application_id]
            and application_configs[application_id]["sdkGenerated"]
            and "sdkId" in application_configs[application_id]
            and application_configs[application_id]["sdkId"] != ""
        ):

            try:
                sys.path.append("generated_clients")
                sdk[
                    application_configs[application_id]["sdkId"]
                ] = importlib.import_module(
                    application_configs[application_id]["sdkId"] + ".apis"
                )
                SyncServer.sync_server_log.info(
                    "Imported SDK for: " + application_configs[application_id]["name"]
                )
            except ImportError as err:
                SyncServer.sync_server_log.error(
                    "Error while importing the SDk for this application "
                    + application_configs[application_id]["name"]
                )
                SyncServer.sync_server_log.error(err)
                SyncServer.stop_sync_server(emergency_stop=True)
                return False, ""
        else:
            SyncServer.sync_server_log.error(
                "Error while importing the SDk for this application "
                + application_configs[application_id]["name"]
            )
            SyncServer.sync_server_log.error("Please restart the sync server")
            SyncServer.stop_sync_server(emergency_stop=True)
            return False, ""
    return True, sdk


def generate_auth(application_config, api_object, config_object):
    if "headerItems" in application_config:
        for key, value in application_config["headerItems"].items():
            config_object.api_key[key] = value
    if "basicUsername" in application_config and "basicPassword" in application_config:
        config_object = api_object.Configuration(
            username=application_config["basicUsername"],
            password=application_config["basicPassword"],
        )
    return config_object


def generate_api_instance_configurations(application_config):
    if (
        "sdkGenerated" in application_config
        and application_config["sdkGenerated"]
        and "sdkId" in application_config
        and application_config["sdkId"] != ""
    ):
        try:
            sys.path.append("generated_clients")
            api_object = importlib.import_module(application_config["sdkId"])
            config_object = api_object.Configuration()
        except ImportError as e:
            SyncServer.sync_server_log.error(
                "Error while importing the config object for SDk for this application "
                + application_config["name"]
            )
            SyncServer.sync_server_log.error(e)
            SyncServer.stop_sync_server(emergency_stop=True)
            return False, ""
        config_object = generate_auth(application_config, api_object, config_object)
        return api_object.ApiClient(config_object)


def get_api_instance(current_sdk, endpoint, endpoint_end):
    try:
        return current_sdk.DefaultApi(endpoint[endpoint_end]["apiInstanceConfig"])
    except Exception as e:
        SyncServer.sync_server_log.error(
            "Error while importing SDK to call: "
            + endpoint[endpoint_end]["url"]
            + ", error:"
            + str(e)
        )
    SyncServer.stop_sync_server(emergency_stop=True)
    return


def find_call_type(connection_config, sdks, endpoint, polling_interval):
    if endpoint["source"]["type"] == "function":
        source_response = call_endpoint(connection_config, sdks, endpoint, "source")
    elif endpoint["source"]["type"] == "variables":
        source_response = ConnectionVariable.get_variables_for_glom(
            connection_config["id"]
        )
    elif endpoint["source"]["type"] == "script":
        print("TBD")
    else:
        SyncServer.sync_server_log.error(
            "Unknown type: either function or variable is allowed, given type:"
            + endpoint["source"]["type"]
        )
        SyncServer.stop_sync_server(emergency_stop=True)
        return
    if check_for_changes(source_response, endpoint, polling_interval):
        if (
            endpoint["target"]["type"] == "function"
            or endpoint["target"]["type"] == "script"
        ):
            target_response = call_endpoint(
                connection_config, sdks, endpoint, "target", source_response
            )
        elif endpoint["target"]["type"] == "variables":
            SyncServerDataHandler.set_variables(
                connection_config, endpoint, source_response
            )
        else:
            SyncServer.sync_server_log.error(
                "Unknown type: either function or variable is allowed, given type:"
                + endpoint["target"]["type"]
            )
            return


def call_endpoint(
    connection_config, sdks, endpoint, endpoint_end, source_response=None, reponse=None
):
    current_sdk = sdks[endpoint[endpoint_end]["sdkId"]]
    if endpoint_end == "source" or (
        endpoint_end == "target" and source_response is not None
    ):
        try:
            api_instance = get_api_instance(current_sdk, endpoint, endpoint_end)
            kwargs = SyncServerDataHandler.generate_calling_kwargs(
                api_instance, connection_config, endpoint, endpoint_end, source_response
            )
            if endpoint_end == "source":
                SyncServer.sync_server_log.info(
                    "Calling: "
                    + SyncServerDataHandler.get_url_with_parameters(
                        endpoint[endpoint_end]["url"], kwargs
                    )
                )
            else:
                SyncServer.sync_server_log.info(
                    "Sending data to: "
                    + SyncServerDataHandler.get_url_with_parameters(
                        endpoint["target"]["url"], kwargs
                    )
                )
            target_api = getattr(api_instance, endpoint[endpoint_end]["function"])
            if kwargs:
                # print("Using data: ", kwargs)
                try:
                    response = target_api(**kwargs)
                except Exception as e:
                    SyncServer.sync_server_log.error(
                        "Error while calling the following API endpoint: "
                        + endpoint[endpoint_end]["url"]
                    )
                    SyncServer.sync_server_log.error(e)
                    SyncServer.stop_sync_server(emergency_stop=True)
                    return
            else:
                try:
                    response = target_api()
                except Exception as e:
                    SyncServer.sync_server_log.error(
                        "Error while calling the following API endpoint: "
                        + endpoint[endpoint_end]["url"]
                    )
                    SyncServer.sync_server_log.error(e)
                    SyncServer.stop_sync_server()
                    return
            return handle_response(response)

        except Exception as e:
            SyncServer.sync_server_log.error(
                "Unknown error: " + endpoint[endpoint_end]["url"] + ", error:" + str(e)
            )
            SyncServer.sync_server_log.error(traceback.format_exc())
            SyncServer.stop_sync_server(emergency_stop=True)
            return
    else:
        SyncServer.sync_server_log.error(
            "Error while calling the following API endpoint: "
            + endpoint[endpoint_end]["url"]
        )
        SyncServer.sync_server_log.error(
            "Source response was not given but is required"
        )
        SyncServer.stop_sync_server(emergency_stop=True)
        return


def handle_response(response):
    if hasattr(response, "__dict__"):
        return SyncServerDataHandler.model_to_dict(response)
    if isinstance(response, list):
        return [SyncServerDataHandler.model_to_dict(item) for item in response]
    else:
        SyncServer.sync_server_log.error("Error while trying to parse the response")
        SyncServer.stop_sync_server(emergency_stop=True)


def check_for_changes(response, endpoint, polling_interval):
    if "cacheId" in endpoint:
        cache_id = ObjectId(endpoint["cacheId"])
        cached_result = collection.find_one({"_id": cache_id})
        cached_result.pop("_id")
        if cached_result["response"] == response:
            if endpoint["source"]["type"] == "function":
                SyncServer.sync_server_log.info(
                    "Nothing changed on endpoint: "
                    + endpoint["source"]["url"]
                    + ", waiting "
                    + str(polling_interval)
                    + " seconds to check again"
                )
            elif endpoint["source"]["type"] == "variables":
                SyncServer.sync_server_log.info(
                    "Values of variables did not change, waiting "
                    + str(polling_interval)
                    + " seconds to check again"
                )
            return False

        else:
            if endpoint["source"]["type"] == "function":
                SyncServer.sync_server_log.info(
                    "Changes found on endpoint: " + endpoint["source"]["url"]
                )
            elif endpoint["source"]["type"] == "variables":
                SyncServer.sync_server_log.info("Values of variables changed")
            updated = collection.update_one(
                {"_id": cache_id}, {"$set": {"data": response}}
            )
            if updated.acknowledged:
                return True
    else:
        if response is not None:
            insert = collection.insert_one({"response": response})
            if insert.acknowledged:
                endpoint["cacheId"] = insert.inserted_id
                return True
        else:
            return False


def empty_cache():
    state = collection.delete_many({})
    if not state.acknowledged:
        SyncServer.sync_server_log.error("Emptying cache failed")
