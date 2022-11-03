from copy import copy

from bson import objectid
from flask import jsonify, Blueprint

from backend.connection import ConnectionConfig, ConnectionVariable, DataTypeUtils
from backend.connection.high_level import Flow as HighLevelFlow

connection_low_level_table_data_handler = Blueprint("ConnectionLowLevelTableDataHandler", __name__)


def traverse_nodes_helper(schema: dict, target: bool) -> list:
    """(Helper) Function to traverse through a JSON data schema

    This helper function is meant to execute the traverse_nodes() function and return its results


    :param schema: Dictionary of the JSON data schema
    :param target: Boolean if the data schema is prepared for a target API
    :return: list of elements in the schema
    """
    found_nodes = []

    def traverse_nodes(
        start_node: dict,
        found_nodes: list,
        target: bool,
        name: str = "",
        in_element: str = "",
        parent: dict = None,
        in_array: bool = False,
        required: list = [],
    ):
        """Function to recursively traverse through a JSON data schema

        This function processes an entire JSON schema and converts it to a list of nodes. Whereas nodes are a schema
        element. So this function basically dissects a nested data schema into individual elements for the React flow
        frontend.

        :param start_node: Schema or remains of the schema that needs to be converted
        :param found_nodes: list of data schema elements that are found so far
        :param target: boolean if the data schema is for a target API
        :param name: Name of the current element, needed because of recursion
        :param in_element: context about in which type of element the nested processes is
        :param parent: full reference to a parent if the data schema is nested
        :param in_array: special bool if the function is nested in an array
        :param required: bool if the current element is marked required in the schema
        """
        if "oneOf" not in start_node and "anyOf" not in start_node:
            node_type = start_node["type"] if "type" in start_node else "null"
            node = {
                "id": str(objectid.ObjectId()),
                "name": start_node["type"] if not name else name,
                "type": node_type,
                "parent": "" if not in_element else parent["id"],
                "parentType": "" if not in_element else in_element,
                "inArray": in_array,
            }
            node["required"] = True if target and node["name"] in required else False
            found_nodes.append(node)
            start_node["id"] = node["id"]

            if node_type == "object" and "properties" in start_node:
                for item in start_node["properties"].keys():
                    traverse_nodes(
                        start_node["properties"][item],
                        found_nodes,
                        target,
                        name=item,
                        in_element="object",
                        parent=node,
                        in_array=in_array,
                        required=start_node["required"]
                        if "required" in start_node
                        else [],
                    )
            elif node_type == "array" and "items" in start_node:
                traverse_nodes(
                    start_node["items"],
                    found_nodes,
                    target,
                    name="array-item",
                    in_element="array",
                    parent=node,
                    in_array=True,
                    required=start_node["required"] if "required" in start_node else [],
                )

    traverse_nodes(schema, found_nodes, target)
    return found_nodes


def get_data_sources(source_application_id: str, node_data: dict) -> tuple[dict, list]:
    """Function to get all data schema elements as nodes for a source API

    :param source_application_id: application identifier of the source API
    :param node_data: OpenAPI section of the API which has the responseSchema section
    :return: a tuple of the API as a node and a list of sources from the data schema
    """
    sources = []
    node = HighLevelFlow.get_node(source_application_id, node_data, internal=True)
    if node:
        if "responseSchema" in node:
            node = node["responseSchema"]
            sources.extend(traverse_nodes_helper(node, False))
    return node, sources


def get_data_targets(target_application_id: str, node_data: dict) -> tuple[dict, list]:
    """Function to get all data schema elements as nodes for a target API

    :param target_application_id:  application identifier of the target API
    :param node_data: OpenAPI section of the API which has the requestSchema
    :return: a tuple of the API as a node, and a list of all targets from the data schema
    """
    targets = []
    node = HighLevelFlow.get_node(target_application_id, node_data, internal=True)
    if node:
        if "requestSchema" in node and "type" in node["requestSchema"]:
            node = node["requestSchema"]
            if node["type"] != "object" and node["type"] != "array":
                targets.append(
                    {
                        "id": str(objectid.ObjectId()),
                        "name": "Entire endpoint",
                        "type": node["type"],
                        "parent": "",
                        "parentType": "",
                        "inArray": False,
                    }
                )
            else:
                targets.extend(traverse_nodes_helper(node, True))
    return node, targets


