from bson import objectid
from flask import jsonify, request, Blueprint

from backend.connection.low_level.StateHandler import generate_connection_name
from backend.connection.low_level.flow import Flow
from backend.connection.low_level.table import DataHandler as LowLevelTable

connection_low_level_flow_data_handler = Blueprint("ConnectionLowLevelFlowDataHandler", __name__)


def get_variable_nodes(variables: list) -> tuple[list, list]:
    """ Function to get all the nodes for the variables

    :param variables: list of all variables set by the user
    :return: a tuple of nodes representing the variables and edges to their parent
    """
    nodes = []
    edges = []
    parent_id = objectid.ObjectId()
    nodes.append(Flow.generate_parent_node(str(parent_id), "Variables", "variable"))
    for variable in variables:
        nodes.append(Flow.generate_node(variable, variable["name"], "variable"))
        edges.append(Flow.generate_edge(parent_id, variable["id"]))
    return nodes, edges


def get_target_nodes(
        application_name: str, parameters: list, schema_items: list
) -> tuple[list, list]:
    """ Function get to all targets that are part of the target API adn convert them to a list of nodes that need to
    be connected to complete the request schema of the target API or other data target

    :param application_name: user-friendly name of the application
    :param parameters: list of parameters that need to be satisfied
    :param schema_items: list of all schema items that are part of the targets request schema
    :return: a tuple of nodes of all targets and a list of edges between these nodes and their parent
    """
    nodes = []
    edges = []
    if parameters or schema_items:
        parent_id = str(objectid.ObjectId())
        nodes.append(Flow.generate_parent_node(parent_id, application_name, "target"))
        for parameter in parameters:
            nodes.append(
                Flow.generate_node(
                    parameter,
                    parameter["name"] + " (" + parameter["in"] + " parameter)",
                    "target",
                )
            )
            if "parent" not in parameter or not parameter["parent"]:
                edges.append(Flow.generate_edge(parameter["id"], parent_id))
        for endpoint in schema_items:
            nodes.append(Flow.generate_node(endpoint, endpoint["name"], "target"))
            if "parent" not in endpoint or not endpoint["parent"]:
                edges.append(Flow.generate_edge(endpoint["id"], parent_id))
    return nodes, edges


def get_source_target_nodes(
        application_name: str, parameters: list
) -> tuple[list, list]:
    """ Function to get all the targets that need to be satisfied in order to call the source API

    :param application_name: user-friendly name of the application
    :param parameters: list of parameters that need to be satisfied
    :return: a tuple with nodes of all source targets and the edges to their parent
    """
    nodes = []
    edges = []
    if parameters:
        parent_id = str(objectid.ObjectId())
        nodes.append(Flow.generate_parent_node(parent_id, application_name, "target"))
        for parameter in parameters:
            nodes.append(
                Flow.generate_node(
                    parameter,
                    parameter["name"] + " (" + parameter["in"] + " parameter)",
                    "target",
                )
            )
            if "parent" not in parameter or not parameter["parent"]:
                edges.append(Flow.generate_edge(parameter["id"], parent_id))
    return nodes, edges


def get_source_nodes(application_name: str, schema_items: list) -> tuple[list, list]:
    """ Function to get all the nodes that are part of teh source data endpoint

    :param application_name: user-friendly name of the application
    :param schema_items: list of all items that are in the source response data schema
    :return: a tuple with all the nodes that are data schema elements and edges to their parent
    """
    nodes = []
    edges = []
    if schema_items:
        parent_id = str(objectid.ObjectId())
        nodes.append(Flow.generate_parent_node(parent_id, application_name, "source"))
        for endpoint in schema_items:
            nodes.append(Flow.generate_node(endpoint, endpoint["name"], "source"))
            if "parent" not in endpoint or not endpoint["parent"]:
                edges.append(Flow.generate_edge(parent_id, endpoint["id"]))
    return nodes, edges


