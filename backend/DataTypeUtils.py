
def convert_python_to_json(data_type: str) -> str:
    """Returns the converted Python data type to JSON typing

     Types are converted to be displayed in the frontend, this is done due to readability. For example str -> string
     :param data_type: Python data type as string
     :return: JSON type as string
     """
    if data_type == "dict":
        return "object"
    elif data_type == "list" or data_type == "tuple":
        return "array"
    elif data_type == "str":
        return "string"
    elif data_type == "int" or data_type == "float" or data_type == "long":
        return "number"
    elif data_type == "bool":
        return "boolean"
    elif data_type == "None":
        return "null"
    else:
        return "unknown datatype"


def convert_openapi_to_json(data_type: str) -> str:
    """ Convert openAPI specific data type to json

    :param data_type: data type as a string
    :return: string of json data type
    """
    if data_type == "number" or data_type == "integer":
        return "number"
    else:
        return data_type


def convert_json_to_python(data_type: str) -> any:
    """ Function to convert json data type to a python native data type

    :param data_type: json data type as a string
    :return: instance of python data type
    """
    if data_type == "object":
        return dict()
    elif data_type == "array":
        return list()
    elif data_type == "string":
        return str()
    elif data_type == "number":
        return float()
    elif data_type == "boolean":
        return bool()
    elif data_type == "null":
        return None
    else:
        return "unknown datatype"
