import jsonpickle
from copy import copy

from bson import objectid
from flask import Blueprint, jsonify, request
import json

import ConnectionVariable
import ConnectionHighLevelFlow
import ConnectionConfig
import DataTypeUtils
import MappingGenerator

connection_low_level_flow = Blueprint(
    "ConnectionLowLevelFlow", __name__, template_folder="templates"
)


def travers_nodes_helper(node, target):
    found_nodes = []

    def traverse_nodes(
            start_node, found_nodes, target, name="", in_element="", parent=None, in_array=False, required=[]
    ):
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
                        required=start_node["required"] if "required" in start_node else []
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
                    required=start_node["required"] if "required" in start_node else []
                )

    traverse_nodes(node, found_nodes, target)
    return found_nodes


def get_data_sources(source_application_id, node_data):
    sources = []
    (
        node,
        _,
        _,
    ) = ConnectionHighLevelFlow.get_node(source_application_id, node_data)
    if node.get_json()["success"]:
        node = node.get_json()["data"]
        if "responseSchema" in node:
            node = node["responseSchema"]
            sources.extend(travers_nodes_helper(node, False))
    return node, sources


def get_data_targets(target_application_id, node_data):
    targets = []
    (
        node,
        _,
        _,
    ) = ConnectionHighLevelFlow.get_node(target_application_id, node_data)
    if node.get_json()["success"]:
        node = node.get_json()["data"]
        if "requestSchema" in node and "type" in node["requestSchema"]:
            node = node["requestSchema"]
            if node["type"] != "object" and node["type"] != "array":
                targets.append({
                    "id": str(objectid.ObjectId()),
                    "name": "Entire endpoint",
                    "type": node["type"],
                    "parent": "",
                    "parentType": "",
                    "inArray": False,
                })
            else:
                targets.extend(travers_nodes_helper(node, True))
    return node, targets


def get_node_parameters(application_id, node_data):
    parameters = []
    (
        node,
        _,
        _,
    ) = ConnectionHighLevelFlow.get_node(application_id, node_data)
    if node.get_json()["success"]:
        node = node.get_json()["data"]
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
    return parameters


def get_target_and_source_names(schema_config):
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


def get_schema_connections(schema_config):
    if (
            "schemaMapping" in schema_config
            and schema_config["schemaMapping"]
    ):
        return schema_config["schemaMapping"]
    else:
        return []


def find_mapping_index(connection_config, mapping_id):
    return next(
        (
            index
            for (index, value) in enumerate(connection_config["endpointMapping"])
            if value["id"] == mapping_id
        ),
        None,
    )


def get_endpoint_mapping(connection_id, mapping_id):
    connection_config = ConnectionConfig.get_connection_config(connection_id, internal=True, flow=False)
    mapping_index = find_mapping_index(connection_config, mapping_id)
    if mapping_index is not None:
        return connection_config["endpointMapping"][mapping_index]
    else:
        print("Schema could not be found")
        return


def update_endpoint_mapping(connection_id, mapping_id, schema_config):
    connection_config = ConnectionConfig.get_connection_config(connection_id, internal=True, flow=False)
    mapping_index = find_mapping_index(connection_config, mapping_id)
    connection_config["endpointMapping"][mapping_index] = schema_config
    id = ConnectionConfig.update_connection_config(
        connection_id, connection_config, internal=True
    )
    if id:
        return True
    else:
        return False


def add_schema_mapping_endpoints(connection_id, mapping_id):
    schema_config = get_endpoint_mapping(connection_id, mapping_id)
    if schema_config:
        targets = target_schema = target_parameters = sources = source_schema = source_parameters = []
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
            return (
                jsonify(
                    {
                        "success": True,
                        "applicationNames": get_target_and_source_names(
                            schema_config
                        ),
                        "dataSources": sources,
                        "dataTargets": targets,
                        "dataVariables": variables,
                        "dataSourceParameters": source_parameters,
                        "dataTargetParameters": target_parameters,
                        "schemaConnections": schema_connection,
                    }
                ),
                200,
                {"ContentType": "application/json"},
            )
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


