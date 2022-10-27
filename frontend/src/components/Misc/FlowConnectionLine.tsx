import React from "react"
import {getSmoothStepPath} from "react-flow-renderer"

export default ({
                    sourceX,
                    sourceY,
                    sourcePosition,
                    targetX,
                    targetY,
                    targetPosition,
                }) => {
    const edgePath = getSmoothStepPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition
    })
    return (
        <g>
            <path
                fill="none"
                stroke="#b1b1b7"
                strokeWidth={1}
                className="animated"
                d={edgePath}
            />
        </g>
    )
}