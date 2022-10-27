import json
import uuid

import genson
import prance.util.formats
import requests
import requests.structures
from prance import BaseParser, ResolvingParser, ValidationError, convert


# OpenAPI generation
# main function: generate_openapi()


def find_api_type_without_header(response: requests.Response):
    """Returns False if API type is not found, true and the type if type is found

    This function uses the body of a response to determine if an API is XML or JSON
    This can be useful when the API has not implemented correct headers.

    :param response: body of a response of a called API
    :return: boolean if type is found and type if found
    """
    if response.text[0] == "{":
        try:
            json.loads(response.text)
        except json.JSONDecodeError:
            return False, ""
        return True, "JSON"
    elif response.text[0] == "<":
        if "<?xml" in response.text:
            return True, "XML"
        else:
            return False, ""
    else:
        return False, ""


def find_api_type_with_header(header: requests.structures.CaseInsensitiveDict[str], response: requests.Response) -> \
        tuple[bool, str]:
    """Returns False if API type is not found, true and the type if type is found

    This function uses the header of a response of an API call to determine if the API is valid and either JSON or XML.
    If the header is not set correctly the PAI type will be tried to be determined by find_api_type_without_header().

    :param header: header of a response of a called API
    :param response: body of a response of a called API
    :return: boolean if type is found and type if found
    """
    if "Content-Type" in header:
        if "json" in header["Content-Type"]:
            try:
                json.loads(response.text)
                return True, "JSON"
            except json.JSONDecodeError:
                return False, ""
        elif header["Content-Type"] == "application/xml":
            if "<?xml" in response.text:
                return True, "XML"
            else:
                return False, ""
        else:
            return False, ""
    elif "content-type" in header:
        if "json" in header["content-type"]:
            try:
                json.loads(response.text)
                return True, "JSON"
            except json.JSONDecodeError:
                return False, ""
        elif header["content-type"] == "application/xml":
            if "<?xml" in response.text:
                return True, "XML"
            else:
                return False, ""
        else:
            return False, ""
    else:
        return find_api_type_without_header(response)


def find_api_type(url: str) -> tuple[bool, str]:
    """Returns if API type is found and if found it returns either XML or JSON

    This function tries to find the type of API that is given it in the url. It decides to try to find the type by
    looking at the header. If the header is not set correctly it will switch to a body based type finder.

    :param url: string of the url of API endpoint
    :return: boolean if type is found and type if found
    """
    response = requests.get(url)
    if 200 <= response.status_code < 300:
        header = response.headers
        if "Content-Type" in header or "content-type" in header:
            return find_api_type_with_header(header, response)
        else:
            return find_api_type_without_header(response)
    else:
        return False, ""


def parse_openapi(url: str = None, specs: dict = None, deref: bool = True) -> \
        tuple[bool, str] | tuple[bool, ResolvingParser] | tuple[bool, BaseParser]:
    """Returns if the given OpenAPI specification is valid and could be parsed, if parsable it returns the parsed specs

    This function tries to parse the given OpenAPI document. The document can be delivered either as an url or as a
    dict.

    :param deref: bool to dereference the parsed openapi specs
    :param url: url to download the spec file from
    :param specs: specs as a local dict
    :return: boolean if the specs are valid and if valid a parsed version of the specs
    """
    try:
        if url is not None:
            if deref:
                return True, ResolvingParser(url, backend="openapi-spec-validator")
            else:
                return True, BaseParser(url, backend="openapi-spec-validator")
        elif specs is not None:
            if deref:
                return True, ResolvingParser(spec_string=str(specs), backend="openapi-spec-validator")
            else:
                return True, BaseParser(spec_string=str(specs), backend="openapi-spec-validator")
        else:
            return False, ""
    except ValidationError as e:
        print("Validation Error:", e)
        return False, ""
    except prance.util.formats.ParseError as e:
        print("Parse Error:", e)
        return False, ""
    except Exception as e:
        print("Unknown Error:", e)
        return False, ""


def get_openapi(config: dict, url: str = None, specs: dict = None, deref: bool = True):
    """Returns OpenAPI specs that are downloaded

        This function downloads the OpenAPI file and converts it from OpenAPI 2.0 to 3.0 (3.1) if necessary.
        The specs are put in tn the config dict.
    .

        :param deref: bool to dereference the openapi specs
        :param specs: openapi specs that need parsing
        :param url: url of the specs to be downloaded
        :param config: the complete configuration for the API in question
        :return: boolean if specs are correctly downloaded and added to config
    """
    if url is not None:
        state, parser = parse_openapi(url=url, deref=deref)
    elif specs is not None:
        state, parser = parse_openapi(specs=specs, deref=deref)
    else:
        return False
    if state:
        if "swagger" in parser.specification:
            try:
                parser = convert.convert_spec(parser)
                config["converted"] = True
                config["specs"] = parser.specification
                return True
            except convert.ConversionError as e:
                print("Conversion Error:", e)
                return False
        else:
            config["converted"] = False
            config["specs"] = parser.specification
            return True
    else:
        print("There was an error generating the openapi document")
        return False


