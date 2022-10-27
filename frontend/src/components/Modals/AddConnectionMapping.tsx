import React from "react"
import {
    InlineNotification,
    Modal,
    Stack,
    StructuredListBody,
    StructuredListCell,
    StructuredListHead,
    StructuredListRow,
    StructuredListWrapper,
    Tag,
} from "@carbon/react"

interface AddConnectionInterface {
    open: boolean,
    setOpen: (state: boolean) => void,
    connection: object,
    connectionId: string | undefined,
}

export const AddConnectionMapping: React.FC<AddConnectionInterface> = ({open, setOpen, connection, connectionId}) => {
    const [application1, setApplication1] = React.useState({})
    const [application2, setApplication2] = React.useState({})
    const [nodes, setNodes] = React.useState({})
    const [constants, setConstants] = React.useState<Array<{ "name", "value", "description" }>>([])
    const [darkMode, setDarkMode] = React.useState(false)
    const [formError, setFormError] = React.useState(false)
    const [errorMsg, setErrorMsg] = React.useState("")

    React.useEffect(() => {
        if (Object.keys(connection).length !== 0) {
            setApplication1(connection["application1"])
            setApplication2(connection["application2"])
            for(const node in connection){
                fetch('/api/connection/flow/get/node/' + connection[node]["applicationId"], {
                    method: 'POST',
                    mode: 'cors',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        path: connection[node]["endpointPath"],
                        operation: connection[node]["endpointOperation"]
                    })
                })
                    .then((res) => res.json())
                    .then((res) => {
                        if(res["success"]) {
                            if (node === "application1") {
                                setApplication1(res["data"])
                            } else {
                                setApplication2(res["data"])
                            }
                        }
                    })
                    .catch(error => {
                        console.log(error)
                    })
            }

        } else {
            setFormError(true)
            setErrorMsg("Mapping details not set")
        }
        fetch('/api/connection/get/constants/' + connectionId)
            .then((res) => res.json())
            .then((res) => {
                if (res["success"]) {
                    if ("data" in res && res["data"]) {
                        setConstants(res["data"])
                    }
                }

            })
            .catch(error => {
                console.log(error)
            })
    if (document.documentElement.getAttribute('data-carbon-theme') === "g100") {
        setDarkMode(true)
    } else {
        setDarkMode(false)
    }
}, [connection])

return (
    <Modal
        modalHeading={"Connecting " + application1["path"] + " and " + application2["path"]}
        modalLabel="API connection Details"
        open={open}
        passiveModal
        onRequestClose={() => setOpen(false)}
    >
        {JSON.stringify(connection)}
        {JSON.stringify(constants)}
    </Modal>
)
}
export default AddConnectionMapping