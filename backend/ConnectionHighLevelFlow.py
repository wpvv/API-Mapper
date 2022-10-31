import json
import random

from bson import objectid
from flask import Blueprint, jsonify, request

import ConnectionConfig
import ConnectionLowLevelFlow
import ConnectionRecommendations

connection_high_level_flow = Blueprint(
    "ConnectionHighLevelFlow", __name__, template_folder="templates"
)


@connection_high_level_flow.route(
    "/api/connection/flow/<connection_id>", methods=["GET"]
)
def get_connection_config_flow(connection_id: str, internal: bool = False) -> tuple:
    """ Function to get the nodes and edges for the gih level flow editor

    This function generates a list of nodes and edges, the list of nodes includes the parent of the edges. The parent
    represents the application whereas the children represent the APIs. The edges between parent and its children
    represents the APIs being part of the application. The nodes and edges are already in line with data schema
    that React flow demands. At the end edges generated from mappings between APIs are appended.

    :param connection_id: Unique identifier for the connection configuration between applications
    :param internal: boolean to indicate return type
    :return: either a flask response with the nodes and edges, or a tuple with the list of nodes and the list of edges
    """
    config = ConnectionConfig.get_connection_config(
        connection_id, internal=True, flow=True
    )
    nodes = []
    edges = []
    specs = {}
    for application_id in config["applicationIds"]:
        specs[application_id] = ConnectionConfig.get_application_specs(application_id)
    nodes.append(
        {
            "id": "0",  # Add set variable node, shown in the editor as node in the middle
            "data": {
                "label": "Variables",
            },
            "position": {"x": 300, "y": 0},
            "type": "input",
            "targetPosition": "bottom",
        }
    )
    node_id = 1
    for application_id in config["applicationIds"]:
        endpoint_id = 1
        parent_id = node_id
        nodes.append(
            {
                "id": str(
                    node_id
                ),  # Add parent node, shown in the editor as application node
                "data": {
                    "label": config[application_id],
                    "applicationId": application_id,
                },
                "position": {"x": 1 if parent_id == 1 else 600, "y": 0},
                "type": "input" if parent_id == 1 else "output",
                "targetPosition": "bottom" if parent_id != 1 else "",
                "connectable": False,
                "selectable": False,
            }
        )
        node_id += 1
        for path in specs[application_id]["paths"]:
            for operation in specs[application_id]["paths"][path]:
                if parent_id == 1:
                    nodes.append(
                        {
                            "id": str(node_id),
                            "data": {
                                "label": path,
                                "path": path,
                                "operation": operation,
                                "applicationId": application_id,
                                "endpointId": endpoint_id,
                                "serverOverride": ""
                                if "servers"
                                   not in specs[application_id]["paths"][path][operation]
                                else specs[application_id]["paths"][path][operation]["servers"][0]["url"],
                            },
                            "parentNode": str(parent_id),
                            "position": {"x": 100, "y": (node_id - parent_id) * 75},
                            "sourcePosition": "left",
                            "targetPosition": "right",
                            "extend": "parent",
                            "selectable": False,
                            "type": "highLevelNode",
                        }
                    )

                    edges.append(
                        {
                            "id": "e" + str(parent_id) + "-" + str(node_id),
                            "source": str(parent_id),
                            "target": str(node_id),
                            "type": "smoothstep",
                        }
                    )
                else:
                    nodes.append(
                        {
                            "id": str(node_id),
                            "data": {
                                "label": path,
                                "path": path,
                                "operation": operation,
                                "applicationId": application_id,
                                "endpointId": endpoint_id,
                                "serverOverride": ""
                                if "servers"
                                   not in specs[application_id]["paths"][path][operation]
                                else specs[application_id]["paths"][path][operation]["servers"][0]["url"],
                            },
                            "parentNode": str(parent_id),
                            "position": {"x": -100, "y": (node_id - parent_id) * 75},
                            "sourcePosition": "left",
                            "targetPosition": "right",
                            "extend": "parent",
                            "selectable": False,
                            "type": "highLevelNode",
                        }
                    )

                    edges.append(
                        {
                            "id": "e" + str(node_id) + "-" + str(parent_id),
                            "source": str(node_id),
                            "target": str(parent_id),
                            "type": "smoothstep",
                        }
                    )
                endpoint_id += 1
                node_id += 1
    edges.extend(generate_node_connections_from_mapping(connection_id, nodes))
    if internal:
        return nodes, edges
    else:
        return (
            jsonify({"success": True, "data": {"nodes": nodes, "edges": edges}}),
            200,
            {"ContentType": "application/json"},
        )


