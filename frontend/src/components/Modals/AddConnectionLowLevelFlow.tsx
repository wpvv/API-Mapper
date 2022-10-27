import React from "react"

import {
    Button,
    ButtonSet,
    Column,
    ComposedModal,
    DataTableSkeleton,
    Grid,
    InlineNotification,
    ModalBody,
    ModalFooter,
    ModalHeader,
    SkeletonPlaceholder,
    ContentSwitcher,
    Switch,
    Tile,
} from "@carbon/react"
import ReactFlow, {
    addEdge,
    Background,
    ConnectionMode,
    Controls,
    ReactFlowProvider,
    useEdgesState,
    useNodesState,
    ConnectionLineComponent,
    Position, getConnectedEdges,
} from "react-flow-renderer"

import Elk, {ElkNode, ElkPrimitiveEdge} from "elkjs"
import LowLevelParameter from "../Tables/LowLevelFlowParameter"
import LowLevelEndpoint from "../Tables/LowLevelFlowEndpoint"
import LowLevelFlowNode from "../Misc/LowLevelFlowNode"
import LowLevelGroupNode from "../Misc/LowLevelGroupNode"
import EditEdge from "../Misc/EditEdge"
import DeleteEdge from "../Misc/DeleteEdge"
import FlowConnectionLine from "../Misc/FlowConnectionLine"
import "./_addConnectionLowLevelFlow.scss"
import AddLowLevelScript from "./AddLowLevelScript";
import ObjectID from "bson-objectid";

interface AddConnectionInterface {
    open: boolean,
    setOpen: (state: boolean) => void,
    mappingId: string,
    setMappingId: (id: string) => void,
    connectionId: string | undefined,
    deleteEndpointConnection: (id: string) => void,
}

