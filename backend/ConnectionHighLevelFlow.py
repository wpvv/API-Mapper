import json
import random

from flask import Blueprint, jsonify, request
from bson import objectid
import ConnectionConfig
import ConnectionLowLevelFlow
import ConnectionRecommendations

connection_high_level_flow = Blueprint(
    "ConnectionHighLevelFlow", __name__, template_folder="templates"
)


@connection_high_level_flow.route(
    "/api/connection/flow/<connection_id>", methods=["GET"]
)
def get_connection_config_flow(connection_id, internal=False):
    config = ConnectionConfig.get_connection_config(connection_id, internal=True, flow=True)
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
                                "serverOverride": "" if "servers" not in specs[application_id]["paths"][path][operation]
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
                                "serverOverride": "" if "servers" not in specs[application_id]["paths"][path][operation]
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
def get_node(application_id, node_data=None):
    if not node_data:
        node_data = request.get_json()
    output = {}
    specs = ConnectionConfig.get_application_specs(application_id)
    try:
        node_details = specs["paths"][node_data["path"]][
            node_data["operation"]
        ]
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


def connection_exists(connection_config, endpoint_config):
    if "endpointMapping" in connection_config and connection_config["endpointMapping"]:
        edge_index = next(
            (index for (index, value) in enumerate(connection_config["endpointMapping"]) if
             value["source"]["endpointId"] == endpoint_config["source"]["endpointId"] and
             value["target"]["endpointId"] == endpoint_config["target"]["endpointId"]),
            None)
        return edge_index is not None
    else:
        return False


@connection_high_level_flow.route(
    "/api/connection/flow/add/edge/<connection_id>", methods=["POST"]
)
def add_endpoint_connection(connection_id, endpoint_config=None, recommendation=False, internal=False):
    if not internal:
        endpoint_config = request.get_json()
    connection_config = ConnectionConfig.get_connection_config(connection_id, internal=True, flow=False)
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
                return jsonify({"success": True, "id": endpoint_config["id"]}), 200, {"ContentType": "application/json"}
            else:
                return jsonify(
                    {"success": False, "message": "Saving the new connection failed"}
                ), 500, {"ContentType": "application/json"}
    else:
        if internal:
            return None
        return jsonify(
            {"success": False, "message": "Connection already exists"}
        ), 400, {"ContentType": "application/json"}


@connection_high_level_flow.route(
    "/api/connection/flow/edge/<connection_id>/<edge_id>", methods=["DELETE"]
)
def delete_endpoint_connection(connection_id, edge_id):
    connection_config = ConnectionConfig.get_connection_config(connection_id, internal=True, flow=False)
    if "endpointMapping" in connection_config:
        edge_index = next(
            (index for (index, value) in enumerate(connection_config["endpointMapping"]) if value["id"] == edge_id),
            None)
        if edge_index is not None:
            connection_config["endpointMapping"].pop(edge_index)
            id = ConnectionConfig.update_connection_config(
                connection_id, connection_config, internal=True
            )
            if id:
                return jsonify({"success": True}), 200, {"ContentType": "application/json"}
            else:
                return jsonify(
                    {"success": False, "message": "Deleting this connection failed"}
                ), 500, {"ContentType": "application/json"}
    return jsonify(
        {"success": False, "message": "This connection was not found"}
    ), 500, {"ContentType": "application/json"}


def generate_node_connections_from_mapping(connection_id, nodes):
    edges = []
    mapping = get_endpoint_connections(connection_id)
    if mapping is not None:
        for connection in json.loads(mapping):
            source = target = -1
            for application in ["source", "target"]:
                if "label" in connection[application] and connection[application]["label"] == "Variables":
                    if ("operation" in connection["source"] and connection["source"]["operation"] == "get") or (
                            "operation" in connection["target"] and connection["target"]["operation"] == "get"):
                        target = 0
                    elif ("operation" in connection["target"] and connection["target"]["operation"] != "get") or (
                            "operation" in connection["source"] and connection["source"]["operation"] != "get"):
                        source = 0
                else:
                    for node in nodes:
                        if "path" in node["data"] and "operation" in node["data"]:
                            if "path" in connection[application] and "operation" in connection[application]:
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
                        "data": {"offset": random.randint(-5, 5) * 10, "recommendation": connection["recommendation"]},
                    }
                )
            else:
                print(
                    "Error in generate_node_connections_from_mapping(): either source or target could not be found")
    return edges


@connection_high_level_flow.route(
    "/api/connection/get/edges/<connection_id>", methods=["GET"]
)
def get_endpoint_connections(connection_id):
    connection_config = ConnectionConfig.get_connection_config(connection_id, internal=True, flow=False)
    if "endpointMapping" in connection_config:
        return json.dumps(connection_config["endpointMapping"])
    else:
        return None


@connection_high_level_flow.route(
    "/api/connection/save/<connection_id>",
    methods=["GET"],
)
def save_final_connection(connection_id):
    if ConnectionLowLevelFlow.save_mappings(connection_id):
        if ConnectionConfig.set_state(connection_id):
            config = ConnectionConfig.get_connection_config(connection_id, internal=True)
            if config["state"] == "Complete":
                return jsonify({"success": True, "state": "Complete"}), 200, {"ContentType": "application/json"}
            else:
                return jsonify({"success": True, "state": "Incomplete", "reason": config["state"],
                                "incompleteMappings": get_incomplete_APIs(connection_id)}), 200, {
                           "ContentType": "application/json"}
        else:
            print("Error in save_final_connection: status failed")
            return jsonify(
                {"success": False, "message": "Detecting and setting status failed"}
            ), 500, {"ContentType": "application/json"}

    else:
        print("Error in save_final_connection: saving mappings failed")
        return jsonify(
            {"success": False, "message": "Saving the low level mappings failed"}
        ), 500, {"ContentType": "application/json"}


@connection_high_level_flow.route(
    "/api/connection/recommendations/<connection_id>",
    methods=["GET"],
)
def get_recommendations(connection_id):
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
                "serverOverride": connection[application + "_server_override"]
            }
        if connection["application1_operation"] == "get":
            endpoint_config["source"] = endpoint_config.pop("application1")
            endpoint_config["target"] = endpoint_config.pop("application2")

        else:
            endpoint_config["source"] = endpoint_config.pop("application2")
            endpoint_config["target"] = endpoint_config.pop("application1")
        add_endpoint_connection(connection_id, endpoint_config=endpoint_config, recommendation=True, internal=True)
    print("Generated " + str(len(predictions)) + " recommendations")
    nodes, edges = get_connection_config_flow(connection_id, internal=True)
    return jsonify({"success": True, "data": {"nodes": nodes, "edges": edges}}), 200, {"ContentType": "application/json"}


def get_incomplete_APIs(connection_id):
    config = ConnectionConfig.get_connection_config(connection_id, internal=True)
    incomplete_mappings = []
    if "endpointMapping" in config and config["endpointMapping"]:
        for api in config["endpointMapping"]:
            if not api["complete"] and not api["recommendation"]:
                incomplete_name = ConnectionLowLevelFlow.generate_connection_name(api)
                incomplete_mappings.append(incomplete_name)
    return incomplete_mappings


@connection_high_level_flow.route(
    "/api/connection/test",
    methods=["GET"],
)
def test():
    ConnectionRecommendations.test()
    return jsonify({"success": True}), 200, {"ContentType": "application/json"}