@connection_high_level_flow.route(
    "/api/connection/flow/get/node/<application_id>", methods=["POST"]
)
def get_node(application_id: str, node_data: dict = None) -> tuple:
    """ Function to return all the information about a node in the mapping interface. A node being an API endpoint.

    :param application_id: unique identifier of a application configuration
    :param node_data: dict containing the path and operation of the requested API endpoint
    :return: a Flask response with all gathered information on the requested API endpoint
    """
    if not node_data:
        node_data = request.get_json()
    output = {}
    specs = ConnectionConfig.get_application_specs(application_id)
    try:
        node_details = specs["paths"][node_data["path"]][node_data["operation"]]
    except KeyError:
        return (
            jsonify({"success": False, "message": "Finding this node failed"}),
            500,
            {"ContentType": "application/json"},
        )
    output["application"] = ConnectionConfig.get_application_name(application_id)
    output["path"] = node_data["path"]
    output["operation"] = node_data["operation"]
    if "summary" in node_details:
        output["summary"] = node_details["summary"]
    if "description" in node_details:
        output["description"] = node_details["description"]
    if "description" not in node_details and "summary" not in node_details:
        output["description"] = "No description or summary provided"
    if "200" in node_details["responses"]:
        for key, value in node_details["responses"]["200"]["content"].items():
            if "/" in key:
                output["responseSchema"] = value["schema"]
    elif "201" in node_details["responses"]:
        for key, value in node_details["responses"]["201"]["content"].items():
            if "/" in key:
                output["responseSchema"] = value["schema"]
    if "requestBody" in node_details and node_details["requestBody"]:
        for key, value in node_details["requestBody"]["content"].items():
            if "/" in key:
                output["requestSchema"] = value["schema"]
    if "parameters" in node_details and node_details["parameters"]:
        output["parameters"] = node_details["parameters"]
    return (
        jsonify({"success": True, "data": output}),
        200,
        {"ContentType": "application/json"},
    )


def connection_exists(connection_config: dict, endpoint_config: dict) -> bool:
    """ Function to check if a connection between API endpoints already exists

    :param connection_config: dict containing all the information about a connection between applications
    :param endpoint_config: dict containing data for the connection that is requested
    :return: boolean if API endpoint connection exists
    """
    if "endpointMapping" in connection_config and connection_config["endpointMapping"]:
        edge_index = next(
            (
                index
                for (index, value) in enumerate(connection_config["endpointMapping"])
                if value["source"]["endpointId"] == endpoint_config["source"]["endpointId"]
                   and
                   value["target"]["endpointId"] == endpoint_config["target"]["endpointId"]
            ),
            None,
        )
        return edge_index is not None
    else:
        return False


@connection_high_level_flow.route(
    "/api/connection/flow/add/edge/<connection_id>", methods=["POST"]
)
def add_endpoint_connection(
        connection_id: str, endpoint_config: dict = None, recommendation: bool = False, internal: bool = False
) -> bool | tuple:
    """ Function to add an API connection

    This connection is added to the configuration for the connection between applications

    :param connection_id: Unique identifier for the connection configuration between applications
    :param endpoint_config: information on the requested API endpoint connection
    :param recommendation: if the connection is generated as a recommendation
    :param internal: boolean to indicate the return type
    :return: either a success boolean or a Flask response with the success state
    """
    if not internal:
        endpoint_config = request.get_json()
    connection_config = ConnectionConfig.get_connection_config(
        connection_id, internal=True, flow=False
    )
    if not connection_exists(connection_config, endpoint_config):
        endpoint_config["id"] = str(objectid.ObjectId())
        endpoint_config["recommendation"] = recommendation
        if "endpointMapping" not in connection_config:
            connection_config["endpointMapping"] = []
            connection_config.pop("state")
        connection_config["endpointMapping"].append(endpoint_config)
        updated = ConnectionConfig.update_connection_config(
            connection_id, connection_config, internal=True
        )
        if internal:
            return updated
        else:
            if updated:
                return (
                    jsonify({"success": True, "id": endpoint_config["id"]}),
                    200,
                    {"ContentType": "application/json"},
                )
            else:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Saving the new connection failed",
                        }
                    ),
                    500,
                    {"ContentType": "application/json"},
                )
    else:
        if internal:
            return False
        return (
            jsonify({"success": False, "message": "Connection already exists"}),
            400,
            {"ContentType": "application/json"},
        )