def get_endpoint_url(base_url: str, url: str) -> str:
    """Returns endpoint without base url

    This function removes the bas url from the whole url in order to return the final path.
    For example: url = https://nguml.nl/api/class/ => baseurl is https://nguml.nl, path is /api/class/

    :param base_url: the base url of an API endpoint,
    :param url: complete url
    :return: the path
    """
    endpoint = url.replace(base_url, "")
    if endpoint.startswith("/"):
        return endpoint
    else:
        return "/" + endpoint


def get_base_url(base_url: str) -> str:
    """Returns base url without trailing /

    This function removes the trailing / if present in th base url.
    This is done to make sure that when base url and path meet that there not 2 slashes in the complete url.

    :param base_url: the base url to clean
    :return: base url without trailing /
    """
    if base_url.endswith("/"):
        return base_url[:-1]
    else:
        return base_url


def generate_example(endpoint: dict) -> set:
    """Returns simple example for a request

    This function generates a simple example for the OpenAPI specs, in particular when for post and put requests.
    These types of requests have a body that is sent to the API.

    :param endpoint: a dict containing all the information about one endpoint for the API,
    for example "https://gorest.co.in/public/v1/users"
    :return: a dict that sevres an example in the request part of an OpenAPI document
    """
    return {endpoint["requestBody"]}


def try_parameter_convert(value: str) -> str | int:
    """returns value as its correct type

    Due to the way the Typescript is set up in the front end there is no way to make distinction between string and
    integer input So that is why this function will try to cast the values. This function is particularly useful for
    generation of schemas for parameters
    :return: value either as an int or as a string

    """
    try:
        return int(value)
    except ValueError:
        return value


def generate_parameters(endpoint: dict) -> list:
    """Returns a dict containing all the query and path variables for one endpoint

    This function generates a dict in OpenAPI format to describe all the query and path variables the given endpoint
    has. This dict is used in an OpenAPI document.

    :param endpoint: a dict containing all the information about one endpoint for the API,
    for example "https://gorest.co.in/public/v1/users"
    :return: a dict with the query and path variables
    """
    output = []
    if endpoint["pathVar"][0]["key"] != "":
        for parameter in endpoint["pathVar"]:
            output.append(
                {
                    "name": parameter["key"],
                    "in": "path",
                    "required": True,
                    "description": "Automatically generated by APIMapping Framework",
                    "schema": generate_schema(
                        try_parameter_convert(parameter["value"]), False
                    ),
                    # "examples": {"entered": parameter}
                }
            )
    if endpoint["queryVar"][0]["key"] != "":
        for parameter in endpoint["queryVar"]:
            output.append(
                {
                    "name": parameter["key"],
                    "in": "query",
                    "required": False,
                    "description": "Automatically generated by APIMapping Framework",
                    "schema": generate_schema(
                        try_parameter_convert(parameter["value"]), False
                    ),
                }
            )
    return output


def generate_response(endpoint: dict) -> dict:
    """Returns a response section for the specified endpoint
    This function generates a response section for a specified endpoint when a response is given.
    A status 204 means Ok without any response.

    :param endpoint: a dict containing all the information about one endpoint for the API,
    for example "https://gorest.co.in/public/v1/users"
    :return: dict containing the response section of the path section of an endpoint
    """
    output = {}
    status = str(endpoint["status"])
    output[status] = {}
    output[status]["description"] = "Automatically generated by APIMapping Framework"
    if status != "204":
        if "Content-Type" in endpoint["header"]:
            output[status]["content"] = {
                endpoint["header"]["Content-Type"]: {
                    "schema": generate_schema(endpoint["response"])
                },
                "examples": {},
            }
        elif "content-type" in endpoint["header"]:
            output[status]["content"] = {
                endpoint["header"]["content-type"]: {
                    "schema": generate_schema(endpoint["response"])
                },
                "examples": {},
            }
        else:
            print(endpoint)
    return output


