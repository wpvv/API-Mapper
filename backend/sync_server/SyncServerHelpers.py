import importlib
import re
import sys
import traceback
from copy import deepcopy
from types import ModuleType

from bson import ObjectId

from backend import db
from backend.application import ApplicationConfig, clientSDK
from backend.connection import ConnectionConfig, ConnectionVariable
from backend.sync_server import SyncServer, SyncServerDataHandler

collection = db["cache"]


def format_configs(connection_id: str) -> tuple[dict, dict]:
    """ Function to aggregate the connection config and application configs during a sync session

    :param connection_id: a unique identifier of a connection between applications
    :return: a tuple with the connection config and a dict with application configs with their id as key
    """
    connection_config = ConnectionConfig.get_connection_config(
        connection_id, internal=True, flow=False
    )
    application_configs = {}
    for application_id in connection_config["applicationIds"]:
        application_configs[application_id] = ApplicationConfig.get_application_config(
            application_id, internal=True
        )
    return connection_config, application_configs


def convert_camelcase_to_snakecase(camelcase: str) -> str:
    """ Function to convert camelcase to snakecase

    Snakecase is used in the generated SDKs so in case anything in the variables or OpenAPI document is in camelcase
    it will need to be converted.

    :param camelcase: string perhaps containing camelcase words
    :return: same string but with snakecase
    """
    return re.sub("(?!^)([A-Z]+)", r"_\1", camelcase).lower()


def handle_sdk_state(connection_config: dict, application_configs: dict) -> tuple[bool, bool]:
    """ Function to set the SDKs if needed

    This function checks the existence of SDKs for both applications. If one or both of them do not have a generated
    SDK it will call clientSDK to generate an SDK

    :param connection_config: configuration of the connection between applications
    :param application_configs: a dict with application configs with their id as key
    :return: if an SDK is generated this changes the config of that application so a refresh of the fetched application
    configs is needed, and a bool incase a error occurred
    """
    configs_need_refresh = False
    for application_id in connection_config["applicationIds"]:
        if not clientSDK.double_check_sdk(application_id):
            if not clientSDK.generate_sdk(application_id):
                SyncServer.sync_server_log.error(
                    "There is an error generating the SDK for this application: "
                    + application_configs[application_id]["name"]
                )
                return configs_need_refresh, True
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
    return configs_need_refresh, False


def convert_parameters(parameter_items: list) -> list:
    """ Function to convert any camelcase parameters to snakecase using convert_camelcase_to_snakecase()

    :param parameter_items: list of parameters that need to be converted
    :return: list of converted parameter items
    """
    converted_parameters = []
    for parameter in parameter_items:
        parameter["name"] = convert_camelcase_to_snakecase(parameter["name"])
        converted_parameters.append(parameter)
    return converted_parameters


