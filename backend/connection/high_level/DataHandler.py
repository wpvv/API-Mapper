from bson import objectid
from flask import jsonify, request, Blueprint

from backend.connection import ConnectionConfig, ConnectionRecommendations
from backend.connection.high_level import Flow
from backend.connection.low_level import StateHandler

connection_high_level_data_handler = Blueprint("ConnectionHighLevelDataHandler", __name__)

def connection_exists(connection_config: dict, endpoint_config: dict) -> bool:
    """Function to check if a connection between API endpoints already exists

    :param connection_config: dict containing all the information about a connection between applications
    :param endpoint_config: dict containing data for the connection that is requested
    :return: boolean if API endpoint connection exists
    """
    if "endpointMapping" in connection_config and connection_config["endpointMapping"]:
        edge_index = next(
            (
                index
                for (index, value) in enumerate(connection_config["endpointMapping"])
                if value["source"]["endpointId"]
                == endpoint_config["source"]["endpointId"]
                and value["target"]["endpointId"]
                == endpoint_config["target"]["endpointId"]
            ),
            None,
        )
        return edge_index is not None
    else:
        return False


@connection_high_level_data_handler.route(
    "/api/connection/flow/add/edge/<connection_id>", methods=["POST"]
)
def add_endpoint_connection(
    connection_id: str,
    endpoint_config: dict = None,
    recommendation: bool = False,
    internal: bool = False,
) -> bool | tuple:
    """Function to add an API connection

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


@connection_high_level_data_handler.route(
    "/api/connection/flow/edge/<connection_id>/<edge_id>", methods=["DELETE"]
)
def delete_endpoint_connection(connection_id: str, edge_id: str) -> tuple:
    """Function to delete a connection between API endpoints

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


@connection_high_level_data_handler.route(
    "/api/connection/get/edges/<connection_id>", methods=["GET"]
)
def get_endpoint_connections(
    connection_id: str, internal: bool = False
) -> list | None | tuple:
    """Function to get a list of connections between API endpoints

    :param internal: Indicator for return type
    :param connection_id: Unique identifier for the connection configuration between applications
    :return: a list of connections between API endpoints
    """
    connection_config = ConnectionConfig.get_connection_config(
        connection_id, internal=True, flow=False
    )
    if "endpointMapping" in connection_config:
        if internal:
            return connection_config["endpointMapping"]
        else:
            return (
                jsonify(connection_config["endpointMapping"]),
                200,
                {"ContentType": "application/json"},
            )
    else:
        if internal:
            return
        else:
            return (
                jsonify({}),
                200,
                {"ContentType": "application/json"},
            )


@connection_high_level_data_handler.route(
    "/api/connection/save/<connection_id>",
    methods=["GET"],
)
def save_final_connection(connection_id: str) -> tuple:
    """Function to "save" all the mapping and return any incomplete mappings.

    Function that sets the state of the connection between the applications. It does not save it because a mapping is
    already saved upon creation. This function does check all mappings for completion and sets its state.

    :param connection_id: Unique identifier for the connection configuration between applications
    :return: a Flask response with the result of the checks
    """
    if StateHandler.save_mappings(connection_id):
        if ConnectionConfig.set_state(objectid.ObjectId(connection_id)):
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


@connection_high_level_data_handler.route(
    "/api/connection/recommendations/<connection_id>",
    methods=["GET"],
)
def get_recommendations(connection_id: str) -> tuple:
    """Function to make the High level interface interact with the recommendations module.

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
    nodes, edges = Flow.get_connection_config_flow(connection_id, internal=True)
    return (
        jsonify({"success": True, "data": {"nodes": nodes, "edges": edges}}),
        200,
        {"ContentType": "application/json"},
    )


def get_incomplete_APIs(connection_id: str) -> list:
    """Function to return a list of all the API connections that are incomplete.

    :param connection_id: Unique identifier for the connection configuration between applications
    :return: a list with the generate name for the connection of 2 API endpoints
    """
    config = ConnectionConfig.get_connection_config(connection_id, internal=True)
    incomplete_mappings = []
    if "endpointMapping" in config and config["endpointMapping"]:
        for api in config["endpointMapping"]:
            if not api["complete"] and not api["recommendation"]:
                incomplete_name = StateHandler.generate_connection_name(api)
                incomplete_mappings.append(incomplete_name)
    return incomplete_mappings