def generate_request(endpoint: dict) -> dict:
    """Returns a request section if needed for the document

    This function generates a requestBody section for an post or put endpoint for an OpenAPI document.
    :param endpoint: a dict containing all the information about one endpoint for the API,
    for example "https://gorest.co.in/public/v1/users"
    :return:dict containing the requestBody
    """
    request = {}
    if "Content-Type" in endpoint["header"]:
        request = {
            "content": {
                endpoint["header"]["Content-Type"]: {
                    "schema": generate_schema(endpoint["requestBody"])
                },
                "example": {},
            }
        }
    elif "content-type" in endpoint["header"]:
        request = {
            "content": {
                endpoint["header"]["content-type"]: {
                    "schema": generate_schema(endpoint["requestBody"])
                },
                "example": {},
            }
        }
    return request


def generate_paths(config: dict, endpoints: dict) -> dict:
    """Returns a dict containing the path section of an OpenAPI specification.

    This function generates the path section of the document by setting description, responses, servers and parameters
    per endpoint. If its a post or put it will set a schema for the data body.

    :param config: the complete configuration for the API in question
    :param endpoints: a dict containing endpoints for the API, example "https://gorest.co.in/public/v1/users"
    :return: a dict containing the paths
    """
    output = {}
    for endpoint in endpoints["endpoints"]:
        # print(endpoint)
        endpoint_url = get_endpoint_url(config["baseUrl"], endpoint["url"])
        if endpoint["pathVar"][0]["key"] != "":
            for parameter in endpoint["pathVar"]:
                if not endpoint_url.endswith("/"):
                    endpoint_url += "/"
                endpoint_url = endpoint_url + "{" + parameter["key"] + "}"
        if endpoint_url not in output:
            output[endpoint_url] = {}
        output[endpoint_url][endpoint["operation"]] = {
            "summary": "Automatically generated by APIMapping Framework",
            "responses": generate_response(endpoint),
            "servers": [{"url": get_base_url(config["baseUrl"])}],
            "parameters": generate_parameters(endpoint),
        }
        if "requestBody" in endpoint and endpoint["requestBody"] != "":
            output[endpoint_url][endpoint["operation"]][
                "requestBody"
            ] = generate_request(endpoint)
    return output


def detect_array_of_uuids(keys: list) -> bool:
    """Returns a boolean after checking for a list of UUID

    This function searches the keys of a dict to find UUIDs.
    :param keys: keys of a dict given as a list
    :return: a boolean if a UUID is found in list of keys
    """
    if not keys:
        return False
    for key in keys:
        try:
            uuid.UUID(key)
        except ValueError:
            return False
    return True


def detect_nested_dict_uuid(data: dict, detected: list) -> None:
    """Returns a list of keys that have a UUID as key dict as its child

    This function uses detect_array_of_uuids in a recursive way to detect teh use of dicts with the keys being UUIDS.
    When such a datatype is found it's added to the detected list which will be used to build the seed upon.

    :param detected: list of detected uuids
    :param data: the data where a schema needs to be build for
    "param detected: a 'call by reference' list of keys that have a UUID dict
    """
    if isinstance(data, dict):
        for key in data.keys():
            if isinstance(data[key], dict):
                detect_nested_dict_uuid(data[key], detected)
                if detect_array_of_uuids(data[key].keys()):
                    detected.append(key)


def detect_null_value(data: dict) -> None:
    """Postprocessor to change type:"null"

    In OpenAPI type null is not allowed. Our schema generator Genson, generates JSON schema, although these do not
    differ much with OpenAPI schema's there are some differences. Null is not allowed and is replaced with nullable:
    true

    :param data: the JSON schema
    """
    for key in data.keys():
        if isinstance(data[key], dict):
            detect_null_value(data[key])
    if "type" in data and data["type"] == "null":
        data["nullable"] = True
        data.pop("type")
    if "type" in data and isinstance(data["type"], list) and data["type"].count("null") == 1:
        data["type"].remove("null")
        data["type"] = data["type"][0]


def build_seed(data: dict) -> dict:
    """Returns a seed for the Genson package

    This function preprocesses the data for which a schema needs to be build for. It preprocesses it because the used
    schema generator Genson cannot generate schemas for certain datatype on its own.
    The Genson package cannot handle dicts that use UUIDs as string format as their key. Genson and sort of JSON schema,
    do not expect variables as the key of dicts. This is mostly fine because normally keys are values that one knows.
    Integer keys cannot be used but UUID keys can be used. Therefor a seed is build to detect these dicts and push
    Genson in the right direction.
    :param data: the data where a schema needs to be build for
    :return: a simple schema that serves as a seed for Genson
    """
    detected_dicts = []
    detect_nested_dict_uuid(data, detected_dicts)
    seed = {}
    if detected_dicts:
        uuid_regex = {
            "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$": {}
        }
        seed["type"] = "object"
        seed["properties"] = {}
        for elements in detected_dicts:
            seed["properties"][elements] = {
                "type": "object",
                "patternProperties": uuid_regex,
            }
    return seed


