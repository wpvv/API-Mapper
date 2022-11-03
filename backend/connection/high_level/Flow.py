import random

from flask import jsonify, request, Blueprint

from backend.connection import ConnectionConfig
from backend.connection.high_level import DataHandler

connection_high_level_flow = Blueprint("ConnectionHighLevelFlow", __name__)


@connection_high_level_flow.route("/api/connection/flow/<connection_id>", methods=["GET"])
def get_connection_config_flow(connection_id: str, internal: bool = False) -> tuple:
    """Function to get the nodes and edges for the gih level flow editor

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
                                else specs[application_id]["paths"][path][operation][
                                    "servers"
                                ][0]["url"],
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
                                else specs[application_id]["paths"][path][operation][
                                    "servers"
                                ][0]["url"],
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
def get_node(
    application_id: str, node_data: dict = None, internal: bool = False
) -> tuple | dict | None:
    """Function to return all the information about a node in the mapping interface. A node being an API endpoint.

    :param application_id: unique identifier of a application configuration
    :param node_data: dict containing the path and operation of the requested API endpoint
    :param internal: bool to determine teh return type
    :return: a Flask response with all gathered information on the requested API endpoint
    """
    if not node_data:
        node_data = request.get_json()
    output = {}
    specs = ConnectionConfig.get_application_specs(application_id)
    try:
        node_details = specs["paths"][node_data["path"]][node_data["operation"]]
    except KeyError:
        if internal:
            return
        else:
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
    if internal:
        return output
    else:
        return (
            jsonify({"success": True, "data": output}),
            200,
            {"ContentType": "application/json"},
        )


def generate_node_connections_from_mapping(connection_id: str, nodes: list) -> list:
    """Function to generate React flow edges for API endpoint connections

    This function generates a list of edges to append to the base list of nodes and edges. This edge extension
    represents edges that are connections between API endpoints.

    :param connection_id: Unique identifier for the connection configuration between applications
    :param nodes: list of API endpoints as React flow Nodes
    :return: list of edges
    """
    edges = []
    mapping = DataHandler.get_endpoint_connections(connection_id, internal=True)
    if mapping is not None:
        for connection in mapping:
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
