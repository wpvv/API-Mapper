import importlib
import io
import sys
import traceback
from datetime import date, datetime
from types import ModuleType

import jsonpickle
from glom import glom

from backend.connection import ConnectionVariable
from backend.connection.low_level import MappingGenerator
from backend.sync_server import SyncServer


def get_url_with_parameters(url: str, packed_parameters: dict) -> str:
    """ function to set an url with parameters with the values that it will be called with

    :param url: url with parameters in parentheses}
    :param packed_parameters: a dict with the parameter names and their values
    :return: an url where the parameters are replaced with their value
    """
    for key, value in packed_parameters.items():
        url = url.replace("{" + key + "}", str(value))
    return url


def search_id_in_schema(item_id: str, schema: dict) -> bool:
    """ Search for a data schema item based on its ID

    :param item_id: id of teh item that may or not be in the schema
    :param schema: schema to search in
    :return: bool if item is found in the schema
    """
    return next((item for item in schema if item["id"] == item_id), None) is not None


def get_schema_mapping(endpoint: dict, mapping_id: str) -> dict | None:
    """ Function to return the mapping for the target of a connection between APIs (Low Level)

    :param endpoint: current row of the list of connections that need to be synced
    :param mapping_id: id of the requested connection between APIs (mapping)
    :return: the config for that specific connection between APIs
    """
    return next(
        (
            mapping
            for mapping in endpoint["schemaMapping"]
            if mapping["target"] == mapping_id
        ),
        None,
    )


def get_parameter_value(
    connection_config: dict, endpoint: dict, data_target_id: str
) -> any:
    """ Function to determine where the value for a parameter is supposed to come from. The function will return the
    value if found

    :param connection_config: configuration of the connection between applications
    :param endpoint: current row of the list of connections that need to be synced
    :param data_target_id: id of the parameter, parameters are always targets, they do not provide data
    :return: value to set the parameter to
    """
    schema_mapping = get_schema_mapping(endpoint, data_target_id)
    if schema_mapping:
        data_source_id = schema_mapping["source"]
        if search_id_in_schema(data_source_id, endpoint["source"]["schemaItems"]):
            print("NEED FURTHER INVESTIGATION")
            return
        elif ConnectionVariable.search_in_variables(
            connection_config["id"], data_source_id
        ):
            element = ConnectionVariable.get_variable(
                connection_config["id"], data_source_id
            )
            return element["value"]
        else:
            SyncServer.sync_server_log.error(
                "Not able to get variable value to satisfy the parameter, parameter id:"
                + data_target_id
            )
            return
    else:
        raise LookupError("Schema mapping for parameter not found")


def generate_packed_path_parameters(
    connection_config: dict, endpoint: dict, endpoint_end: str
) -> dict:
    """ Function to pack parameters, basically a dict wth the name of the parameter as key, and its value as value

    :param connection_config: configuration of the connection between applications
    :param endpoint: current row of the list of connections that need to be synced
    :param endpoint_end: side of the connection the API instance is required of, target or source
    :return: a dict of packed parameters with key value combinations
    """
    packed_path_parameters = {}
    for parameter in endpoint[endpoint_end]["parameterItems"]:
        if "in" in parameter and parameter["in"] == "path":
            parameter_value = get_parameter_value(
                connection_config, endpoint, parameter["id"]
            )
            if parameter_value is not None:
                packed_path_parameters[parameter["name"]] = parameter_value
    return packed_path_parameters


def get_body_param_name(api_instance: object, endpoint: dict) -> list:
    """ Function to generate the name of the request body for the API, this is the main payload for an API with a
    request body. This name is extracted from the imported SDK and analysing the configuration for the specific API
    within the SDK

    :param api_instance: function of the generated SDK, this function represents an API
    :param endpoint: current row of the list of connections that need to be synced
    :return: a list of body items
    """
    target_model_name = endpoint["target"]["function"] + "_endpoint"
    target_model_params = api_instance.__dict__[target_model_name].location_map
    return [key for (key, value) in target_model_params.items() if value == "body"]


