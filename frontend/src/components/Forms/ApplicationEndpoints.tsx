import {
    Button,
    ButtonSet,
    CodeSnippet,
    CodeSnippetSkeleton,
    Column,
    Form,
    FormGroup,
    Grid,
    InlineNotification,
    ModalBody,
    ModalFooter,
    ModalHeader,
    Select,
    SelectItem,
    TextArea,
    TextInput,
    Tile,
    StructuredListBody,
    StructuredListCell,
    StructuredListHead,
    StructuredListRow,
    StructuredListWrapper,
    Tag,
} from "@carbon/react"
import {Add, TrashCan} from "@carbon/react/icons"
import React from "react"
import AceEditor from "react-ace"
import ReactJson from 'react-json-view'

import "ace-builds/src-noconflict/mode-json"
import "ace-builds/src-noconflict/snippets/json"
import "ace-builds/src-noconflict/theme-ambiance"
import "ace-builds/src-noconflict/theme-github"
import "ace-builds/src-noconflict/worker-json"
import "ace-builds/src-noconflict/ext-language_tools"
import 'ace-builds/webpack-resolver'

interface APIEndpointsInterface {
    id: string,
    setOpen: (state: boolean) => void,
    setTab: (index: number) => void,
    setId: (id: string) => void,
}

export const ApplicationEndpoints: React.FC<APIEndpointsInterface> = ({id, setOpen, setTab, setId}) => {
    const [formError, setFormError] = React.useState(false)
    const [formMessage, setFormMessage] = React.useState("")

    const [darkMode, setDarkMode] = React.useState(false)

    const [baseUrl, setBaseUrl] = React.useState("")
    const [operation, setOperation] = React.useState<any>("get")
    const [apiUrl, setApiUrl] = React.useState("")

    const [crawlBody, setCrawlBody] = React.useState("")
    const [crawlResponse, setCrawlResponse] = React.useState<any>(null)
    const [crawlHeader, setCrawlHeader] = React.useState("")
    const [crawlStatusCode, setCrawlStatusCode] = React.useState(404)
    const [crawling, setCrawling] = React.useState(false)
    const [crawlError, setCrawlError] = React.useState(false)

    const [pathParameterList, setPathParameterList] = React.useState([{key: "", value: ""}])
    const [queryParameterList, setQueryParameterList] = React.useState([{key: "", value: ""}])


    const [endpointList, setEndpointList] = React.useState<Array<{ "operation", "url", "requestBody", "pathVar", "queryVar", "response", "header", "status" }>>([])

    React.useEffect(() => {
        if (id !== "") {
            fetch("api/application/" + id)
                .then((res) => res.json())
                .then((res) => res["config"])
                .then((res) => {
                    setBaseUrl(res["baseUrl"])
                    setApiUrl(res["baseUrl"])
                    if ("endpointsBackup" in res) {
                        setEndpointList(res["endpointsBackup"])
                    }
                })
                .catch(error => {
                    console.log(error)
                })

        } else {
            setCrawlError(true)
            setFormMessage("Application ID not set")
        }
        if (document.documentElement.getAttribute("data-carbon-theme") === "g100") {
            setDarkMode(true)
        } else {
            setDarkMode(false)
        }
    }, [baseUrl, id])

    const initialState = () => {
        setFormError(false)
        setFormMessage("")
        resetCrawlForm()
        setId("")
    }

    const resetCrawlForm = () => {
        setCrawlBody("")
        setOperation("get")
        setApiUrl(baseUrl)
        setCrawlResponse(null)
        setCrawlHeader("")
        setCrawlStatusCode(404)
        setCrawling(false)
        setPathParameterList([{key: "", value: ""}])
        setQueryParameterList([{key: "", value: ""}])
        setCrawlError(false)
        setFormMessage("")
    }

    const close = () => {
        initialState()
        setTab(0)
        setOpen(false)
    }

    const crawlAPI = (e) => {
        setCrawling(true)
        setFormMessage("")
        setCrawlError(false)
        e.preventDefault()
        fetch("api/application/endpoint/crawl/" + id, {
            method: "POST",
            mode: "cors",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                operation: operation,
                url: apiUrl + getParameters(true),
                body: crawlBody,
            })
        }).then(response => response.json())
            .then(response => {
                if (!response["success"]) {
                    setCrawlError(true)
                    setCrawling(false)
                    setFormMessage(response["message"])
                } else {
                    setCrawlResponse(response["response"])
                    setCrawlHeader(response["header"])
                    setCrawlStatusCode(response["status"])
                    setCrawling(false)
                    if (response["status"] > 299 || response["status"] < 200) {
                        setCrawlError(true)
                        setFormMessage("Invalid API call")
                    }
                }
            })
            .catch(error => {
                console.log(error)
            })
    }

    const submit = (e) => {
        e.preventDefault()
        fetch("/api/application/endpoint/save/" + id, {
            method: "POST",
            mode: "cors",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                endpoints: endpointList
            })
        }).then(response => response.json())
            .then(response => {
                if (!response["success"]) {
                    setFormError(true)
                    setFormMessage(response["message"])
                } else {
                    setTab(3)
                }
            })
            .catch(error => {
                console.log(error)
            })
    }

    const addToEndpoint = () => {
        let tempCrawlBody = ""
        if (crawlBody !== "") {
            tempCrawlBody = JSON.parse(crawlBody)
        }
        let tempEndpointList = [{
            operation: "",
            url: "",
            requestBody: "",
            pathVar: [{key: "", value: ""}],
            queryVar: [{key: "", value: ""}],
            response: {},
            header: "",
            status: 0
        }]
        tempEndpointList = [...endpointList, {
            operation: operation,
            url: apiUrl,
            requestBody: tempCrawlBody,
            pathVar: pathParameterList,
            queryVar: queryParameterList,
            response: crawlResponse,
            header: crawlHeader,
            status: crawlStatusCode
        }]
        setEndpointList(() => tempEndpointList)
        resetCrawlForm()
    }
    const deleteFromEndpointList = (i) => {
        endpointList.splice(i, 1)
        setEndpointList([...endpointList])
    }

    const handleInputChange = (e, index, type) => {
        if (type === "path") {
            const {name, value} = e.target
            const list = [...pathParameterList]
            list[index][name] = value
            setPathParameterList(list)
        } else {
            const {name, value} = e.target
            const list = [...queryParameterList]
            list[index][name] = value
            setQueryParameterList(list)
        }
    }

    const handleRemoveClick = (index, type) => {
        if (type === "path") {
            const list = [...pathParameterList]
            list.splice(index, 1)
            setPathParameterList(list)
        } else {
            const list = [...queryParameterList]
            list.splice(index, 1)
            setQueryParameterList(list)
        }
    }

    const handleAddClick = (type) => {
        if (type === "path") {
            setPathParameterList(parameterList => [...parameterList, {key: "", value: ""}])
        } else {
            setQueryParameterList(parameterList => [...parameterList, {key: "", value: ""}])
        }
    }

    const setApiUrlWithParameters = (url) => {
        let seperated = url.split("/:")
        setApiUrl(seperated[0])
    }

    const getParameters = (toCrawl) => {
        let returnString = ""
        pathParameterList.map((x) => {
            if (x.key !== "" && x.value !== "") {
                if ((returnString === "" && apiUrl.endsWith("/")) || (returnString !== "" && returnString.endsWith("/"))) {
                    if (!toCrawl) {
                        returnString = returnString + ":" + x.key
                    } else {
                        returnString = returnString + x.value
                    }
                } else {
                    if (!toCrawl) {
                        returnString = returnString + "/" + ":" + x.key
                    } else {
                        returnString = returnString + "/" + x.value
                    }
                }
            }
        })
        let firstQuery = true
        queryParameterList.map((x) => {
            if (x.key !== "" && x.value !== "") {
                if (firstQuery) {
                    returnString = returnString + "?"
                    firstQuery = false
                } else {
                    returnString = returnString + "&"
                }
                returnString = returnString + x.key + "=" + x.value
            }
        })
        return returnString
    }

    return (
        <>
            <ModalHeader closeModal={() => close()}>
                <h3 className="bx--modal-header__heading">Add API Endpoints</h3>
            </ModalHeader>
            <ModalBody className="enable-scrollbar" aria-label="Add Endpoints" hasScrollingContent hasForm>
                <Grid>
                    <Column lg={8}>
                        <Tile className="crawl-tile-padding">
                            <h4 className="crawl-tile-title">Crawl Endpoint</h4>
                            <Form onSubmit={(e) => crawlAPI(e)}>
                                <FormGroup legendText="" className="api-formgroup-endpoint">
                                    <Select id="operation" value={operation} labelText="Operation"
                                            onChange={(e) => setOperation(e.currentTarget.value)}>
                                        <SelectItem value="get" text="GET"/>
                                        <SelectItem value="post" text="POST"/>
                                        <SelectItem value="put" text="PUT"/>
                                        <SelectItem value="delete" text="DELETE"/>
                                    </Select>
                                    <TextInput id="url" labelText="Endpoint URL" type="url" data-modal-primary-focus
                                               value={apiUrl + getParameters(false)}
                                               onChange={(e) => setApiUrlWithParameters(e.currentTarget.value)}
                                               required/>
                                    <Button size="field" type="submit">Crawl</Button>
                                </FormGroup>
                                <FormGroup legendText="Path variables" className="no-bottom-margin">
                                    {pathParameterList.map((x, i) => {
                                        return (
                                            <FormGroup legendText="" className="api-formgroup-parameter"
                                                       key={i}>
                                                <TextInput id={"key" + i}
                                                           labelText="Key"
                                                           value={x.key} key={i + ".1"}
                                                           name="key"
                                                           onChange={e => handleInputChange(e, i, "path")}
                                                />
                                                <TextInput id={"value" + i} className=""
                                                           labelText="Value"
                                                           value={x.value} key={i + ".2"} name="value"
                                                           onChange={e => handleInputChange(e, i, "path")}
                                                />
                                                {pathParameterList.length !== 1 &&
                                                    [(pathParameterList.length - 1 !== i &&
                                                        <Button hasIconOnly renderIcon={TrashCan} size="field"
                                                                key={i + ".4"}
                                                                className={"margin-add-button"}
                                                                iconDescription="Delete row"
                                                                tooltipAlignment="end" kind="ghost"
                                                                onClick={() => handleRemoveClick(i, "path")}/>

                                                    )]
                                                }
                                                {pathParameterList.length - 1 === i &&
                                                    <>
                                                        {pathParameterList.length !== 1 &&
                                                            <Button hasIconOnly renderIcon={TrashCan} size="field"
                                                                    className="button-spacing"
                                                                    iconDescription="Delete row"
                                                                    tooltipAlignment="end" key={i + ".5"} kind="ghost"
                                                                    onClick={() => handleRemoveClick(i, "path")}/>
                                                        }
                                                        <Button hasIconOnly renderIcon={Add} size="field"
                                                                iconDescription="Add row" key={i + ".6"}
                                                                tooltipAlignment="end" kind="ghost"
                                                                onClick={() => handleAddClick("path")}/>
                                                    </>
                                                }
                                            </FormGroup>
                                        )
                                    })}
                                </FormGroup>
                                <FormGroup legendText="Query variables" className="no-bottom-margin">
                                    {queryParameterList.map((x, i) => {
                                        return (
                                            <FormGroup legendText="" className="api-formgroup-parameter"
                                                       key={i}>
                                                <TextInput id={"key" + i}
                                                           labelText="Key"
                                                           value={x.key} key={i + ".1"}
                                                           name="key"
                                                           onChange={e => handleInputChange(e, i, "query")}
                                                />
                                                <TextInput id={"value" + i} className=""
                                                           labelText="Value"
                                                           value={x.value} key={i + ".2"} name="value"
                                                           onChange={e => handleInputChange(e, i, "query")}
                                                />
                                                {queryParameterList.length !== 1 &&
                                                    [(queryParameterList.length - 1 !== i &&
                                                        <Button hasIconOnly renderIcon={TrashCan} size="field"
                                                                key={i + ".4"}
                                                                className={"margin-add-button"}
                                                                iconDescription="Delete row"
                                                                tooltipAlignment="end" kind="ghost"
                                                                onClick={() => handleRemoveClick(i, "query")}/>

                                                    )]
                                                }
                                                {queryParameterList.length - 1 === i &&
                                                    <>
                                                        {queryParameterList.length !== 1 &&
                                                            <Button hasIconOnly renderIcon={TrashCan} size="field"
                                                                    className="button-spacing"
                                                                    iconDescription="Delete row"
                                                                    tooltipAlignment="end" key={i + ".5"} kind="ghost"
                                                                    onClick={() => handleRemoveClick(i, "query")}/>
                                                        }
                                                        <Button hasIconOnly renderIcon={Add} size="field"
                                                                iconDescription="Add row" key={i + ".6"}
                                                                tooltipAlignment="end" kind="ghost"
                                                                onClick={() => handleAddClick("query")}/>
                                                    </>
                                                }
                                            </FormGroup>
                                        )
                                    })}
                                </FormGroup>
                                <FormGroup legendText="Request Body" className="no-bottom-margin">
                                    {operation != "get" ?
                                        [(darkMode ?
                                                <AceEditor
                                                    style={{fontFamily: "inherit!important"}}
                                                    width="100%"
                                                    height="14rem"
                                                    mode="json"
                                                    theme="ambiance"
                                                    placeholder="(Optional) add a JSON body to the crawl"
                                                    fontSize={18}
                                                    onChange={setCrawlBody}
                                                    value={crawlBody}
                                                    highlightActiveLine={false}
                                                    showPrintMargin={false}
                                                />
                                                :
                                                <AceEditor
                                                    style={{fontFamily: "inherit!important"}}
                                                    width="100%"
                                                    height="14rem"
                                                    mode="json"
                                                    theme="github"
                                                    placeholder="(Optional) add a JSON body to the crawl"
                                                    fontSize={14}
                                                    onChange={setCrawlBody}
                                                    value={crawlBody}
                                                    highlightActiveLine={false}
                                                    showPrintMargin={false}

                                                />
                                        )]
                                        :
                                        <TextArea
                                            placeholder="(Optional) add a JSON body to the crawl, available when the operation is not GET"
                                            disabled={true}
                                            // onChange={(e) => setCrawlBody(e.currentTarget.value)}
                                            value={crawlBody}

                                        />
                                    }
                                </FormGroup>
                            </Form>
                        </Tile>
                    </Column>
                    <Column lg={8}>
                        <Tile>
                            <h4 className="crawl-tile-title">Crawl Response</h4>
                            {crawling ?
                                <CodeSnippetSkeleton type="multi"/>
                                :
                                <>
                                    {crawlResponse === null ?
                                        <>
                                            <CodeSnippet type="multi" hideCopyButton maxExpandedNumberOfRows={50}>
                                                {"Crawl an endpoint to see the response"}
                                            </CodeSnippet>
                                            {endpointList.length > 0 &&
                                                <>
                                                    <h4 className="crawl-tile-title">Added Endpoints </h4>
                                                    <StructuredListWrapper>
                                                        <StructuredListHead>
                                                            <StructuredListRow head>
                                                                <StructuredListCell head>Url</StructuredListCell>
                                                                <StructuredListCell head>Type</StructuredListCell>
                                                                <StructuredListCell head> </StructuredListCell>
                                                            </StructuredListRow>
                                                        </StructuredListHead>
                                                        <StructuredListBody>
                                                            {endpointList.map((endpoint, i) => (
                                                                <StructuredListRow key={i}>
                                                                    <StructuredListCell
                                                                        key={i + ".1"}>{endpoint.url}</StructuredListCell>
                                                                    <StructuredListCell key={i + ".2"}>
                                                                        <Tag className={"node-" + endpoint.operation}
                                                                             size="md">
                                                                            {endpoint.operation.toUpperCase()}
                                                                        </Tag>
                                                                    </StructuredListCell>
                                                                    <StructuredListCell><Button hasIconOnly
                                                                                                renderIcon={TrashCan}
                                                                                                kind={"ghost"}
                                                                                                label="Remove endpoint"
                                                                                                onClick={() => deleteFromEndpointList(i)}>Delete</Button></StructuredListCell>
                                                                </StructuredListRow>
                                                            ))}
                                                        </StructuredListBody>
                                                    </StructuredListWrapper>
                                                </>
                                            }
                                        </>

                                        :

                                        ([darkMode ?
                                            // @ts-ignore
                                            <ReactJson
                                                src={crawlResponse}
                                                name={false}
                                                theme="bright"
                                                displayObjectSize={false}
                                                displayDataTypes={false}
                                                enableClipboard={false}
                                                collapsed={1}
                                            />
                                            :
                                            // @ts-ignore
                                            <ReactJson
                                                src={crawlResponse}
                                                name={false}
                                                theme="rjv-default"
                                                displayObjectSize={false}
                                                displayDataTypes={false}
                                                enableClipboard={false}
                                                collapsed={1}
                                            />
                                        ])

                                    }
                                    {crawlResponse !== null &&
                                        <ButtonSet className="crawl-button-panel">
                                            <Button kind="secondary" onClick={() => resetCrawlForm()}>
                                                Discard
                                            </Button>
                                            <Button kind="primary" onClick={() => addToEndpoint()}
                                                    disabled={crawlStatusCode > 299}>
                                                Add Endpoint
                                            </Button>
                                        </ButtonSet>
                                    }
                                </>
                            }
                        </Tile>
                    </Column>
                </Grid>
            </ModalBody>
            {(formError || crawlError) &&
                <InlineNotification className={"modal-notification"} kind="error" title="Error"
                                    subtitle={formMessage}/>
            }
            <ModalFooter>
                <Button
                    kind="secondary"
                    onClick={() => {
                        setTab(1)
                    }}>
                    Back
                </Button>
                <Button
                    kind="primary"
                    type="submit"
                    onClick={(e) => submit(e)}
                >
                    Next
                </Button>
            </ModalFooter>
        </>

    )
}

export default ApplicationEndpoints