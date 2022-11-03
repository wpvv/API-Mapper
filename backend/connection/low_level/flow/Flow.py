from bson import objectid


def reverse_position(position: str) -> str:
    """Function to reverse the position of a node handle

    :param position: Original position
    :return: reversed position
    """
    if position == "left":
        return "right"
    elif position == "right":
        return "left"
    elif position == "top":
        return "bottom"
    else:
        return "top"


def get_position_from_type(node_type: str) -> str:
    """Function to get the position of the node handle depending on the node type

    :param node_type: type of node
    :return: position of the handle of the node
    """
    if node_type == "source":
        return "right"
    elif node_type == "target":
        return "left"
    elif node_type == "variable":
        return "top"
    else:
        return "bottom"


def generate_parent_node(parent_id: str, label: str, node_type: str) -> dict:
    """Function to generate a parent node, a parent being the node that represents the application that the
    API is part of

    :param parent_id: unique identifier to assign to the node
    :param label: name of the node
    :param node_type: type of node, source, target and variable
    :return: dict in line with react flow nodes
    """
    node = {
        "id": parent_id,
        "data": {
            "label": label,
        },
        "position": {"x": 0, "y": 0},
        "connectable": False,
        "selectable": False,
    }
    if node_type == "target":
        node["type"] = "output"
        node["targetPosition"] = reverse_position(get_position_from_type(node_type))
    else:
        node["type"] = "input"
        node["sourcePosition"] = reverse_position(get_position_from_type(node_type))
    return node


def generate_group_node(data: dict, node_type: str) -> dict:
    """ Function to generate a node that can hold nodes within it, some types as array and dicts can have nested
    data types

    :param data: dict with all information on the node as id, name and type
    :param node_type: type of node, source, target and variable
    :return: dict in line with react flow nodes
    """
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
        if node_type == "target":
            node["sourcePosition"] = get_position_from_type(node_type)
            node["targetPosition"] = reverse_position(get_position_from_type(node_type))
        else:
            node["sourcePosition"] = reverse_position(get_position_from_type(node_type))
            node["targetPosition"] = get_position_from_type(node_type)
        node["data"]["nodeType"] = "entire-" + node_type
    return node


def generate_node(data: dict, label: str, node_type: str) -> dict:
    """ Function to generate a node that represents a data element from a JSON schema

    :param data: dict with all information on the node as id, name and type
    :param label: name of the nade
    :param node_type: type of node, source, target and variable
    :return: dict in line with react flow nodes
    """
    if data["type"] == "array" or data["type"] == "object":
        return generate_group_node(data, node_type)
    else:
        node = {
            "id": data["id"],
            "data": {
                "label": label,
                "dataType": data["type"],
                "type": data["type"],
                "required": False if "required" not in data else data["required"],
                "child": False,
                "nodeType": node_type,
                "inArray": data["inArray"] if "inArray" in data else False,
            },
            "selectable": False,
            "position": {"x": 10, "y": 10},
            "type": "targetNode",
        }
        if node_type == "target":
            if "parent" not in data or not data["parent"]:
                node["sourcePosition"] = get_position_from_type(node_type)
            node["targetPosition"] = reverse_position(get_position_from_type(node_type))
        else:
            node["sourcePosition"] = reverse_position(get_position_from_type(node_type))
            if "parent" not in data or not data["parent"]:
                node["targetPosition"] = get_position_from_type(node_type)
        if "value" in data:
            node["data"]["value"] = "value: " + str(data["value"])
        if "parent" in data and data["parent"]:
            node["parentNode"] = data["parent"]
            node["extent"] = "parent"
            node["data"]["child"] = True
        return node


def generate_edge(source_id: objectid, target_id: objectid) -> dict:
    """ Function to generate an edge between nodes

    :param source_id: identifier of the source node
    :param target_id: identifier of the target node
    :return: a dict depicting a React Flow edge
    """
    return {
        "id": "e" + str(source_id) + "-" + str(target_id),
        "source": str(source_id),
        "target": str(target_id),
        "type": "smoothstep",
    }


def generate_script_nodes(connections: list) -> list:
    """ Function to generate a node for the custom python scripts that the user has added between APIs

    :param connections: a list of all connections between the source, target and variables
    :return: a list of nodes for the script(s)
    """
    script_nodes = []
    for connection in connections:
        if "type" in connection and connection["type"] == "script":
            script_nodes.append(
                {
                    "id": connection["id"],
                    "data": {
                        "label": "Python Script Node",
                        "type": "script",
                        "source": str(objectid.ObjectId()),
                        "target": str(objectid.ObjectId()),
                    },
                    "type": "targetNode",
                    "position": {
                        "x": connection["scriptPosition"]["x"]
                        if "scriptPosition" in connection
                        else 400,
                        "y": connection["scriptPosition"]["y"]
                        if "scriptPosition" in connection
                        else 400,
                    },
                    "targetPosition": "right",
                    "sourcePosition": "left",
                }
            )
    return script_nodes


def convert_connections_to_flow_edges(connections: list, script_nodes: list) -> list:
    """ Function to convert the list of connections to React Flow edges

    :param connections: list of connections between data elements or scripts
    :param script_nodes: list of script nodes with their ids and target and source
    :return: a list of React Flow edges
    """
    flow_edges = []
    if connections:
        for connection in connections:
            if "type" in connection and connection["type"] == "direct":
                flow_edges.append(
                    {
                        "id": connection["id"],
                        "source": connection["source"],
                        "target": connection["target"],
                        "type": "deleteEdge",
                        "animated": True,
                        "zIndex": 1,
                    }
                )
            elif "type" in connection and connection["type"] == "script":
                script_node = [
                    node for node in script_nodes if node["id"] == connection["id"]
                ][0]
                flow_edges.append(
                    {
                        "id": script_node["data"]["source"],
                        "source": connection["source"],
                        "target": connection["id"],
                        "type": "smoothstep",
                        "animated": True,
                        "zIndex": 1,
                    }
                )
                flow_edges.append(
                    {
                        "id": script_node["data"]["target"],
                        "source": connection["id"],
                        "target": connection["target"],
                        "type": "smoothstep",
                        "animated": True,
                        "zIndex": 1,
                    }
                )
    return flow_edges
