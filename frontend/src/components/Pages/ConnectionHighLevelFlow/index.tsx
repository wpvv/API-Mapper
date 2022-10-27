import React from "react"
import "./_connectionHighLevelFlow.scss"
import {
    Button,
    ButtonSet,
    HeaderPanel,
    InlineNotification,
    InlineLoading,
    SkeletonPlaceholder,
    Tile
} from "@carbon/react"
import ReactFlow, {
    addEdge,
    Background,
    ConnectionMode,
    Controls,
    ReactFlowProvider,
    useEdgesState,
    useNodesState,
} from "react-flow-renderer"
import {useParams} from "react-router-dom"
import AddConnectionDetails from "../../Modals/AddConnectionDetails"
import ViewEndpointDetails from "../../Modals/ViewEndpointDetails"
import AddConnectionVariable from "../../Modals/AddConnectionVariable"
import FlowConnectionLine from "../../Misc/FlowConnectionLine"
import AddConnectionLowLevelFlow from "../../Modals/AddConnectionLowLevelFlow"
import EditEdge from "../../Misc/EditEdge"
import HighLevelFlowNode from "../../Misc/HighLevelFlowNode"
import IncompleteMapping from "../../Modals/IncompleteMapping";

interface ConnectionInterface {
    error: boolean,
}