@connection_high_level_flow.route(
    "/api/connection/flow/edge/<connection_id>/<edge_id>", methods=["DELETE"]
)
def delete_endpoint_connection(connection_id: str, edge_id: str) -> tuple:
    """ Function to delete a connection between API endpoints

    :param connection_id: Unique identifier for the connection configuration between applications
    :param edge_id: unique identifier of the API endpoint connection that needs to be deleted
    :return: Flask response with indication of successful deletion
    """
    connection_config = ConnectionConfig.get_connection_config(
        connection_id, internal=True, flow=False
    )
    if "endpointMapping" in connection_config:
        edge_index = next(
            (
                index
                for (index, value) in enumerate(connection_config["endpointMapping"])
                if value["id"] == edge_id
            ),
            None,
        )
        if edge_index is not None:
            connection_config["endpointMapping"].pop(edge_index)
            updated = ConnectionConfig.update_connection_config(
                connection_id, connection_config, internal=True
            )
            if updated:
                return (
                    jsonify({"success": True}),
                    200,
                    {"ContentType": "application/json"},
                )
            else:
                return (
                    jsonify(
                        {"success": False, "message": "Deleting this connection failed"}
                    ),
                    500,
                    {"ContentType": "application/json"},
                )
    return (
        jsonify({"success": False, "message": "This connection was not found"}),
        500,
        {"ContentType": "application/json"},
    )


def generate_node_connections_from_mapping(connection_id: str, nodes: list) -> list:
    """ Function to generate React flow edges for API endpoint connections

    This function generates a list of edges to append to the base list of nodes and edges. This edge extension
    represents edges that are connections between API endpoints.

    :param connection_id: Unique identifier for the connection configuration between applications
    :param nodes: list of API endpoints as React flow Nodes
    :return: list of edges
    """
    edges = []
    mapping = get_endpoint_connections(connection_id)
    if mapping is not None:
        for connection in json.loads(mapping):
            source = target = -1
            for application in ["source", "target"]:
                if (
                        "label" in connection[application]
                        and connection[application]["label"] == "Variables"
                ):
                    if (
                            "operation" in connection["source"]
                            and connection["source"]["operation"] == "get"
                    ) or (
                            "operation" in connection["target"]
                            and connection["target"]["operation"] == "get"
                    ):
                        target = 0
                    elif (
                            "operation" in connection["target"]
                            and connection["target"]["operation"] != "get"
                    ) or (
                            "operation" in connection["source"]
                            and connection["source"]["operation"] != "get"
                    ):
                        source = 0
                else:
                    for node in nodes:
                        if "path" in node["data"] and "operation" in node["data"]:
                            if (
                                    "path" in connection[application]
                                    and "operation" in connection[application]
                            ):
                                if (
                                        node["data"]["path"]
                                        == connection[application]["path"]
                                        and node["data"]["operation"]
                                        == connection[application]["operation"]
                                ):
                                    if node["data"]["operation"] == "get":
                                        source = node["id"]
                                    else:
                                        target = node["id"]
            if source != -1 and target != -1:
                edges.append(
                    {
                        "id": connection["id"],
                        "source": str(source),
                        "target": str(target),
                        "animated": True,
                        "type": "editEdge",
                        "data": {
                            "offset": random.randint(-5, 5) * 10,
                            "recommendation": connection["recommendation"],
                        },
                    }
                )
            else:
                print(
                    "Error in generate_node_connections_from_mapping(): either source or target could not be found"
                )
    return edges


@connection_high_level_flow.route(
    "/api/connection/get/edges/<connection_id>", methods=["GET"]
)
def get_endpoint_connections(connection_id: str) -> str:
    """ Function to get a list of connections between API endpoints

    :param connection_id: Unique identifier for the connection configuration between applications
    :return: a list of connections between API endpoints
    """
    connection_config = ConnectionConfig.get_connection_config(
        connection_id, internal=True, flow=False
    )
    if "endpointMapping" in connection_config:
        return json.dumps(connection_config["endpointMapping"])
    else:
        return ""