def generate_schema(data: any, use_seed: bool = True) -> dict:
    """Returns a modified JSON schema given the data is sent to or received from an API

    This function takes the received or send data from an PAI and creates a schema describing the fields and types of
    data that are sent or received. It is modified to work as an OpenAPI schema, removing the schema definition
    from the returned dict. It also adds a seed to enable the generation of schema's that are not supported
    out-of-the-box.
    Example of data:
    {
        "id": 2203,
        "name": "Deevakar Johar",
        "email": "johar_deevakar@ohara-prosacco.biz",
        "gender": "female",
        "status": "inactive"
    }
    Generated schema:
    {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer"
        },
        "name": {
          "type": "string"
        },
        "email": {
          "type": "string"
        },
        "gender": {
          "type": "string"
        },
        "status": {
          "type": "string"
        }
      }
    }
    :param use_seed: boolean to make a seed schema
    :param data: a body that is sent or received from an API
    :return: a JSON schema as a dict
    """
    builder = genson.SchemaBuilder(schema_uri=False)
    if use_seed:
        builder.add_schema(build_seed(data))
    builder.add_object(data)
    schema = builder.to_schema()
    detect_null_value(schema)
    return schema


def generate_security_scheme(config: dict) -> dict:
    """Returns a dict that contains the security scheme part of an OpenAPI specification

    This functions generates a dict containing with either basic authentication or header authentication if set in
    config if no authentication is set in the config then an empty dict is returned.

    :param config: the complete configuration for the API in question
    :return: a dict containing the security scheme
    """
    output = {}
    if "securityScheme" in config:
        if config["securityScheme"] == "BasicAuth":
            output = {config["securityScheme"]: {"type": "http", "scheme": "basic"}}

        elif config["securityScheme"] == "ApiKeyAuth":
            for key in config["headerItems"]:
                output[key] = {"type": "apiKey", "in": "header", "name": key}
    return output


def generate_security(config: dict) -> list:
    """Returns the security part of an OpenAPI specification

    This function takes the config and checks if the there is a header authentication needed. If so a security
    section is generated which contain all the header items that are needed for authentication
    :param config: the complete configuration for the API in question
    :return: a list containing the security section
    """
    output = {}
    if "securityScheme" in config:
        if config["securityScheme"] == "ApiKeyAuth":
            for key in config["headerItems"]:
                output[key] = []
    return [output]


def generate_openapi(config: dict, endpoints: dict) -> bool:
    """Returns a generated OpenAPI specification

    This main function generates an OpenAPI specification given its API endpoints and configuration.
    It generates it by calling a series of functions that all generate a section of the OpenAPI specification.

    :param config: the complete configuration for the API in question
    :param endpoints: a dict containing endpoints for the API, example "https://gorest.co.in/public/v1/users"
    :return: a parsed OpenAPI specification as a dict containing dicts
    """
    info = {
        "title": config["name"],
        "description": config["description"],
        "version": str(config["version"]),
    }
    servers = [{"url": get_base_url(config["baseUrl"])}]
    components = {"securitySchemes": generate_security_scheme(config)}
    security = generate_security(config)
    paths = generate_paths(config, endpoints)

    api_spec = {
        "openapi": "3.0.1",
        "info": info,
        "paths": paths,
        "servers": servers,
        "components": components,
        "security": security,
    }
    print("=========== Generated OpenAPI Specifications ===========")
    print(api_spec)
    print("=========== End Generated OpenAPI Specifications ===========")
    return get_openapi(config, specs=api_spec, deref=False)


def resolve_refs(specs: str) -> tuple[bool, str]:
    """Returns specs without $refs

    This function uses the Prance ResolvingParser to (temporarily) resolve the $refs for schema's in the OpenAPI specs.
    :param specs: the complete OpenAPI specification
    :return: a parsed OpenAPI specification as a dict without $refs
    """
    try:
        resolved_refs_specs = ResolvingParser(
            spec_string=specs, backend="openapi-spec-validator",
        )
        return True, resolved_refs_specs.specification
    except ValidationError as e:
        print("Validation Error:", e)
        return False, ""
    except prance.util.formats.ParseError as e:
        print("Parse Error:", e)
        return False, ""