export const AddConnectionLowLevelFlow: React.FC<AddConnectionInterface> = ({
                                                                                open,
                                                                                setOpen,
                                                                                mappingId,
                                                                                setMappingId,
                                                                                connectionId,
                                                                                deleteEndpointConnection,
                                                                            }) => {
    const [connectionName, setConnectionName] = React.useState("")
    const [names, setNames] = React.useState<string[]>([])
    const [sourceEndpoints, setSourceEndpoints] = React.useState<Array<{ id, name, dataType, nodeType }>>([])
    const [targetEndpoints, setTargetEndpoints] = React.useState<Array<{ id, name, dataType, required, nodeType }>>([])
    const [variables, setVariables] = React.useState<Array<{ id, name, type }>>([])
    const [scriptModal, setScriptModal] = React.useState(false)
    const [selectedScriptNode, setSelectedScriptNode] = React.useState({})
    const [sourceParameters, setSourceParameters] = React.useState<Array<{ id, name, dataType, in, required, nodeType }>>([])
    const [targetParameters, setTargetParameters] = React.useState<Array<{ id, name, dataType, in, required, nodeType }>>([])

    const [lowLevelNodes, setLowLevelNodes, onLowLevelNodesChange] = useNodesState([])
    const [lowLevelEdges, setLowLevelEdges, onLowLevelEdgesChange] = useEdgesState([])

    const [viewIndex, setViewIndex] = React.useState(0)
    const [loading, setLoading] = React.useState(true)
    const [darkMode, setDarkMode] = React.useState(false)
    const [formError, setFormError] = React.useState(false)
    const [errorMsg, setErrorMsg] = React.useState("")
    const edgeTypes = React.useMemo(() => ({editEdge: EditEdge, deleteEdge: DeleteEdge}), [])
    const nodeTypes = React.useMemo(() => ({targetNode: LowLevelFlowNode, groupNode: LowLevelGroupNode}), [])


    React.useEffect(() => {
        if (mappingId !== "") {
            setFormError(false)
            fetch("/api/schemamapping/table/" + connectionId + "/" + mappingId)
                .then((res) => res.json())
                .then((res) => {
                    if (res["success"]) {
                        setNames(res["applicationNames"])
                        setSourceEndpoints(res["dataSources"])
                        setTargetEndpoints(res["dataTargets"])
                        setVariables(res["dataVariables"])
                        setSourceParameters(res["dataSourceParameters"])
                        setTargetParameters(res["dataTargetParameters"])
                        fetch("/api/schemamapping/flow/" + connectionId + "/" + mappingId)
                            .then((res) => res.json())
                            .then(async (res) => {
                                if (res["success"]) {
                                    const layoutedNodes = await getLayoutedElk(res["targetNodes"], res["targetEdges"], res["sourceNodes"], res["sourceEdges"], res["variableNodes"], res["variableEdges"], res["scriptNodes"], res["edges"])
                                    setLowLevelNodes(layoutedNodes)
                                    setLowLevelEdges(res["edges"].concat(res["targetEdges"]).concat(res["sourceEdges"]).concat(res["variableEdges"]))
                                    setConnectionName(res["connectionName"])
                                    setLoading(false)
                                }
                            })
                            .catch(error => {
                                console.log(error)
                            })
                    } else {
                        setFormError(true)
                        setErrorMsg(res["message"])
                    }
                })
                .catch(error => {
                    console.log(error)
                })
        } else {
            setFormError(true)
            setErrorMsg("Mapping details not set")
        }
        if (document.documentElement.getAttribute("data-carbon-theme") === "g100") {
            setDarkMode(true)
        } else {
            setDarkMode(false)
        }
    }, [mappingId, open])

    const calculateWidth = () => {
        return 150
    }

    const calculateHeight = (node) => {
        if (("required" in node["data"] && node["data"]["required"]) || "value" in node["data"]) {
            if (node["data"]["label"].length > 16 || ("value" in node && node["data"]["value"].length > 16)) {
                return 80
            }
            return 70
        } else {
            return 40
        }
    }

    const findNode = (array, id) => {
        let result
        array.some(
            (child) =>
                (child.id === id && (result = child)) ||
                (result = findNode(child.children || [], id))
        )
        return result
    }

    const getNodesAsElk = (nodes) => {
        const elkNodes: ElkNode[] = []
        nodes.forEach((node) => {
            let append_node = {
                id: node.id,
                width: calculateWidth(),
                height: calculateHeight(node),
            }
            if (node.type === "groupNode") {
                append_node["children"] = []
                if (node.data?.required) {
                    append_node["layoutOptions"] = {
                        "elk.padding": "[left=20, top=60, right=20, bottom=20]",
                    }
                } else {
                    append_node["layoutOptions"] = {
                        "elk.padding": "[left=20, top=40, right=20, bottom=20]",
                    }
                }
            }
            if ("parentNode" in node) {
                append_node["parent"] = node["parentNode"]
                let parentNode = findNode(elkNodes, node.parentNode)
                parentNode?.children.push(append_node)
            } else {
                elkNodes.push(append_node)
            }
        })
        return elkNodes
    }

    const getEdgesAsElk = (edges) => {
        const elkEdges: ElkPrimitiveEdge[] = []
        edges.forEach((edge) => {
            elkEdges.push({
                id: edge.id,
                target: edge.target,
                source: edge.source,
            })
        })
        return elkEdges
    }

    const setPositionAndSize = (nodes, graph, position, offset) => {
        const returnNodes: any = []
        nodes.forEach((flowNode) => {
            const node = findNode(graph?.children, flowNode.id)
            if (node?.x && node?.y && node?.width && node?.height) {
                if (!node.parent) {
                    if (position === "right") {
                        flowNode.position = {
                            x: node.x + (offset.sourceOffset + 600),
                            y: node.y + (offset.variableOffset + 100),
                        }
                    }
                    if (position === "top") {
                        flowNode.position = {
                            x: node.x + 400,
                            y: node.y,
                        }
                    }
                    if (position === "left") {
                        flowNode.position = {
                            x: node.x,
                            y: node.y + (offset.variableOffset + 100),
                        }
                    }
                } else {
                    flowNode.position = {
                        x: node.x,
                        y: node.y,
                    }
                }
                if (node?.children) {
                    flowNode.style = {
                        height: node.height + 8,
                        width: node.width
                    }
                }
                if (position === "top" && (node.y + node.height) > offset.variableOffset) {
                    offset.variableOffset = node.y + node.height
                }
                if (position === "left" && (node.x + node.width) > offset.sourceOffset) {
                    offset.sourceOffset = node.x + node.width
                }
                returnNodes.push(flowNode)
            }
        })
        return returnNodes
    }

    const getLayoutedElk = async (targetNodes, targetEdges, sourceNodes, sourceEdges, variableNodes, variableEdges, scriptNodes, edges) => {
        const elk = new Elk()
        let offset = {variableOffset: 0, sourceOffset: 0}
        let nodes: any = []
        let graph = {
            id: "root",
            "layoutOptions": {},
            children: [
                {
                    id: "target",
                    layoutOptions: {
                        "elk.direction": "LEFT",
                    },
                    children: getNodesAsElk(targetNodes),
                    edges: getEdgesAsElk(targetEdges),
                },
                {
                    id: "variable",
                    layoutOptions: {
                        "elk.direction": "DOWN",
                    },
                    children: getNodesAsElk(variableNodes),
                    edges: getEdgesAsElk(variableEdges),
                },
                {
                    id: "source",
                    layoutOptions: {
                        "elk.direction": "LEFT",
                    },
                    children: getNodesAsElk(sourceNodes),
                    edges: getEdgesAsElk(sourceEdges),
                },
                {
                    id: "script",
                    children: getNodesAsElk(scriptNodes),
                }
            ],
            edges: getEdgesAsElk(edges)
        }
        const elkGraph = await elk.layout(graph).catch(e => console.log(e))
        nodes = nodes.concat(setPositionAndSize(variableNodes, elkGraph, "top", offset))
        nodes = nodes.concat(setPositionAndSize(targetNodes, elkGraph, "left", offset))
        nodes = nodes.concat(setPositionAndSize(sourceNodes, elkGraph, "right", offset))
        nodes = nodes.concat(scriptNodes)
        return nodes
    }
    const findNodesWithIds = (params) => {
        return [lowLevelNodes.find(({id}) => id === params["target"]), lowLevelNodes.find(({id}) => id === params["source"])]
    }
    const findRealTargetAndSource = (params) => {
        const nodes: any = findNodesWithIds(params)
        let sourceNode = nodes.find(({data}) => data?.nodeType === "source")
        let targetNode = nodes.find(({data}) => data?.nodeType === "target")
        if (!sourceNode) {
            sourceNode = nodes.find(({data}) => data?.nodeType === "variable")
        } else if (!targetNode) {
            targetNode = nodes.find(({data}) => data?.nodeType === "variable")
        }
        return [sourceNode, targetNode]
    }

    const checkCompatibilityConnection = (sourceNode, targetNode) => {
        let source = sourceNode?.data.dataType
        let target = targetNode?.data.dataType
        if (target === "string" || target === "null") {
            return true
        } else if (target === "number" || target === "integer") {
            return source === "integer" || source === "number" || source === "boolean"
        } else if (target === "boolean") {
            return source === "boolean"
        } else return false
    }

    const checkScriptConnection = (params) => {
        const nodes: any = findNodesWithIds(params)
        return (nodes[0]?.data?.type === "script" || nodes[1]?.data?.type === "script")
    }

    const checkInArrayStatus = (sourceNode, targetNode) => {
        return sourceNode.data.inArray === targetNode.data.inArray
    }

    const addConnection = (params) => {
        if (!checkScriptConnection(params)) {
            let [sourceNode, targetNode] = findRealTargetAndSource(params)
            if (sourceNode !== undefined && targetNode !== undefined) {
                if (checkCompatibilityConnection(sourceNode, targetNode)) {
                    if (checkInArrayStatus(sourceNode, targetNode)) {
                        fetch("/api/schemamapping/flow/edge/" + connectionId + "/" + mappingId, {
                            method: "POST",
                            mode: "cors",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify({
                                source: sourceNode,
                                target: targetNode
                            })
                        }).then(res => res.json())
                            .then(res => {
                                if (!res["success"]) {
                                    setFormError(true)
                                    setErrorMsg("Adding of schema mapping failed, check logs")
                                } else {
                                    let edge = {
                                        id: res["id"],
                                        source: sourceNode.id,
                                        target: targetNode.id,
                                        sourceHandle: "",
                                        targetHandle: "",
                                        animated: true,
                                        type: "deleteEdge",
                                        zIndex: 1,
                                    }
                                    setLowLevelEdges((eds) => addEdge(edge, eds))
                                }
                            })
                            .catch(error => {
                                console.log(error)
                            })
                    } else {
                        setFormError(true)
                        setErrorMsg("A schema mapping connection can only be made with both elements in an array or neither")
                    }
                } else {
                    setFormError(true)
                    setErrorMsg("A schema mapping connection can only be made when both data types are the same (string <-> string, integer <-> integer)")
                }

            } else {
                setFormError(true)
                setErrorMsg("A connection can only be made between either an source(right) and target(left) or either with a variable(top)")
            }
        } else {
            addScriptConnection(params)
        }
    }

    const deleteEdge = (edgeId) => {
        let index = lowLevelEdges.findIndex(({id}) => id === edgeId)
        lowLevelEdges.splice(index, 1)
        setLowLevelEdges([...lowLevelEdges])
    }

    const deleteNode = (nodeId) => {
        let index = lowLevelNodes.findIndex(({id}) => id === nodeId)
        lowLevelNodes.splice(index, 1)
        setLowLevelNodes([...lowLevelNodes])
    }

    const deleteConnection = (e, connection) => {
        if (connection.type == "deleteEdge") {
            fetch("/api/schemamapping/flow/edge/" + connectionId + "/" + mappingId + "/" + connection.id, {
                method: "DELETE",
                mode: "cors",
            }).then(response => response.json())
                .then(response => {
                    if (!response["success"]) {
                        setFormError(true)
                        setErrorMsg(response["message"])
                    } else {
                        deleteEdge(connection.id)
                    }
                })
                .catch(error => {
                    console.log(error)
                })
        }
    }
    const reverseSourceAndTarget = (node) => {
        console.log("reversing data")
        if (node.data.source !== -1) {
            node.data.target = node.data.source
            node.data.source = -1
        } else {
            node.data.source = node.data.target
            node.data.target = -1
        }
        return node
    }

    const addScriptConnection = (params) => {
        const nodes: any = findNodesWithIds(params)
        let scriptNode = nodes.find(({data}) => data?.type === "script")
        const connectedNode = nodes.find(({data}) => data?.type !== "script")
        if (!connectedNode.data.nodeType.startsWith("entire") && connectedNode.data.nodeType !== "variable") {
            setFormError(true)
            setErrorMsg("A connection with a script can only be made with an entire source or target (object and array) not with individual elements")
            return
        }
        let connectedType
        if (connectedNode.data.nodeType.startsWith("entire")) {
            connectedType = connectedNode.data.nodeType.replace("entire-", "")
            if (scriptNode.data[connectedType] !== -1) {
                scriptNode = reverseSourceAndTarget(scriptNode)
            }
        } else {
            if (scriptNode.data.source !== -1) {
                connectedType = "target"
            }
            else{
                connectedType = "source"
            }
        }
        const nodeList = lowLevelNodes
        const nodeIndex = lowLevelNodes.findIndex(({id}) => id === scriptNode.id)
        if (nodeIndex !== -1) {
            scriptNode.data[connectedType] = connectedNode.id
            nodeList[nodeIndex] = scriptNode
            setLowLevelNodes(nodeList)
            let edge = {
                id: ObjectID().toHexString(),
                source: ((connectedType === "source") ? connectedNode.id : scriptNode.id),
                target: ((connectedType === "target") ? connectedNode.id : scriptNode.id),
                sourceHandle: "",
                targetHandle: "",
                animated: true,
                type: "smoothstep",
                zIndex: 1,
            }
            setLowLevelEdges((eds) => addEdge(edge, eds))
            if (scriptNode.data.source !== -1 && scriptNode.data.target !== -1) {
                fetch("/api/connection/script/" + connectionId + "/" + mappingId + "/" + scriptNode.id, {
                    method: "POST",
                    mode: "cors",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        source: scriptNode.data.source,
                        target: scriptNode.data.target,
                        position: scriptNode.position,
                    })
                }).then(res => res.json())
                    .then(res => {
                        if (!res["success"]) {
                            setFormError(true)
                            setErrorMsg("Adding of schema mapping failed, check logs")
                        }
                    })
            }
        }
    }

    const deleteScriptNode = (node) => {
        if (node.data.source !== -1) {
            deleteEdge(node.data.source)
        }
        if (node.data.target !== -1) {
            deleteEdge(node.data.target)
        }
        deleteNode(node)
    }

    const addScriptNode = React.useCallback(() => {
        const id = ObjectID().toHexString()
        const newNode = {
            id: id,
            data: {
                label: "Python Script Node",
                type: "script",
                source: -1,
                target: -1,
            },
            type: "targetNode",
            position: {
                x: 600,
                y: 600
            },
            targetPosition: Position.Right,
            sourcePosition: Position.Left,
        }
        setLowLevelNodes((nds) => nds.concat(newNode))
    }, [setLowLevelNodes])

    const nodeClick = (e, node) => {
        if (node?.data?.type === "script") {
            setSelectedScriptNode(node)
            setScriptModal(true)
        }
    }

    const close = () => {
        setMappingId("")
        setNames([])
        setSourceEndpoints([])
        setTargetEndpoints([])
        setVariables([])
        setSourceParameters([])
        setTargetParameters([])

        setLowLevelNodes([])
        setLowLevelEdges([])

        setFormError(false)
        setErrorMsg("")
        setLoading(true)
        setOpen(false)
    }

    return (
        <ComposedModal open={open} onClose={() => close()} size="lg">
            <ModalHeader closeModal={() => close()}>
                <h3 className="bx--modal-header__heading">Connecting {connectionName}</h3>
            </ModalHeader>
            <ModalBody className="low-level-modal" aria-label="Add an low-level mapping">
                <ContentSwitcher onChange={(obj) => setViewIndex(obj.index)}>
                    <Switch name="table" text="Table view"/>
                    <Switch name="visual" text="Flow editor view"/>
                </ContentSwitcher>
                <Grid>
                    {viewIndex === 0 &&
                        <Column lg={16}>
                            <div className="low-level-container">
                                {loading ?
                                    <DataTableSkeleton columnCount={4} rowCount={2}/>
                                    :
                                    [(Object(sourceParameters).length !== 0 &&
                                        <LowLevelParameter name={names[0]} rows={sourceParameters}
                                                           dataSources={variables}/>
                                    )]
                                }
                                {loading ?
                                    <DataTableSkeleton columnCount={4} rowCount={2}/>
                                    :
                                    [(Object(targetParameters).length !== 0 &&
                                        <LowLevelParameter name={names[1]} rows={targetParameters}
                                                           dataSources={[...variables, ...sourceEndpoints]}/>
                                    )]
                                }
                                {loading ?
                                    <DataTableSkeleton columnCount={4} rowCount={2}/>
                                    :
                                    [(Object(targetEndpoints).length !== 0 &&
                                        <LowLevelEndpoint name={names[1]} rows={targetEndpoints}
                                                          dataSources={[...variables, ...sourceEndpoints]}/>
                                    )]
                                }
                            </div>
                        </Column>
                    }
                    {viewIndex === 1 &&
                        <Column lg={16} xlg={16} max={16}>
                            {loading ?
                                <div className="low-level-container">
                                    <SkeletonPlaceholder className="low-level-skeleton"/>
                                </div>
                                :
                                [(mappingId !== "" &&
                                    <ReactFlowProvider>
                                        <div className="low-level-container">
                                            <ReactFlow
                                                id={"lowLevelMapping"}
                                                nodes={lowLevelNodes}
                                                edges={lowLevelEdges}
                                                onNodesChange={onLowLevelNodesChange}
                                                onEdgesChange={onLowLevelEdgesChange}
                                                onConnect={addConnection}
                                                onNodeClick={(e, node) => nodeClick(e, node)}
                                                onEdgeClick={deleteConnection}
                                                edgeTypes={edgeTypes}
                                                nodeTypes={nodeTypes}
                                                connectionMode={ConnectionMode.Loose}
                                                connectionLineComponent={FlowConnectionLine as ConnectionLineComponent}
                                                connectionLineStyle={{zIndex: 100}}
                                                fitView
                                            >
                                                <Controls/>
                                                <Background color="#aaa" gap={16}/>
                                                <Tile className="low-level-button-panel">
                                                    <ButtonSet stacked>
                                                        <Button kind="secondary" onClick={addScriptNode}
                                                        >Add a script</Button>
                                                    </ButtonSet>

                                                </Tile>
                                            </ReactFlow>
                                        </div>
                                    </ReactFlowProvider>
                                )]
                            }
                        </Column>
                    }
                </Grid>
            </ModalBody>
            {
                formError &&
                <InlineNotification className={"modal-notification"} kind="error" title="Error"
                                    subtitle={errorMsg}/>
            }
            <ModalFooter>
                <Button
                    kind="danger"
                    onClick={() => {
                        deleteEndpointConnection(mappingId)
                        close()
                    }}>
                    Delete Connection
                </Button>
                <Button
                    kind="primary"
                    onClick={() => close()}
                >
                    Save Connection
                </Button>
            </ModalFooter>
            <AddLowLevelScript open={scriptModal} setOpen={setScriptModal} connectionId={connectionId}
                               mappingId={mappingId} scriptNode={selectedScriptNode}
                               setScriptNode={setSelectedScriptNode} deleteScriptNode={deleteScriptNode}/>
        </ComposedModal>
    )
}
export default AddConnectionLowLevelFlow