@connection_high_level_flow.route(
    "/api/connection/save/<connection_id>",
    methods=["GET"],
)
def save_final_connection(connection_id: str) -> tuple:
    """ Function to "save" all the mapping and return any incomplete mappings.

    Function that sets the state of the connection between the applications. It does not save it because a mapping is
    already saved upon creation. This function does check all mappings for completion and sets its state.

    :param connection_id: Unique identifier for the connection configuration between applications
    :return: a Flask response with the result of the checks
    """
    if ConnectionLowLevelFlow.save_mappings(connection_id):
        if ConnectionConfig.set_state(connection_id):
            config = ConnectionConfig.get_connection_config(
                connection_id, internal=True
            )
            if config["state"] == "Complete":
                return (
                    jsonify({"success": True, "state": "Complete"}),
                    200,
                    {"ContentType": "application/json"},
                )
            else:
                return (
                    jsonify(
                        {
                            "success": True,
                            "state": "Incomplete",
                            "reason": config["state"],
                            "incompleteMappings": get_incomplete_APIs(connection_id),
                        }
                    ),
                    200,
                    {"ContentType": "application/json"},
                )
        else:
            print("Error in save_final_connection: status failed")
            return (
                jsonify(
                    {"success": False, "message": "Detecting and setting status failed"}
                ),
                500,
                {"ContentType": "application/json"},
            )

    else:
        print("Error in save_final_connection: saving mappings failed")
        return (
            jsonify(
                {"success": False, "message": "Saving the low level mappings failed"}
            ),
            500,
            {"ContentType": "application/json"},
        )


@connection_high_level_flow.route(
    "/api/connection/recommendations/<connection_id>",
    methods=["GET"],
)
def get_recommendations(connection_id: str) -> tuple:
    """ Function to make the High level interface interact with the recommendations module.

    This function is called when the user presses the "Get recommendations" button in the high level interface.
    It will use the recommendations module to generate recommended connections APIs. Generated recommendations are then
    converted to a list of endpoint connections with the correct source and target, depending on the operation of the
    endpoints.

    :param connection_id: Unique identifier for the connection configuration between applications
    :return: a Flask response with the nodes and edges after the new recommended connections (edges) have been added
    """
    config = ConnectionConfig.get_connection_config(connection_id, internal=True)
    predictions = ConnectionRecommendations.make_prediction(config["applicationIds"])
    for connection in predictions:
        endpoint_config = {}
        for application in ["application1", "application2"]:
            endpoint_config[application] = {
                "applicationId": connection[application + "_id"],
                "endpointId": connection[application + "_endpoint_id"],
                "label": connection[application + "_original_path"],
                "operation": connection[application + "_operation"],
                "path": connection[application + "_original_path"],
                "serverOverride": connection[application + "_server_override"],
            }
        if connection["application1_operation"] == "get":
            endpoint_config["source"] = endpoint_config.pop("application1")
            endpoint_config["target"] = endpoint_config.pop("application2")

        else:
            endpoint_config["source"] = endpoint_config.pop("application2")
            endpoint_config["target"] = endpoint_config.pop("application1")
        add_endpoint_connection(
            connection_id,
            endpoint_config=endpoint_config,
            recommendation=True,
            internal=True,
        )
    print("Generated " + str(len(predictions)) + " recommendations")
    nodes, edges = get_connection_config_flow(connection_id, internal=True)
    return (
        jsonify({"success": True, "data": {"nodes": nodes, "edges": edges}}),
        200,
        {"ContentType": "application/json"},
    )


def get_incomplete_APIs(connection_id: str) -> list:
    """ Function to return a list of all the API connections that are incomplete.

    :param connection_id: Unique identifier for the connection configuration between applications
    :return: a list with the generate name for the connection of 2 API endpoints
    """
    config = ConnectionConfig.get_connection_config(connection_id, internal=True)
    incomplete_mappings = []
    if "endpointMapping" in config and config["endpointMapping"]:
        for api in config["endpointMapping"]:
            if not api["complete"] and not api["recommendation"]:
                incomplete_name = ConnectionLowLevelFlow.generate_connection_name(api)
                incomplete_mappings.append(incomplete_name)
    return incomplete_mappings
