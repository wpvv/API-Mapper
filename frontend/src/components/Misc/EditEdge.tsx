import React from "react"
import {getEdgeCenter, getSmoothStepPath} from "react-flow-renderer"
import {Edit} from "@carbon/react/icons"
import "./_editEdge.scss"

const foreignObjectSize = 12


export default function EditEdge({
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
                                     data = {offset: 0, recommendation: false},
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
                className={!data.recommendation ? "react-flow__edge-path" : "react-flow__edge-path recommendation-edge"}
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
                <div className={!data.recommendation ? "edge-icon-edit" : "edge-icon-edit recommendation-edge-icon"}>
                    <Edit size={foreignObjectSize}/>
                </div>
            </foreignObject>
        </>
    )
}