@connection_low_level_flow.route(
    "/api/schemamapping/table/<connection_id>/<mapping_id>",
    methods=["GET"],
)
def get_schema_mapping(connection_id, mapping_id):
    schema_config = get_endpoint_mapping(connection_id, mapping_id)
    if schema_config:
        if (
                "schemaItems" not in schema_config["source"]
                or "schemaItems" not in schema_config["target"]
        ):
            return add_schema_mapping_endpoints(connection_id, mapping_id)
        else:
            return (
                jsonify(
                    {
                        "success": True,
                        "applicationNames": get_target_and_source_names(
                            schema_config
                        ),
                        "dataSources": schema_config["source"]["schemaItems"],
                        "dataTargets": schema_config["target"]["schemaItems"],
                        "dataVariables": ConnectionVariable.get_variable_sources(
                            connection_id
                        ),
                        "dataSourceParameters": schema_config["source"]["parameterItems"],
                        "dataTargetParameters": schema_config["target"]["parameterItems"],
                        "schemaConnections": get_schema_connections(schema_config)
                    }
                ),
                200,
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


def reverse_position(position):
    if position == "left":
        return "right"
    elif position == "right":
        return "left"
    elif position == "top":
        return "bottom"
    else:
        return "top"


def get_position_from_type(type):
    if type == "source":
        return "right"
    elif type == "target":
        return "left"
    elif type == "variable":
        return "top"
    else:
        return "bottom"


def generate_parent_node(parent_id, label, type):
    node = {
        "id": parent_id,
        "data": {
            "label": label,
        },
        "position": {"x": 0, "y": 0},
        "connectable": False,
        "selectable": False,
    }
    if type == "target":
        node["type"] = "output"
        node["targetPosition"] = reverse_position(get_position_from_type(type))
    else:
        node["type"] = "input"
        node["sourcePosition"] = reverse_position(get_position_from_type(type))
    return node


def generate_group_node(data, type):
    node = {
        "id": data["id"],
        "data": {
            "type": data["type"],
            "label": data["name"],
            "required": False if "required" not in data else data["required"],
        },
        "position": {"x": 10, "y": 10},
        "type": "groupNode",
    }
    if "parent" in data and data["parent"]:
        node["parentNode"] = data["parent"]
        node["extent"] = "parent"
        node["data"]["child"] = True
    else:  # so only the outer parents gets connection hooks
        if type == "target":
            node["sourcePosition"] = get_position_from_type(type)
            node["targetPosition"] = reverse_position(get_position_from_type(type))
        else:
            node["sourcePosition"] = reverse_position(get_position_from_type(type))
            node["targetPosition"] = get_position_from_type(type)
        node["data"]["nodeType"] = "entire-" + type
    return node


def generate_node(data, label, type):
    if data["type"] == "array" or data["type"] == "object":
        return generate_group_node(data, type)
    else:
        node = {
            "id": data["id"],
            "data": {
                "label": label,
                "dataType": data["type"],
                "type": data["type"],
                "required": False if "required" not in data else data["required"],
                "child": False,
                "nodeType": type,
                "inArray": data["inArray"] if "inArray" in data else False
            },

            "selectable": False,
            "position": {"x": 10, "y": 10},
            "type": "targetNode",
        }
        if type == "target":
            if "parent" not in data or not data["parent"]:
                node["sourcePosition"] = get_position_from_type(type)
            node["targetPosition"] = reverse_position(get_position_from_type(type))
        else:
            node["sourcePosition"] = reverse_position(get_position_from_type(type))
            if "parent" not in data or not data["parent"]:
                node["targetPosition"] = get_position_from_type(type)
        if "value" in data:
            node["data"]["value"] = "value: " + str(data["value"])
        if "parent" in data and data["parent"]:
            node["parentNode"] = data["parent"]
            node["extent"] = "parent"
            node["data"]["child"] = True
        return node


def generate_edge(source_id, target_id):
    return {
        "id": "e" + str(source_id) + "-" + str(target_id),
        "source": str(source_id),
        "target": str(target_id),
        "type": "smoothstep",
    }


def get_variable_nodes(variables):
    nodes = []
    edges = []
    parent_id = str(objectid.ObjectId())
    nodes.append(generate_parent_node(parent_id, "Variables", "variable"))
    for variable in variables:
        nodes.append(generate_node(variable, variable["name"], "variable"))
        edges.append(generate_edge(parent_id, variable["id"]))
    return nodes, edges


def get_target_nodes(application_name, parameters, schema_items):
    nodes = []
    edges = []
    if parameters or schema_items:
        parent_id = str(objectid.ObjectId())
        nodes.append(generate_parent_node(parent_id, application_name, "target"))
        for parameter in parameters:
            nodes.append(
                generate_node(
                    parameter,
                    parameter["name"] + " (" + parameter["in"] + " parameter)",
                    "target",
                )
            )
            if "parent" not in parameter or not parameter["parent"]:
                edges.append(generate_edge(parameter["id"], parent_id))
        for endpoint in schema_items:
            nodes.append(generate_node(endpoint, endpoint["name"], "target"))
            if "parent" not in endpoint or not endpoint["parent"]:
                edges.append(generate_edge(endpoint["id"], parent_id))
    return nodes, edges


def get_source_target_nodes(application_name, parameters):
    nodes = []
    edges = []
    if parameters:
        parent_id = str(objectid.ObjectId())
        nodes.append(generate_parent_node(parent_id, application_name, "target"))
        for parameter in parameters:
            nodes.append(
                generate_node(
                    parameter,
                    parameter["name"] + " (" + parameter["in"] + " parameter)",
                    "target",
                )
            )
            if "parent" not in parameter or not parameter["parent"]:
                edges.append(generate_edge(parameter["id"], parent_id))
    return nodes, edges


def get_source_nodes(application_name, schema_items):
    nodes = []
    edges = []
    if schema_items:
        parent_id = str(objectid.ObjectId())
        nodes.append(generate_parent_node(parent_id, application_name, "source"))
        for endpoint in schema_items:
            nodes.append(generate_node(endpoint, endpoint["name"], "source"))
            if "parent" not in endpoint or not endpoint["parent"]:
                edges.append(generate_edge(parent_id, endpoint["id"]))
    return nodes, edges


def convert_connections_to_flow_edges(connections, script_nodes):
    flow_edges = []
    if connections:
        for connection in connections:
            if "type" in connection and connection["type"] == "direct":
                flow_edges.append(
                    {"id": connection["id"], "source": connection["source"], "target": connection["target"],
                     "type": "deleteEdge", "animated": True, "zIndex": 1})
            elif "type" in connection and connection["type"] == "script":
                script_node = [node for node in script_nodes if node["id"] == connection["id"]][0]
                flow_edges.append(
                    {"id": script_node["data"]["source"], "source": connection["source"], "target": connection["id"],
                     "type": "smoothstep", "animated": True, "zIndex": 1})
                flow_edges.append(
                    {"id": script_node["data"]["target"], "source": connection["id"], "target": connection["target"],
                     "type": "smoothstep", "animated": True, "zIndex": 1})
    return flow_edges


def generate_scripts(connections):
    script_nodes = []
    for connection in connections:
        if "type" in connection and connection["type"] == "script":
            script_nodes.append({
                "id": connection["id"],
                "data": {
                    "label": "Python Script Node",
                    "type": "script",
                    "source": str(objectid.ObjectId()),
                    "target": str(objectid.ObjectId()),
                },
                "type": "targetNode",
                "position": {
                    "x": connection["scriptPosition"]["x"] if "scriptPosition" in connection else 400,
                    "y": connection["scriptPosition"]["y"] if "scriptPosition" in connection else 400,
                },
                "targetPosition": "right",
                "sourcePosition": "left",
            })
    return script_nodes


@connection_low_level_flow.route(
    "/api/schemamapping/flow/<connection_id>/<mapping_id>",
    methods=["GET"],
)
def get_low_level_flow(connection_id, mapping_id):
    schema_mapping_table_format, _, _ = get_schema_mapping(connection_id, mapping_id)
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
        script_nodes = generate_scripts(connections)
        return (
            jsonify(
                {
                    "success": True,
                    "connectionName": generate_connection_name(get_endpoint_mapping(connection_id, mapping_id)),
                    "targetNodes": target_nodes + source_target_nodes,
                    "targetEdges": target_edges + source_target_edges,
                    "sourceNodes": source_nodes,
                    "sourceEdges": source_edges,
                    "variableNodes": variable_nodes,
                    "variableEdges": variable_edges,
                    "scriptNodes": script_nodes,
                    "edges": convert_connections_to_flow_edges(connections, script_nodes),
                }
            ),
            200,
            {"ContentType": "application/json"},
        )


@connection_low_level_flow.route(
    "/api/schemamapping/flow/edge/<connection_id>/<mapping_id>", methods=["POST"]
)
def add_schema_mapping_connection(connection_id, mapping_id):
    schema_element_config = request.get_json()
    new_connection = {
        "id": str(objectid.ObjectId()),
        "target": schema_element_config["target"]["id"],
        "source": schema_element_config["source"]["id"],
        "type": "direct",
    }
    schema_config = get_endpoint_mapping(connection_id, mapping_id)
    if schema_config:
        if "schemaMapping" not in schema_config:
            schema_config["schemaMapping"] = []
        schema_config["schemaMapping"].append(new_connection)
        success = update_endpoint_mapping(connection_id, mapping_id, schema_config)
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


@connection_low_level_flow.route(
    "/api/schemamapping/flow/edge/<connection_id>/<mapping_id>/<schema_mapping_id>",
    methods=["DELETE"],
)
def delete_schema_mapping_connection(connection_id, mapping_id, schema_mapping_id):
    schema_config = get_endpoint_mapping(connection_id, mapping_id)
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
            success = update_endpoint_mapping(connection_id, mapping_id, schema_config)
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


def check_parameter_state(schema_mapping):
    incomplete_parameter_items = []
    if "schemaMapping" in schema_mapping and schema_mapping["schemaMapping"]:
        for connection in ["source", "target"]:
            if "parameterItems" in schema_mapping[connection]:
                for parameter in schema_mapping[connection]["parameterItems"]:
                    if "required" in parameter and parameter["required"]:
                        index = next((i for i, item in enumerate(schema_mapping["schemaMapping"]) if
                                      item["source"] == parameter["id"] or item["target"] == parameter["id"]), None)
                        if index is None:
                            incomplete_parameter_items.append((parameter["name"], connection + " parameter"))
        if incomplete_parameter_items:
            return False, incomplete_parameter_items
        else:
            return True, []
    else:
        return False, []



def check_low_level_state(endpoint_mapping):
    incomplete_glom_items = []
    glom_complete = False
    if endpoint_mapping["type"] == "glom":
        glom_complete, incomplete_glom_items = MappingGenerator.check_glom_mapping_state(
            jsonpickle.decode(endpoint_mapping["glomMapping"]), True)
    parameter_complete, incomplete_parameter_items = check_parameter_state(endpoint_mapping)
    if (endpoint_mapping["type"] == "glom" and not glom_complete) or not parameter_complete:
        return False, incomplete_glom_items + incomplete_parameter_items
    else:
        return True, []


@connection_low_level_flow.route(
    "/api/schemamapping/flow/save/<connection_id>/<mapping_id>",
    methods=["GET"],
)
def save_mapping(connection_id, endpoint_mapping):
    endpoint_mapping = MappingGenerator.set_mapping_type(endpoint_mapping)
    if endpoint_mapping["type"] == "glom":
        glom_mapping = MappingGenerator.generate_glom_mapping(connection_id, endpoint_mapping)
        if glom_mapping:
            endpoint_mapping["glomMapping"] = jsonpickle.encode(glom_mapping)
            endpoint_mapping["complete"], endpoint_mapping["incompleteItems"] = check_low_level_state(endpoint_mapping)
            success = update_endpoint_mapping(connection_id, endpoint_mapping["id"], endpoint_mapping)
            return success
        else:
            endpoint_mapping["complete"] = False
            success = update_endpoint_mapping(connection_id, endpoint_mapping["id"], endpoint_mapping)
            return success
    else:
        endpoint_mapping["complete"], endpoint_mapping["incompleteItems"] = check_low_level_state(endpoint_mapping)
        success = update_endpoint_mapping(connection_id, endpoint_mapping["id"], endpoint_mapping)
        return success


def save_mappings(connection_id):
    connection_config = ConnectionConfig.get_connection_config(connection_id, internal=True, flow=False)
    if "endpointMapping" in connection_config and connection_config["endpointMapping"]:
        for endpoint_mapping in connection_config["endpointMapping"]:
            if not save_mapping(connection_id, endpoint_mapping):
                print("Error in save_mappings(): saving failed, mapping id: " + endpoint_mapping["id"])
    return True


def generate_connection_name(api):
    if "path" not in api["source"]:
        name = "Variables -> " + api["target"]["path"] + " (" + api["target"][
            "operation"] + ")"
    elif "path" not in api["target"]:
        name = api["source"]["path"] + " (" + api["source"][
            "operation"] + ") -> Variables"
    else:
        name = api["source"]["path"] + " (" + api["source"][
            "operation"] + ") -> " + api["target"]["path"] + " (" + api["target"][
                   "operation"] + ")"
    return name