def get_node_parameters(application_id: str, node_data: dict) -> list:
    """Function to process all parameters in an API in its OpenAPI specs

    This function converts the parameters section of an API in the OpenAPI specs to a list of parameters

    :param application_id: unique identifier of an application
    :param node_data: OpenAPI section of the API which has the parameters
    :return: a list of parameters
    """
    parameters = []
    node = HighLevelFlow.get_node(application_id, node_data, internal=True)
    if node:
        if "parameters" in node:
            for parameter in node["parameters"]:
                if (
                    "schema" in parameter
                    and "type" in parameter["schema"]
                    and "name" in parameter
                ):
                    data_type = DataTypeUtils.convert_openapi_to_json(
                        parameter["schema"]["type"]
                    )
                    parameters.append(
                        {
                            "id": str(objectid.ObjectId()),
                            "name": parameter["name"],
                            "type": data_type,
                            "in": parameter["in"],
                            "required": True
                            if "required" in parameter and parameter["required"]
                            else False,
                        }
                    )
                else:
                    print(
                        "Error in ConnectionLowLevelFlow.get_node_parameters(), no type or name found for parameter:"
                        + parameter
                    )
                    return []
    return parameters


def get_target_and_source_names(schema_config: dict) -> list:
    """Function to get the names of the source and target application

    :param schema_config: configuration for the low level flow
    :return: a list with 0 being source application name and 1 target application name
    """
    source = target = ""
    if "applicationId" in schema_config["source"]:
        source = ConnectionConfig.get_application_name(
            schema_config["source"]["applicationId"]
        )
    if "applicationId" in schema_config["target"]:
        target = ConnectionConfig.get_application_name(
            schema_config["target"]["applicationId"]
        )
    return [source, target]


def get_schema_connections(schema_config: dict) -> list:
    """Function to return all existing connection across source and target schemas

    :param schema_config: configuration of the low level flow
    :return: a list of existing connections
    """
    if "schemaMapping" in schema_config and schema_config["schemaMapping"]:
        return schema_config["schemaMapping"]
    else:
        return []


def find_mapping_index(connection_config: dict, mapping_id: str) -> int | None:
    """Function to get the index of a specific connection (mapping) between data schemas in the list of existing
     connections

    :param connection_config: dict containing all the information about a connection between applications
    :param mapping_id: Unique identifier for the connection between data schema items
    :return:
    """
    return next(
        (
            index
            for (index, value) in enumerate(connection_config["endpointMapping"])
            if value["id"] == mapping_id
        ),
        None,
    )


def get_endpoint_mapping(connection_id: str, mapping_id: str) -> dict | None:
    """Function to get a specific connection (mapping) between data schemas

    :param connection_id: Unique identifier for the connection configuration between applications
    :param mapping_id: Unique identifier for the connection between data schema items
    :return: dictionary containing the mapping
    """
    connection_config = ConnectionConfig.get_connection_config(
        connection_id, internal=True, flow=False
    )
    mapping_index = find_mapping_index(connection_config, mapping_id)
    if mapping_index is not None:
        return connection_config["endpointMapping"][mapping_index]
    else:
        print("Schema could not be found")
        return


def update_endpoint_mapping(
    connection_id: str, mapping_id: str, schema_config: dict
) -> bool:
    """Function to update a specific connection (mapping) between data schemas

    This function basically overwrites the existing mapping (schema_config) with the given one.

    :param connection_id: Unique identifier for the connection configuration between applications
    :param mapping_id: Unique identifier for the connection between data schema items
    :param schema_config: New configuration for a existing connection between data schema items
    :return: boolean if updating in DB was sucessful
    """
    connection_config = ConnectionConfig.get_connection_config(
        connection_id, internal=True, flow=False
    )
    mapping_index = find_mapping_index(connection_config, mapping_id)
    connection_config["endpointMapping"][mapping_index] = schema_config
    updated = ConnectionConfig.update_connection_config(
        connection_id, connection_config, internal=True
    )
    if updated:
        return True
    else:
        return False


