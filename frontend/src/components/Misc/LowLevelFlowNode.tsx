import React from "react"
import {StringText, StringInteger, Boolean, Notebook, Table, LogoPython} from "@carbon/icons-react"
import {Handle, Position} from "react-flow-renderer"
import "./_lowLevelFlowNode.scss"

interface LowLevelFlowNodeInterface {
    data: any,
    isConnectable: boolean,
    targetPosition?: Position,
    sourcePosition?: Position,
}

export const LowLevelFlowNode: React.FC<LowLevelFlowNodeInterface> = ({
                                                                          data,
                                                                          isConnectable,
                                                                          targetPosition = undefined,
                                                                          sourcePosition = undefined
                                                                      }) => {
    return (
        <div className="target-node">
            {!(data.child && data.nodeType == "source") && targetPosition != undefined &&
                <Handle
                    type="target"
                    position={targetPosition}
                    isConnectable={isConnectable}

                />
            }
            <div className={data.type != "script" ? "target-node-label" : "target-node-label-script"}>
                {data.type == "string" &&
                    <StringText size={12} className="target-node-data-type-icon"/>
                }
                {data.type == "number" || data.type == "integer" &&
                    <StringInteger size={12} className="target-node-data-type-icon"/>
                }
                {data.type == "boolean" &&
                    <Boolean size={12} className="target-node-data-type-icon"/>
                }
                {data.type == "object" &&
                    <Notebook size={12} className="target-node-data-type-icon"/>
                }
                {data.type == "array" &&
                    <Table size={12} className="target-node-data-type-icon"/>
                }
                {data.type == "script" &&
                    <LogoPython size={12} className="target-node-data-type-icon"/>
                }
                {data.label}
            </div>
            {data.type != "script" &&
                <div className="target-node-type">
                    {data.type}
                </div>
            }
            {(data.required) &&
                <div className="target-node-required">
                    Required
                </div>
            }
            {("value" in data) &&
                <div className="target-node-value">
                    {data.value}
                </div>
            }
            {!(data.child && data.nodeType == "target") && sourcePosition != undefined &&
                <Handle
                    type="source"
                    position={sourcePosition}
                    isConnectable={isConnectable}
                />
            }
        </div>
    )
}
export default LowLevelFlowNode