def generate_target_data(
    api_instance: ModuleType,
    endpoint: dict,
    source_response: any,
    connection_config: dict,
) -> dict:
    """ Function to pack the main payload, the request body, and the parameters to be used when the API gets called.
    It can generate data through Glom with a one-on-one mapping of data elements between the source and target.
    It can also call the connection script that the user added in the Low Level mapping interface

    :param api_instance:
    :param endpoint: current row of the list of connections that need to be synced
    :param source_response: response data from a source
    :param connection_config: configuration of the connection between applications
    :return: all data packed in a dict with the appropriate names as keys
    """
    packed_target_data = {}
    if endpoint["type"] == "glom":
        glom_mapping = jsonpickle.decode(endpoint["glomMapping"])
        try:
            target_data = glom(source_response, glom_mapping)
            packed_target_data[
                api_instance.users_post_endpoint.params_map["all"][0]
            ] = target_data
            return packed_target_data

        except Exception as e:
            SyncServer.sync_server_log.error(
                "Error while generating target data: endpoint id:"
                + endpoint["id"]
                + "error encountered: "
                + str(e)
            )
    elif endpoint["type"] == "script":
        schema_mapping_id = endpoint["target"]["schemaItems"][0]["id"]
        schema_mapping = get_schema_mapping(endpoint, schema_mapping_id)
        if schema_mapping and schema_mapping["type"] == "script":
            script_id = schema_mapping["id"]
            kwargs = generate_variables_as_kwargs(connection_config["id"])
            try:
                sys.path.append("../connection_scripts")
                script = importlib.import_module(script_id)
                try:
                    SyncServer.sync_server_log.info(
                        "Converting response with custom script"
                    )
                    target_data = script.main(source_response, **kwargs)
                    body_param_name = get_body_param_name(api_instance, endpoint)
                    if body_param_name:
                        packed_target_data[body_param_name[0]] = target_data
                        return packed_target_data
                except Exception as e:
                    SyncServer.sync_server_log.error(
                        "Error in added script, script id: "
                        + script_id
                        + ", error: "
                        + str(e)
                    )
                    SyncServer.sync_server_log.error(traceback.format_exc())
            except ImportError as e:
                SyncServer.sync_server_log.error(
                    "Error while generating target data with script id:"
                    + script_id
                    + "error encountered: "
                    + str(e)
                )
    else:
        raise ValueError(
            "Connection type is not supported, either glom or script is supported, given type:"
            + endpoint["type"]
        )


def generate_calling_kwargs(
    api_instance: ModuleType,
    connection_config: dict,
    endpoint: dict,
    endpoint_end: str,
    source_response: bool = None,
) -> dict:
    """ Function to convert packed parameter data and if needed body data to kwargs

    :param api_instance:
    :param connection_config: configuration of the connection between applications
    :param endpoint: current row of the list of connections that need to be synced
    :param endpoint_end: side of the connection the API instance is required of, target or source
    :param source_response: response data from a source
    :return: dict of kwargs as payload for the API
    """
    packed_path_parameters = generate_packed_path_parameters(
        connection_config, endpoint, endpoint_end
    )
    if source_response is not None:
        target_data = generate_target_data(
            api_instance, endpoint, source_response, connection_config
        )
        return dict(packed_path_parameters, **target_data)
    else:
        return packed_path_parameters


def generate_variables_as_kwargs(connection_id: str) -> dict:
    """ Generate a dict of all variables within the current application connection to be used in the Python script made
     by the user

    :param connection_id: a unique identifier of a connection between applications
    :return: a dict of variables, key is their name and value is the variables value with the correct typing
    """
    kwargs = {}
    variables = ConnectionVariable.get_variables(connection_id, internal=True)
    for variable in variables:
        kwargs[variable["name"]] = variable["value"]
    return kwargs


