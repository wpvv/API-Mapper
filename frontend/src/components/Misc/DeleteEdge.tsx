import React from "react"
import {getEdgeCenter, getSmoothStepPath} from "react-flow-renderer"
import {TrashCan} from "@carbon/react/icons"
import "./_deleteEdge.scss"

const foreignObjectSize = 16


export default function DeleteEdge({
                                       id,
                                       source,
                                       target,
                                       sourceX,
                                       sourceY,
                                       targetX,
                                       targetY,
                                       sourcePosition,
                                       targetPosition,
                                       style = {},
                                       markerEnd = "",
                                       data = {offset: 0},
                                       zIndex = 100,
                                   }) {
    let [edgeCenterX, edgeCenterY] = getEdgeCenter({
        sourceX,
        sourceY,
        targetX,
        targetY,
    })
    const edgePath = getSmoothStepPath({
        sourceX,
        sourceY,
        centerX: edgeCenterX - data.offset,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
        borderRadius: 10,
    })

    return (
        <>
            <path
                id={id}
                style={style}
                className="react-flow__edge-path"
                d={edgePath}
                markerEnd={markerEnd}
            />
            <foreignObject
                width={foreignObjectSize}
                height={foreignObjectSize}
                x={(edgeCenterX - data.offset) - foreignObjectSize / 2}
                y={edgeCenterY - foreignObjectSize / 2}
                style={{textAlign: "center"}}
                requiredExtensions="http://www.w3.org/1999/xhtml"
            >
                <div className={"edge-icon-delete"}>
                    <TrashCan size={10}/>
                </div>
            </foreignObject>
        </>
    )
}
