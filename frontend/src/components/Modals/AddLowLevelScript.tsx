import React from "react"
import {Buffer} from "buffer"
import {
    Button,
    ComposedModal,
    InlineNotification,
    ModalBody,
    ModalFooter,
    ModalHeader,
} from "@carbon/react"
import AceEditor from "react-ace"

import "ace-builds/src-noconflict/mode-python"
import "ace-builds/src-noconflict/snippets/python"
import "ace-builds/src-noconflict/theme-ambiance"
import "ace-builds/src-noconflict/theme-github"
import "ace-builds/src-noconflict/ext-language_tools"
import "ace-builds/webpack-resolver"

interface AddConnectionDetailsInterface {
    open: boolean,
    setOpen: (state: boolean) => void,
    connectionId: string | undefined,
    mappingId: string,
    scriptNode: any,
    setScriptNode: (scriptNode: any) => void,
    deleteScriptNode: (scriptNodeId: string) => void,
}

export const AddLowLevelScript: React.FC<AddConnectionDetailsInterface> = ({
                                                                               open,
                                                                               setOpen,
                                                                               connectionId,
                                                                               mappingId,
                                                                               scriptNode,
                                                                               setScriptNode,
                                                                               deleteScriptNode,
                                                                           }) => {
    const [newScript, setNewScript] = React.useState(false)
    const [scriptContent, setScriptContent] = React.useState("")
    const [darkMode, setDarkMode] = React.useState(false)
    const [formError, setFormError] = React.useState(false)
    const [errorMsg, setErrorMsg] = React.useState("")

    React.useEffect(() => {
        if (Object.keys(scriptNode).length !== 0 && connectionId !== "" && mappingId !== "" && scriptNode?.id !== "") {
            if (scriptNode.data.source !== -1 && scriptNode.data.target !== -1) {
                fetch("/api/connection/script/" + connectionId + "/" + mappingId + "/" + scriptNode.id)
                    .then((res) => res.json())
                    .then((res) => {
                        if (res["success"]) {
                            setScriptContent(Buffer.from(res["config"]["script"], "base64").toString())
                        } else {
                            setFormError(true)
                            setErrorMsg(res["message"])
                        }
                    })
                    .catch(error => {
                        console.log(error)
                    })
            } else {
                setNewScript(true)
                setFormError(true)
                setErrorMsg("You can add a script when the script node is connected to both APIs")
            }
        }

        if (document.documentElement.getAttribute("data-carbon-theme") === "g100") {
            setDarkMode(true)
        } else {
            setDarkMode(false)
        }
    }, [scriptNode, connectionId, mappingId])

    const close = () => {
        setOpen(false)
        setScriptNode({})
        setErrorMsg("")
        setScriptContent("")
        setFormError(false)
        setNewScript(false)
    }

    const saveScript = () => {
        fetch("/api/connection/script/" + connectionId + "/" + mappingId + "/" + scriptNode.id, {
            method: "PUT",
            mode: "cors",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                script: Buffer.from(scriptContent).toString("base64"),
                position: scriptNode.position,
            })
        }).then(res => res.json())
            .then(res => {
                if (!res["success"]) {
                    setFormError(true)
                    setErrorMsg(res["message"])
                }
                else{
                    close()

                }
            })
    }

    const deleteScript = () => {
        if (!newScript) {
            fetch("/api/connection/script/" + connectionId + "/" + mappingId + "/" + scriptNode.id, {
                method: "DELETE",
                mode: "cors",
            }).then(response => response.json())
                .then(response => {
                    if (!response["success"]) {
                        setFormError(true)
                        setErrorMsg(response["message"])
                    } else {
                        deleteScriptNode(scriptNode)
                        close()
                    }

                })
                .catch(error => {
                    console.log(error)
                })
        } else {
            deleteScriptNode(scriptNode)
            close()
        }
    }

    return (
        <ComposedModal open={open} onClose={close} size="md">
            <ModalHeader label="Add your own Python data converter script" title={"Python Script"}
                         buttonOnClick={close}/>
            <ModalBody>
                {!newScript &&
                    [(darkMode ?
                            <AceEditor
                                style={{fontFamily: "inherit!important"}}
                                width="100%"
                                height="14rem"
                                mode="python"
                                theme="ambiance"
                                placeholder=""
                                fontSize={14}
                                onChange={setScriptContent}
                                value={scriptContent}
                                highlightActiveLine={false}
                                showPrintMargin={false}
                            />
                            :
                            <AceEditor
                                style={{fontFamily: "inherit!important"}}
                                width="100%"
                                height="14rem"
                                mode="python"
                                theme="github"
                                placeholder=""
                                fontSize={14}
                                onChange={setScriptContent}
                                value={scriptContent}
                                highlightActiveLine={false}
                                showPrintMargin={false}

                            />
                    )]
                }
            </ModalBody>
            {formError &&
                <InlineNotification className={"modal-notification"} kind="error" title="Error"
                                    subtitle={errorMsg}/>
            }
            <ModalFooter>
                <Button
                    kind="danger"
                    onClick={() => {
                        deleteScript()
                    }}>
                    Delete Script
                </Button>
                <Button
                    disabled={newScript}
                    kind="primary"
                    onClick={() => {
                        saveScript()
                    }}>
                    Save Script
                </Button>
            </ModalFooter>
        </ComposedModal>
    )
}
export default AddLowLevelScript