def set_variables(
    connection_config: dict, endpoint: dict, source_response: any
) -> None:
    """ Function to set variables whenever a variable is the target of a connection between APIs. This can be a direct
    connection meaning that a data element from the source API give the new value for the variable, or it can be a
    value that is generated with a source API and a script in between

    :param connection_config: configuration of the connection between applications
    :param endpoint: current row of the list of connections that need to be synced
    :param source_response: response data from a source
    :return: None
    """
    for schema_mapping in endpoint["schemaMapping"]:
        if ConnectionVariable.search_in_variables(
            connection_config["id"], schema_mapping["target"]
        ):
            if schema_mapping["type"] == "direct":
                data_location = MappingGenerator.find_schema_item(
                    connection_config["id"],
                    "source",
                    endpoint,
                    schema_mapping["source"],
                )
                if data_location == "schema":
                    found_path = MappingGenerator.find_path_in_json_schema(
                        endpoint["source"]["schema"], schema_mapping["source"]
                    )
                    if found_path:
                        found_path = found_path[0]
                    else:
                        print(endpoint["source"]["schema"], schema_mapping["source"])
                        return
                    # found_path = convert_camelcase_to_snakecase(found_path)
                    target_paths = found_path.split(".")
                    value = MappingGenerator.get_by_path(source_response, target_paths)
                    SyncServer.sync_server_log.info(
                        "Setting variable: "
                        + ConnectionVariable.get_variable(
                            connection_config["id"], schema_mapping["target"]
                        )["name"]
                        + " with the following value: "
                        + str(value)
                    )
                    if not ConnectionVariable.set_variable(
                        connection_config["id"], schema_mapping["target"], value
                    ):
                        SyncServer.sync_server_log.error(
                            "Error while trying to set value for a variable, variable: "
                            + ConnectionVariable.get_variable(
                                connection_config["id"], schema_mapping["target"]
                            )["name"]
                        )
                        SyncServer.stop_sync_server(emergency_stop=True)
                        return
            elif schema_mapping["type"] == "script":
                script_id = schema_mapping["id"]
                kwargs = generate_variables_as_kwargs(connection_config["id"])
                try:
                    sys.path.append("../connection_scripts")
                    script = importlib.import_module(script_id)
                    try:
                        SyncServer.sync_server_log.info(
                            "Converting response with custom script"
                        )
                        value = script.main(source_response, **kwargs)
                        SyncServer.sync_server_log.info(
                            "Setting variable: "
                            + ConnectionVariable.get_variable(
                                connection_config["id"], schema_mapping["target"]
                            )["name"]
                            + " with the following value: "
                            + str(value)
                        )
                        if not ConnectionVariable.set_variable(
                            connection_config["id"], schema_mapping["target"], value
                        ):
                            SyncServer.sync_server_log.error(
                                "Error while trying to set value for a variable, variable: "
                                + ConnectionVariable.get_variable(
                                    connection_config["id"], schema_mapping["target"]
                                )["name"]
                                + ", value: "
                                + str(value)
                            )
                            SyncServer.stop_sync_server(emergency_stop=True)
                            return
                    except Exception as e:
                        SyncServer.sync_server_log.error(
                            "Error in added script, script id: "
                            + script_id
                            + ", error: "
                            + str(e)
                        )
                        SyncServer.sync_server_log.error(traceback.format_exc())
                        return
                except ImportError as e:
                    SyncServer.sync_server_log.error(
                        "Error while generating target data with script id:"
                        + script_id
                        + "error encountered: "
                        + str(e)
                    )
                    return

            else:
                SyncServer.sync_server_log.error(
                    "Error while trying to set value for a variable, type of schema mapping is unknown, variable: "
                    + ConnectionVariable.get_variable(
                        connection_config["id"], schema_mapping["target"]
                    )["name"]
                )
                SyncServer.stop_sync_server(emergency_stop=True)
                return


def model_to_dict(model_instance: ModuleType, serialize: bool = True) -> dict:
    # This is an overload of the standard model_to_dict that is part of model_instance within a generated SDK.
    # This overload is needed because the standard implementation has "serialize" as standard to be False, which is
    # needed to be True for our purpose. The fact that the standard function is part of generated code makes this
    # overload necessary.

    """Returns the model properties as a dict

    Args:
        model_instance (one of your model instances): the model instance that
            will be converted to a dict.

    Keyword Args:
        serialize (bool): if True, the keys in the dict will be values from
            attribute_map
    """
    result = {}
    file_type = io.IOBase
    PRIMITIVE_TYPES = (list, float, int, bool, datetime, date, str, file_type)

    def extract_item(item):
        """

        :param item:
        :return:
        """
        return (
            (item[0], model_to_dict(item[1], serialize=serialize))
            if hasattr(item[1], "_data_store")
            else item
        )

    model_instances = [model_instance]
    if model_instance._composed_schemas:
        model_instances.extend(model_instance._composed_instances)
    seen_json_attribute_names = set()
    used_fallback_python_attribute_names = set()
    py_to_json_map = {}
    for model_instance in model_instances:
        for attr, value in model_instance._data_store.items():
            if serialize:
                # we use get here because additional property key names do not
                # exist in attribute_map
                try:
                    attr = model_instance.attribute_map[attr]
                    py_to_json_map.update(model_instance.attribute_map)
                    seen_json_attribute_names.add(attr)
                except KeyError:
                    used_fallback_python_attribute_names.add(attr)
            if isinstance(value, list):
                if not value:
                    # empty list or None
                    result[attr] = value
                else:
                    res = []
                    for v in value:
                        if isinstance(v, PRIMITIVE_TYPES) or v is None:
                            res.append(v)
                        # elif isinstance(v, ModelSimple):
                        #     res.append(v.value)
                        elif isinstance(v, dict):
                            res.append(dict(map(extract_item, v.items())))
                        else:
                            res.append(model_to_dict(v, serialize=serialize))
                    result[attr] = res
            elif isinstance(value, dict):
                result[attr] = dict(map(extract_item, value.items()))
            # elif isinstance(value, ModelSimple):
            #     result[attr] = value.value
            elif hasattr(value, "_data_store"):
                result[attr] = model_to_dict(value, serialize=serialize)
            else:
                result[attr] = value
    if serialize:
        for python_key in used_fallback_python_attribute_names:
            json_key = py_to_json_map.get(python_key)
            if json_key is None:
                continue
            if python_key == json_key:
                continue
            json_key_assigned_no_need_for_python_key = (
                json_key in seen_json_attribute_names
            )
            if json_key_assigned_no_need_for_python_key:
                del result[python_key]

    return result