export const ConnectionGenerator: React.FC<ConnectionInterface> = ({error}) => {
    const [nodes, setNodes, onNodesChange] = useNodesState([])
    const [edges, setEdges, onEdgesChange] = useEdgesState([])
    const [selectedNode, setSelectedNode] = React.useState({})
    const [selectedConnection, setSelectedConnection] = React.useState("")
    const [showConverterSidebar, setShowConverterSidebar] = React.useState(false)
    const [reactFlowInstance, setReactFlowInstance] = React.useState<any>()

    const [connectionDetailsModal, setConnectionDetailsModal] = React.useState(false)
    const [nodeDetailsModal, setNodeDetailsModal] = React.useState(false)
    const [addConstantModal, setAddConstantModal] = React.useState(false)
    const [addMappingModal, setAddMappingModal] = React.useState(false)
    const [incompleteMappingModal, setIncompleteMappingModal] = React.useState(false)

    const [incompleteReason, setIncompleteReason] = React.useState("")
    const [incompleteMappingList, setIncompleteMappingList] = React.useState([])

    const [formError, setFormError] = React.useState(false)
    const [errorMsg, setErrorMsg] = React.useState("")

    const {id} = useParams()
    const reactFlowWrapper = React.useRef<any>()
    let node_id = 0
    const getId = () => `dndnode_${node_id++}`

    const edgeTypes = React.useMemo(() => ({editEdge: EditEdge,}), [])
    const nodeTypes = React.useMemo(() => ({highLevelNode: HighLevelFlowNode,}), [])

    const [formIsSubmitting, setFormIsSubmitting] = React.useState(false)
    const [formSuccess, setFormSuccess] = React.useState(false)
    const [formMessageShort, setFormMessageShort] = React.useState("")

    const [recommendationIsSubmitting, setRecommendationIsSubmitting] = React.useState(false)
    const [recommendationSuccess, setRecommendationSuccess] = React.useState(false)
    const [recommendationMessageShort, setRecommendationMessageShort] = React.useState("")

    React.useEffect(() => {
        if (id !== "") {
            fetch("/api/connection/" + id)
                .then((res) => res.json())
                .then((res) => {
                    if (res["state"] !== "Complete") {
                        setConnectionDetailsModal(true)
                    }
                })
                .catch(error => {
                    console.log(error)
                })
            fetch("/api/connection/flow/" + id)
                .then((res) => res.json())
                .then((res) => {
                    if (res["success"]) {
                        setNodes(res["data"]["nodes"])
                        setEdges(res["data"]["edges"])
                    }
                })
                .catch(error => {
                    console.log(error)
                })
        } else {
            setFormError(true)
            setErrorMsg("Connection ID not set")
        }
    }, [id])

    const AddConnectionSetBody = (params) => {
        let types = ["post", "put", "delete"]
        let connectionBody = {}
        if (nodes[params.source]["data"]["operation"] === "get") {
            connectionBody["source"] = nodes[params.source]["data"]
            connectionBody["target"] = nodes[params.target]["data"]
        } else if (types.includes(nodes[params.source]["data"]["operation"])) {
            connectionBody["source"] = nodes[params.target]["data"]
            connectionBody["target"] = nodes[params.source]["data"]
        } else {
            if (nodes[params.target]["data"]["operation"] === "get") {
                connectionBody["source"] = nodes[params.target]["data"]
                connectionBody["target"] = nodes[params.source]["data"]
            } else {
                connectionBody["source"] = nodes[params.source]["data"]
                connectionBody["target"] = nodes[params.target]["data"]
            }
        }
        return connectionBody
    }
    const validateNewConnection = (params) => {
        let types = ["post", "put", "delete"]
        if (((nodes[params.source]["data"]["operation"] === "get") && (types.includes(nodes[params.target]["data"]["operation"]))) ||
            (nodes[params.target]["data"]["operation"] === "get") && (types.includes(nodes[params.source]["data"]["operation"]))) {
            return true
        } else if (params.source === "0" || params.target === "0") {
            return true
        }
        return false
    }

    const addConnection = (params) => {
        if (validateNewConnection(params)) {
            fetch("/api/connection/flow/add/edge/" + id, {
                method: "POST",
                mode: "cors",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(AddConnectionSetBody(params))
            }).then(res => res.json())
                .then(res => {
                    if (!res["success"]) {
                        setFormError(true)
                        setErrorMsg("Adding of connection failed, check logs")
                    } else {
                        let edge = {
                            id: res["id"],
                            source: params.source,
                            target: params.target,
                            sourceHandle: "",
                            targetHandle: "",
                            animated: true,
                            type: "editEdge",
                            data: {"offset": ((Math.random() * 2 - 1) * 50)},
                        }
                        if (nodes[params.target]["data"]["operation"] === "get") {
                            edge["className"] = "reverse"
                        }
                        setEdges((eds) => addEdge(edge, eds))
                    }
                })
                .catch(error => {
                    console.log(error)
                })
        } else {
            setFormError(true)
            setErrorMsg("A connection needs to have a get endpoint on one side and either post, delete or put on the other side ")
        }
    }


    const deleteConnectionWithMappingId = (mappingId) => {
        let index = edges.findIndex(i => i.id === mappingId)
        deleteConnection([edges[index]])
        edges.splice(index, 1)
        setEdges([...edges])
    }

    const deleteConnection = (edges) => {
        edges.forEach((edge) => {
            fetch("/api/connection/flow/edge/" + id + "/" + edge.id,
                {
                    method: "DELETE",
                    mode: "cors",
                }
            )
                .then((res) => res.json())
                .then((res) => {
                    if (!res["success"]) {
                        setFormError(true)
                        setErrorMsg("Deletion of connection failed, check logs")
                    }
                })
                .catch(error => {
                    console.log(error)
                })
        })
    }

    const addNode = (node) => {
        fetch("/api/connection/flow/add/node/" + id, {
            method: "POST",
            mode: "cors",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                type: node.type,
                data: node.data,
            })
        }).then(res => res.json())
            .then(res => {
                if (!res["success"]) {
                    setFormError(true)
                    setErrorMsg("Adding of node failed, check logs")
                } else {
                    setNodes((nds) => nds.concat(node))

                }
            })
            .catch(error => {
                console.log(error)
            })
    }

    const deleteNode = (node) => {
        console.log(node)
    }

    const nodeClick = (e, node) => {
        if (!isNaN(parseInt(node.id))) {
            if ("operation" in node.data) {
                //node is generated by backend
                setSelectedNode(node)
                setNodeDetailsModal(true)
            }
            if (node.id === "0") {
                //Node is Set variable node
                setAddConstantModal(true)
            }
        } else {
            console.log("added node", node)
        }
    }
    const connectionClick = (e, connection) => {
        let regex = /^[a-f\d]{24}$/i
        if (regex.test(connection.id)) {
            setSelectedConnection(connection.id)
            setAddMappingModal(true)
            connection.selected = false
            let edges = reactFlowInstance.getEdges()
            let index = edges.findIndex(({id}) => id === connection.id)
            edges[index] = connection
            reactFlowInstance.setEdges(edges)
        }
    }

    const onInit = (reactFlowInstance) => {
        setReactFlowInstance(reactFlowInstance)
    }

    const onDragStart = (event, nodeType) => {
        event.dataTransfer.setData("application/reactflow", nodeType)
        event.dataTransfer.effectAllowed = "move"
    }

    const onDragOver = React.useCallback((event) => {
        event.preventDefault()
        event.dataTransfer.dropEffect = "move"
    }, [])

    const onDrop = React.useCallback(
        (event) => {

            event.preventDefault()
            const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect()
            const type = event.dataTransfer.getData("application/reactflow")

            if (typeof type === "undefined" || !type) {
                return
            }

            const position = reactFlowInstance.project({
                x: event.clientX - reactFlowBounds.left,
                y: event.clientY - reactFlowBounds.top,
            })

            const newNode = {
                id: getId(),
                type,
                position,
                data: {label: `${type} node`},
            }

            setNodes((nds) => nds.concat(newNode))
        },
        [reactFlowInstance]
    )
    const setRecommendations = (e) => {
        setRecommendationIsSubmitting(true)
        setRecommendationSuccess(false)
        setRecommendationMessageShort("Generating recommendations")
        fetch("/api/connection/recommendations/" + id)
            .then((res) => res.json())
            .then((res) => {
                if (res["success"]) {
                    setNodes(res["data"]["nodes"])
                    setEdges(res["data"]["edges"])
                    setRecommendationSuccess(true)
                    setRecommendationMessageShort("Recommendations added")
                    setTimeout(() => {
                        setRecommendationIsSubmitting(false)
                    }, 2000)
                }
            })
    }

    const saveMapping = (e) => {
        e.preventDefault()
        fetch("/api/connection/save/" + id)
            .then((res) => res.json())
            .then((res) => {
                    if (res["state"] !== "Complete") {
                        console.log("Incomplete")
                    }
                    setFormIsSubmitting(true)
                    setFormMessageShort("Saving")
                    setTimeout(() => {
                        setFormIsSubmitting(false)
                        if (res["state"] == "Complete") {
                            setFormSuccess(true)
                            setFormMessageShort("Saved!")
                        } else {
                            setFormSuccess(false)
                            setIncompleteReason(res["reason"])
                            setIncompleteMappingList(res["incompleteMappings"])
                            setIncompleteMappingModal(true)
                        }
                        setTimeout(() => {
                            setTimeout(() => {
                                setFormSuccess(false)
                                setFormMessageShort("Saving")
                            }, 1500)
                        }, 1000)
                    }, 2000)
                }
            )
            .catch(error => {
                console.log(error)
            })
    }

    return (
        <div>
            <HeaderPanel aria-label="Header Panel" expanded={showConverterSidebar}>
                <div className="cds--modal-header">
                    <h2 className="cds--modal-header__label cds--type-delta">Drag a converter to translate schemas</h2>
                    <h3 className="cds--modal-header__heading cds--type-beta">Converters</h3>
                    <Button onClick={() => setShowConverterSidebar(!showConverterSidebar)} className="cds--modal-close">
                        <svg focusable="false" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"
                             fill="currentColor" width="20" height="20" viewBox="0 0 32 32" aria-hidden="true"
                             className="cds--modal-close__icon">
                            <path
                                d="M24 9.4L22.6 8 16 14.6 9.4 8 8 9.4 14.6 16 8 22.6 9.4 24 16 17.4 22.6 24 24 22.6 17.4 16 24 9.4z"/>
                        </svg>
                    </Button>
                </div>
                <div className="cds--modal-content">
                    <div className="dndnode input" onDragStart={(event) => onDragStart(event, "input")} draggable>
                        Input Node
                    </div>
                    <div className="dndnode" onDragStart={(event) => onDragStart(event, "default")} draggable>
                        Default Node
                    </div>
                    <div className="dndnode output" onDragStart={(event) => onDragStart(event, "output")} draggable>
                        Output Node
                    </div>
                </div>

            </HeaderPanel>
            {
                formError &&
                <InlineNotification className={"modal-notification"} kind="error" title="Error"
                                    subtitle={errorMsg}/>
            }
            {
                error ?
                    <div className="main-container">
                        <SkeletonPlaceholder className="visual-skeleton"/>
                    </div>
                    :
                    <ReactFlowProvider>
                        <div className="main-container" ref={reactFlowWrapper}>

                            <ReactFlow
                                nodes={nodes}
                                edges={edges}
                                onNodeClick={(e, node) => nodeClick(e, node)}
                                onEdgeClick={(e, connection) => connectionClick(e, connection)}
                                onNodesChange={onNodesChange}
                                onEdgesChange={onEdgesChange}
                                onConnect={addConnection}
                                onNodesDelete={deleteNode}
                                onEdgesDelete={deleteConnection}
                                onInit={onInit}
                                connectionMode={"loose" as ConnectionMode}
                                // @ts-ignore
                                connectionLineComponent={FlowConnectionLine}
                                onDrop={onDrop}
                                onDragOver={onDragOver}
                                fitView
                                edgeTypes={edgeTypes}
                                nodeTypes={nodeTypes}
                            >
                                <Controls/>
                                <Background color="#aaa" gap={16}/>
                                <Tile className="button-panel">
                                    <ButtonSet stacked>
                                        <Button kind="secondary"
                                                disabled={formIsSubmitting || formSuccess || formError || recommendationIsSubmitting}>Info</Button>
                                        {/*<Button kind="secondary" disabled={formIsSubmitting || formSuccess || formError}*/}
                                        {/*        onClick={() => setShowConverterSidebar(!showConverterSidebar)}>*/}
                                        {/*    Add a converter*/}
                                        {/*</Button>*/}
                                        {recommendationIsSubmitting ? (
                                            <Button kind="secondary">
                                                <InlineLoading
                                                    className={"button-loading"}
                                                    description={recommendationMessageShort}
                                                    status={recommendationSuccess ? "finished" : "active"}
                                                />
                                            </Button>
                                        ) : (
                                            <Button kind="secondary"
                                                    disabled={formIsSubmitting || formSuccess || formError}
                                                    onClick={e => setRecommendations(e)}>Get recommendations</Button>
                                        )}


                                        <Button kind="secondary"
                                                disabled={formIsSubmitting || formSuccess || formError || recommendationIsSubmitting}
                                                onClick={() => setAddConstantModal(!addConstantModal)}>Add a
                                            variable</Button>

                                        {formIsSubmitting || formSuccess ? (
                                            <Button kind="primary">
                                                <InlineLoading
                                                    className={"button-loading"}
                                                    description={formMessageShort}
                                                    status={formSuccess ? "finished" : "active"}
                                                />
                                            </Button>
                                        ) : (
                                            <Button
                                                kind="primary"
                                                type="submit"
                                                onClick={(e) => saveMapping(e)}
                                                disabled={recommendationIsSubmitting}
                                            >
                                                Save mapping
                                            </Button>
                                        )}
                                    </ButtonSet>

                                </Tile>

                            </ReactFlow>
                            <AddConnectionDetails id={id} open={connectionDetailsModal}
                                                  setOpen={setConnectionDetailsModal}/>
                            <ViewEndpointDetails node={selectedNode} open={nodeDetailsModal}
                                                 setOpen={setNodeDetailsModal}/>
                            <AddConnectionVariable id={id} open={addConstantModal} setOpen={setAddConstantModal}/>
                            <AddConnectionLowLevelFlow open={addMappingModal} setOpen={setAddMappingModal}
                                                       mappingId={selectedConnection}
                                                       setMappingId={setSelectedConnection}
                                                       connectionId={id}
                                                       deleteEndpointConnection={deleteConnectionWithMappingId}/>
                            <IncompleteMapping open={incompleteMappingModal} setOpen={setIncompleteMappingModal} id={id}
                                               reason={incompleteReason} incompleteAPIs={incompleteMappingList}/>
                        </div>
                    </ReactFlowProvider>
            }
        </div>

    )

}
export default ConnectionGenerator