def add_schema_mapping_endpoints(
    connection_id: str, mapping_id: str, internal: bool = False
) -> tuple | dict:
    """Function to generate all the nodes in a Low Level flow.

    This function generates the following items: target nodes, target parameters, source nodes and source targets.
    It also collects the following things: variables and application names. It also sets the connection type to normal
    if the connection was made as a recommendation.

    :param connection_id: Unique identifier for the connection configuration between applications
    :param mapping_id: Unique identifier for the connection between data schema items
    :param internal: indicator to determine return type
    :return: Flask response with all the generated data
    """
    schema_config = get_endpoint_mapping(connection_id, mapping_id)
    if schema_config:
        targets = (
            target_schema
        ) = target_parameters = sources = source_schema = source_parameters = []
        if "applicationId" in schema_config["source"]:
            source_schema, sources = get_data_sources(
                schema_config["source"]["applicationId"],
                copy(schema_config["source"]),
            )
            source_parameters = get_node_parameters(
                schema_config["source"]["applicationId"],
                copy(schema_config["source"]),
            )
        if "applicationId" in schema_config["target"]:
            target_schema, targets = get_data_targets(
                schema_config["target"]["applicationId"],
                copy(schema_config["target"]),
            )
            target_parameters = get_node_parameters(
                schema_config["target"]["applicationId"],
                copy(schema_config["target"]),
            )
        variables = ConnectionVariable.get_variable_sources(connection_id)

        schema_connection = get_schema_connections(schema_config)

        schema_config["target"]["schemaItems"] = targets
        schema_config["target"]["schema"] = target_schema
        schema_config["target"]["parameterItems"] = target_parameters
        schema_config["source"]["schemaItems"] = sources
        schema_config["source"]["schema"] = source_schema
        schema_config["source"]["parameterItems"] = source_parameters
        if "recommendation" in schema_config and schema_config["recommendation"]:
            schema_config["recommendation"] = False
        success = update_endpoint_mapping(connection_id, mapping_id, schema_config)
        if success:
            output = {
                "success": True,
                "applicationNames": get_target_and_source_names(schema_config),
                "dataSources": sources,
                "dataTargets": targets,
                "dataVariables": variables,
                "dataSourceParameters": source_parameters,
                "dataTargetParameters": target_parameters,
                "schemaConnections": schema_connection,
            }
            if internal:
                return output
            else:
                return (
                    jsonify(output),
                    200,
                    {"ContentType": "application/json"},
                )
    else:
        if internal:
            return {}
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "An unknown error occurred while looking for data targets and sources",
                    }
                ),
                500,
                {"ContentType": "application/json"},
            )


@connection_low_level_table_data_handler.route(
    "/api/schemamapping/table/<connection_id>/<mapping_id>",
    methods=["GET"],
)
def get_schema_mapping(
    connection_id: str, mapping_id: str, internal: bool = False
) -> tuple | dict:
    """Function to get al nodes and connections for a low level connection in table format

    :param connection_id: Unique identifier for the connection configuration between applications
    :param mapping_id: Unique identifier for the connection between data schema items
    :param internal: indicator te determine the return type
    :return: a Flask response with all nodes and connections
    """
    schema_config = get_endpoint_mapping(connection_id, mapping_id)
    if schema_config:
        if (
            "schemaItems" not in schema_config["source"]
            or "schemaItems" not in schema_config["target"]
        ):
            return add_schema_mapping_endpoints(
                connection_id, mapping_id, internal=internal
            )
        else:
            output = {
                "success": True,
                "applicationNames": get_target_and_source_names(schema_config),
                "dataSources": schema_config["source"]["schemaItems"],
                "dataTargets": schema_config["target"]["schemaItems"],
                "dataVariables": ConnectionVariable.get_variable_sources(connection_id),
                "dataSourceParameters": schema_config["source"]["parameterItems"],
                "dataTargetParameters": schema_config["target"]["parameterItems"],
                "schemaConnections": get_schema_connections(schema_config),
            }
            if internal:
                return output
            return (
                jsonify(output),
                200,
                {"ContentType": "application/json"},
            )
    else:
        if internal:
            return {}
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "An error occurred while looking for the low level mapping details",
                    }
                ),
                500,
                {"ContentType": "application/json"},
            )