def get_mapping_config(connection_config: dict, application_configs: dict) -> list:
    """ Function to extract needed information from the connection config and the application configs.
    This is needed to convert the configs to an easily loop-able list of connection with all needed information,
    instead of a config with the details and connections separately.

    :param connection_config: configuration of the connection between applications
    :param application_configs: a dict with application configs with their id as key
    :return: list of connections with details per list item
    """
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
                    ] = generate_sdk_instance_configurations(
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
    return mapping_config


def get_endpoint_function_name(endpoint_path: str, endpoint_operation: str) -> str:
    """ Function to generate the function name of an API in the generated SDK, this is based on the path and operation
    of that API.

    :param endpoint_path: path of the API
    :param endpoint_operation: operation of the API
    :return: the predicted function name within the generated SDk of a specific API
    """
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


def get_sdks_as_import(
    connection_config: dict, application_configs: dict
) -> tuple[bool, dict]:
    """ Function to import the SDKs and save them in easily passable variable

    :param connection_config: configuration of the connection between applications
    :param application_configs: a dict with application configs with their id as key
    :return: tuple, with a boolean if import was sucessful and a dict with the SDKs of the application with their id
    as keys
    """
    sdk = {}
    for application_id in connection_config["applicationIds"]:
        if (
            "sdkGenerated" in application_configs[application_id]
            and application_configs[application_id]["sdkGenerated"]
            and "sdkId" in application_configs[application_id]
            and application_configs[application_id]["sdkId"] != ""
        ):

            try:
                sys.path.append("../generated_clients")
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
                return False, {}
        else:
            SyncServer.sync_server_log.error(
                "Error while importing the SDk for this application "
                + application_configs[application_id]["name"]
            )
            SyncServer.sync_server_log.error("Please restart the sync server")
            SyncServer.stop_sync_server(emergency_stop=True)
            return False, {}
    return True, sdk


def generate_auth(
    application_config: dict, sdk_object: ModuleType, config_object: ModuleType
):
    """ Function to add either header items or basic auth to the sdk_object, which as an
    instance of the imported SDK

    :param application_config: a dict containing the config of the application
    :param sdk_object: an instance of an
    :param config_object: a config within an imported SDK
    :return:
    """
    if "headerItems" in application_config:
        for key, value in application_config["headerItems"].items():
            config_object.api_key[key] = value
    if "basicUsername" in application_config and "basicPassword" in application_config:
        config_object = sdk_object.Configuration(
            username=application_config["basicUsername"],
            password=application_config["basicPassword"],
        )
    return config_object


def generate_sdk_instance_configurations(application_config: dict) -> ModuleType | None:
    """ Function to import the SDKs configuration object

    :param application_config: a dict containing the config of the application
    :return: config object for an SDK
    """
    if (
        "sdkGenerated" in application_config
        and application_config["sdkGenerated"]
        and "sdkId" in application_config
        and application_config["sdkId"] != ""
    ):
        try:
            sys.path.append("../generated_clients")
            sdk_object = importlib.import_module(application_config["sdkId"])
            config_object = sdk_object.Configuration()
        except ImportError as e:
            SyncServer.sync_server_log.error(
                "Error while importing the config object for SDk for this application "
                + application_config["name"]
            )
            SyncServer.sync_server_log.error(e)
            SyncServer.stop_sync_server(emergency_stop=True)
            return
        config_object = generate_auth(application_config, sdk_object, config_object)
        return sdk_object.ApiClient(config_object)


def get_api_instance(
    current_sdk: ModuleType, endpoint: dict, endpoint_end: str
) -> ModuleType | None:
    """ Function to get a specific API within the imported SDKs

    :param current_sdk: a single SDK out of dict with the imported SDKs for both applications
    :param endpoint: current row of the list of connections that need to be synced
    :param endpoint_end: side of the connection the API instance is required of, target or source
    :return: return the SDK API as a function
    """
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


def find_call_type(
    connection_config: dict, sdks: dict, endpoint: dict, polling_interval: int
) -> None:
    """ Function to determine the type of connection bot target and source can be of type: function, variable or script.
    Each different type requires a different handling

    :param connection_config: configuration of the connection between applications
    :param sdks: dict with the imported SDKs for both applications
    :param endpoint: current row of the list of connections that need to be synced
    :param polling_interval: integer of the interval between sync runs
    :return: None
    """
    if endpoint["source"]["type"] == "function":
        source_response = call_endpoint(connection_config, sdks, endpoint, "source")
    elif endpoint["source"]["type"] == "variables":
        source_response = ConnectionVariable.get_variables_for_glom(
            connection_config["id"]
        )
    elif endpoint["source"]["type"] == "script":
        print("TBD")
        return
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
            SyncServer.sync_server_log.info(target_response)
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
    connection_config: dict,
    sdks: dict,
    endpoint: dict,
    endpoint_end: str,
    source_response: any = None,
) -> any:
    """ Function to call a function that represents an API in the SDK

    It calls this function which will call the actual API. The function is called with a dict of kwargs which are the
    schemas and parameters

    :param connection_config: configuration of the connection between applications
    :param sdks: dict with the imported SDKs for both applications
    :param endpoint: current row of the list of connections that need to be synced
    :param endpoint_end: side of the connection the API instance is required of, target or source
    :param source_response: response data from a source
    :return: a handled version of the response from the API
    """
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


def handle_response(response: any) -> any:
    """ Function to format the response from the SDK

    Depending on the type the response needs to be processed in a different manner

    :param response: response data from a source
    :return:
    """
    if hasattr(response, "__dict__"):
        return SyncServerDataHandler.model_to_dict(response)
    if isinstance(response, list):
        return [SyncServerDataHandler.model_to_dict(item) for item in response]
    else:
        SyncServer.sync_server_log.error("Error while trying to parse the response")
        SyncServer.stop_sync_server(emergency_stop=True)


def check_for_changes(response: any, endpoint: dict, polling_interval: int) -> bool:
    """ Function to check the response of a source, it checks with the cache that has been saved in the cache document
    in the DB

    :param response: response data from a source
    :param endpoint: row of the list of connections that need to be synced
    :param polling_interval: integer of time between sync runs
    :return: bool if changes were detected
    """
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


def empty_cache() -> None:
    """ Function to empty the entire cache document in the DB"""
    state = collection.delete_many({})
    if not state.acknowledged:
        SyncServer.sync_server_log.error("Emptying cache failed")