@connection_low_level_flow_data_handler.route(
    "/api/schemamapping/flow/<connection_id>/<mapping_id>",
    methods=["GET"],
)
def get_low_level_flow(connection_id: str, mapping_id: str) -> tuple:
    """ Function to get all nodes and edges for the low level flow interface

    :param connection_id: Unique identifier for the connection configuration between applications
    :param mapping_id: Unique identifier for the connection between data endpoints
    :return: a Flask response with all nodes and edges
    """
    schema_mapping_table_format, _, _ = LowLevelTable.get_schema_mapping(
        connection_id, mapping_id
    )
    if schema_mapping_table_format.get_json()["success"]:
        schema_mapping_table_format = schema_mapping_table_format.get_json()
        application_names = schema_mapping_table_format["applicationNames"]
        target_schema_items = schema_mapping_table_format["dataTargets"]
        source_schema_items = schema_mapping_table_format["dataSources"]
        target_parameters = schema_mapping_table_format["dataTargetParameters"]
        source_parameters = schema_mapping_table_format["dataSourceParameters"]
        variables = schema_mapping_table_format["dataVariables"]
        connections = schema_mapping_table_format["schemaConnections"]
        variable_nodes, variable_edges = get_variable_nodes(variables)
        target_nodes, target_edges = get_target_nodes(
            application_names[1], target_parameters, target_schema_items
        )
        source_target_nodes, source_target_edges = get_source_target_nodes(
            application_names[0], source_parameters
        )
        source_nodes, source_edges = get_source_nodes(
            application_names[0], source_schema_items
        )
        script_nodes = Flow.generate_script_nodes(connections)
        return (
            jsonify(
                {
                    "success": True,
                    "connectionName": generate_connection_name(
                        LowLevelTable.get_endpoint_mapping(connection_id, mapping_id)
                    ),
                    "targetNodes": target_nodes + source_target_nodes,
                    "targetEdges": target_edges + source_target_edges,
                    "sourceNodes": source_nodes,
                    "sourceEdges": source_edges,
                    "variableNodes": variable_nodes,
                    "variableEdges": variable_edges,
                    "scriptNodes": script_nodes,
                    "edges": Flow.convert_connections_to_flow_edges(
                        connections, script_nodes
                    ),
                }
            ),
            200,
            {"ContentType": "application/json"},
        )


@connection_low_level_flow_data_handler.route(
    "/api/schemamapping/flow/edge/<connection_id>/<mapping_id>", methods=["POST"]
)
def add_schema_mapping_connection(connection_id: str, mapping_id: str) -> tuple:
    """ Function to add a connection between data schema elements

    :param connection_id: Unique identifier for the connection configuration between applications
    :param mapping_id: Unique identifier for the connection between data endpoints
    :return: a Flask response with the message if creation was sucessful and the id of the new connection
    """
    schema_element_config = request.get_json()
    new_connection = {
        "id": str(objectid.ObjectId()),
        "target": schema_element_config["target"]["id"],
        "source": schema_element_config["source"]["id"],
        "type": "direct",
    }
    schema_config = LowLevelTable.get_endpoint_mapping(connection_id, mapping_id)
    if schema_config:
        if "schemaMapping" not in schema_config:
            schema_config["schemaMapping"] = []
        schema_config["schemaMapping"].append(new_connection)
        success = LowLevelTable.update_endpoint_mapping(
            connection_id, mapping_id, schema_config
        )
        if success:
            return (
                jsonify({"success": True, "id": new_connection["id"]}),
                200,
                {"ContentType": "application/json"},
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Saving the new schema mapping failed",
                    }
                ),
                500,
                {"ContentType": "application/json"},
            )
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


@connection_low_level_flow_data_handler.route(
    "/api/schemamapping/flow/edge/<connection_id>/<mapping_id>/<schema_mapping_id>",
    methods=["DELETE"],
)
def delete_schema_mapping_connection(
        connection_id: str, mapping_id: str, schema_mapping_id: str
) -> tuple:
    """ Function to delete a connection between data schema connections

    :param connection_id: Unique identifier for the connection configuration between applications
    :param mapping_id: Unique identifier for the connection between data endpoints
    :param schema_mapping_id: Unique identifier for the connection between data schema elements
    :return: a Flask response with the message if deletion was sucessful
    """
    schema_config = LowLevelTable.get_endpoint_mapping(connection_id, mapping_id)
    if "schemaMapping" in schema_config:
        schema_index = next(
            (
                index
                for (index, value) in enumerate(schema_config["schemaMapping"])
                if value["id"] == schema_mapping_id
            ),
            None,
        )
        if schema_index is not None:
            schema_config["schemaMapping"].pop(schema_index)
            success = LowLevelTable.update_endpoint_mapping(
                connection_id, mapping_id, schema_config
            )
            if success:
                return (
                    jsonify({"success": True}),
                    200,
                    {"ContentType": "application/json"},
                )
    return (
        jsonify({"success": False, "message": "Deleting the schema mapping failed"}),
        500,
        {"ContentType": "application/json"},
    )
