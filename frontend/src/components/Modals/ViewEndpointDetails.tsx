import React from "react"
import {
    InlineNotification,
    Modal,
    Stack,
    StructuredListBody,
    StructuredListCell,
    StructuredListHead,
    StructuredListRow,
    StructuredListWrapper,
    Tag,
} from "@carbon/react"
import ReactJson from "react-json-view"
import "./_viewEndpointDetails.scss"
interface AddConnectionDetailsInterface {
    open: boolean,
    setOpen: (state: boolean) => void,
    node: object,
}

export const ViewEndpointDetails: React.FC<AddConnectionDetailsInterface> = ({open, setOpen, node}) => {
    const [application, setApplication] = React.useState("")
    const [endpoint, setEndpoint] = React.useState("")
    const [operation, setOperation] = React.useState("")
    const [description, setDescription] = React.useState("")
    const [summary, setSummary] = React.useState("")
    const [parameters, setParameters] = React.useState<Array<{ in, name, required }>>([])
    const [responseSchema, setResponseSchema] = React.useState({})
    const [requestSchema, setRequestSchema] = React.useState({})

    const [darkMode, setDarkMode] = React.useState(false)
    const [formError, setFormError] = React.useState(false)
    const [errorMsg, setErrorMsg] = React.useState("")

    React.useEffect(() => {
        if (Object.keys(node).length !== 0) {
            if (node["data"]["applicationId"] !== "") {
                fetch("/api/connection/flow/get/node/" + node["data"]["applicationId"], {
                    method: "POST",
                    mode: "cors",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        path: node["data"]["path"],
                        operation: node["data"]["operation"]
                    })
                }).then((res) => res.json())
                    .then((res) => {
                        setApplication(res["data"]["application"])
                        setEndpoint(res["data"]["path"])
                        setOperation(res["data"]["operation"])
                        if ("description" in res["data"]) {
                            setDescription(res["data"]["description"])
                        }
                        if ("summary" in res["data"]) {
                            setSummary(res["data"]["summary"])
                        }
                        if ("parameters" in res["data"]) {
                            setParameters(res["data"]["parameters"])
                        }
                        if ("responseSchema" in res["data"]) {
                            setResponseSchema(res["data"]["responseSchema"])
                        }
                        if ("requestSchema" in res["data"]) {
                            setRequestSchema(res["data"]["requestSchema"])
                        }
                    })
                    .catch(error => {
                        console.log(error)
                    })
            } else {
                setFormError(true)
                setErrorMsg("Node ID not set")
            }
        }
        if (document.documentElement.getAttribute("data-carbon-theme") === "g100") {
            setDarkMode(true)
        } else {
            setDarkMode(false)
        }
    }, [node])

    const close = () => {
        setOpen(false)
        node = {}
        setApplication("")
        setEndpoint("")
        setOperation("")
        setDescription("")
        setSummary("")
        setParameters([])
        setResponseSchema({})
        setRequestSchema({})
    }
    return (
        <Modal
            modalHeading={endpoint}
            modalLabel="Endpoint Details"
            open={open}
            passiveModal
            onRequestClose={() => close()}
        >
            <Stack gap={6}>
                <div>
                    <h6>Application: </h6>
                    {application}
                </div>
                <div>
                    <h6>Endpoint path:</h6>
                    {endpoint}
                </div>
                <div>
                    <h6>Operation: </h6>
                    <Tag className={"node-" + operation} size="md">
                        {operation.toUpperCase()}
                    </Tag>
                </div>
                {description &&
                    <div><h6>Description: </h6>{description}</div>
                }
                {summary &&
                    <div><h6>Summary: </h6>{summary}</div>
                }
                {parameters.length !== 0 &&
                    <div><h6>Parameters: </h6>
                        <StructuredListWrapper>
                            <StructuredListHead>
                                <StructuredListRow head>
                                    <StructuredListCell head>Name</StructuredListCell>
                                    <StructuredListCell head>Type</StructuredListCell>
                                    <StructuredListCell head>Required</StructuredListCell>
                                </StructuredListRow>
                            </StructuredListHead>
                            <StructuredListBody>
                                {parameters.map((parameter, i) => (
                                    <StructuredListRow key={i}>
                                        <StructuredListCell key={i + ".1"}>{parameter.name}</StructuredListCell>
                                        <StructuredListCell key={i + ".2"}>{parameter.in}</StructuredListCell>
                                        {parameter.required ?
                                            <StructuredListCell key={i + ".3"} className="parameter-required">Required</StructuredListCell>
                                            :
                                            <StructuredListCell key={i + ".3"} className="parameter-optional">Optional</StructuredListCell>
                                        }
                                    </StructuredListRow>
                                ))}
                            </StructuredListBody>
                        </StructuredListWrapper>
                    </div>
                }
                {Object.keys(requestSchema).length !== 0 &&
                    <div><h6>Request Schema: </h6>
                        {darkMode ?
                            // @ts-ignore
                            <ReactJson
                                name={false}
                                displayObjectSize={false}
                                displayDataTypes={false}
                                enableClipboard={false}
                                src={requestSchema}
                                theme="bright"
                                collapsed={1}
                            />
                            :
                            // @ts-ignore
                            <ReactJson
                                name={false}
                                displayObjectSize={false}
                                displayDataTypes={false}
                                enableClipboard={false}
                                src={requestSchema}
                                theme="rjv-default"
                                collapsed={1}
                            />
                        }
                    </div>
                }
                {Object.keys(responseSchema).length !== 0 &&
                    <div><h6>Response Schema: </h6>
                        {darkMode ?
                            // @ts-ignore
                            <ReactJson
                                name={false}
                                displayObjectSize={false}
                                displayDataTypes={false}
                                enableClipboard={false}
                                src={responseSchema}
                                theme="bright"
                                collapsed={1}
                            />
                            :
                            // @ts-ignore
                            <ReactJson
                                name={false}
                                displayObjectSize={false}
                                displayDataTypes={false}
                                enableClipboard={false}
                                src={responseSchema}
                                theme="rjv-default"
                                collapsed={1}
                            />
                        }
                    </div>
                }
            </Stack>
            {formError &&
                <InlineNotification className={"modal-notification"} kind="error" title="Error"
                                    subtitle={errorMsg}/>
            }
        </Modal>
    )
}
export default ViewEndpointDetails