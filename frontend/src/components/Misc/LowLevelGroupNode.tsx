import React from "react"
import {StringText, StringInteger, Boolean, Notebook, Table} from "@carbon/icons-react"
import {Handle, Position} from "react-flow-renderer"
import "./_lowLevelGroupNode.scss"

interface LowLevelGroupNodeInterface {
    data: any,
    isConnectable: boolean,
    targetPosition?: Position,
    sourcePosition?: Position,
}

export const LowLevelGroupNode: React.FC<LowLevelGroupNodeInterface> = ({
                                                                            data,
                                                                            isConnectable,
                                                                            targetPosition = undefined,
                                                                            sourcePosition = undefined
                                                                        }) => {
    return (
        <div className="group-node">
            <div className="group-node-label">
                {data.type == "object" &&
                    <Notebook size={16} className="group-node-data-type-icon"/>
                }
                {data.type == "array" &&
                    <Table size={16} className="group-node-data-type-icon"/>
                }
                {data.label == "array-item" ?
                    "Object in Array"
                    :
                    data?.label
                }
            </div>
            {!data.child && targetPosition != undefined &&
                <Handle type="target" position={targetPosition} isConnectable={isConnectable}/>
            }
            {!data.child && sourcePosition != undefined &&
                <Handle type="source" position={sourcePosition} isConnectable={isConnectable}/>
            }
            {(data.required) &&
                <div className="group-node-required">
                    Required
                </div>
            }
        </div>
    )
}
export default LowLevelGroupNode