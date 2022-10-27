import React from "react"
import {StringText, StringInteger, Boolean, Notebook, Table} from "@carbon/icons-react"
import {Handle, Position} from "react-flow-renderer"
import "./_highLevelFlowNode.scss"

interface HighLevelFlowNodeInterface {
    data: any,
    isConnectable: boolean,
    targetPosition?: Position,
    sourcePosition?: Position,
}

export const HighLevelFlowNode: React.FC<HighLevelFlowNodeInterface> = ({
                                                                            data,
                                                                            isConnectable,
                                                                            targetPosition= undefined,
                                                                            sourcePosition = undefined
                                                                        }) => {
    return (
        <div className={"high-level-node node-" + data.operation}>
            {targetPosition != undefined &&
                <Handle
                    type="target"
                    position={targetPosition}
                    isConnectable={isConnectable}

                />
            }
            <div className="high-level-node-label">
                {data.label}
            </div>
            <div className="high-level-node-operation">
                {data.operation.toUpperCase()}
            </div>
            {sourcePosition != undefined &&
                <Handle
                    type="source"
                    position={sourcePosition}
                    isConnectable={isConnectable}
                />
            }
        </div>
    )
}
export default HighLevelFlowNode
