import React from "react"
import {
    Button,
    ComposedModal,
    Form,
    InlineNotification,
    ModalBody,
    ModalFooter,
    ModalHeader,
    NumberInput,
    TextInput,
} from "@carbon/react";

interface AddConnectionDetailsInterface {
    open: boolean,
    setOpen: (state: boolean) => void,
    id: string | undefined,

}
export const AddConnectionDetails: React.FC<AddConnectionDetailsInterface> = ({open, setOpen, id}) => {
    const [applicationName1, setApplicationName1] = React.useState("")
    const [applicationName2, setApplicationName2] = React.useState("")
    const [version, setVersion] = React.useState(0.1)
    const [description, setDescription] = React.useState("")
    const [formError, setFormError] = React.useState(false)
    const [errorMsg, setErrorMsg] = React.useState("")

    React.useEffect(() => {
        if(id !== "") {
            fetch("/api/connection/" + id)
                .then((res) => res.json())
                .then((res) => res["config"])
                .then((res) => {
                    setApplicationName1(res[res["applicationIds"][0]])
                    setApplicationName2(res[res["applicationIds"][1]])
                    if (!res["complete"]) {
                        if ("version" in res) {
                            setVersion(res["version"])
                        }
                        if ("description" in res) {
                            setDescription(res["description"])
                        }
                    }
                })
                .catch(error => {
                    console.log(error)
                })
        }
        else{
            setFormError(true)
            setErrorMsg("Connection ID not set")
        }
    }, [id])

    const close = () => {
        setOpen(false)
        setVersion(0.1)
        setDescription("")

    }

    const saveDetails  = (e) => {
        e.preventDefault()
        fetch("/api/connection/" + id, {
            method: "PUT",
            mode: "cors",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                description: description,
                version: version
            })
        }).then(response => response.json())
            .then(response => {
                if (!response["success"]) {
                    setFormError(true)
                    setErrorMsg(response["message"])
                } else {
                    close()
                }
            })
            .catch(error => {
                console.log(error)
            })
    }

    return(
        <ComposedModal open={open} onClose={() => false} preventCloseOnClickOutside size="md">
            <ModalHeader closeClassName={"hide-close-button"} label="Add Connection details" title={"Connecting " + applicationName1 + " and " + applicationName2} >
                <h3 className="bx--modal-header__heading"></h3>
            </ModalHeader>
            <ModalBody>
                <p style={{marginBottom: "1rem"}}>
                   Before we start mapping the two selected applications, you need to add a version number and a
                    description of the application mapping that you are currently making.
                </p>
                <Form id="connectionDetails" onSubmit={e => saveDetails(e)}>

                    <TextInput id="description" style={{marginBottom: "1rem"}}
                               labelText="Connection Description"
                               required
                               value={description}
                               onChange={e => {
                                   setDescription(e.currentTarget.value)
                               }}/>

                    <NumberInput id="version" style={{fontFamily: "unset"}} label="Connection Version" required step={0.1}
                                 value={version} min={0.1} onChange={e => setVersion(e.imaginaryTarget.valueAsNumber)} iconDescription="change version number"/>

                </Form>
            </ModalBody>
            {formError &&
                <InlineNotification className={"modal-notification"} kind="error" title="Error"
                                    subtitle={errorMsg}/>
            }
            <ModalFooter>
                <Button
                    kind="primary"
                    type="submit"
                    form="connectionDetails"
                >
                    Save
                </Button>
            </ModalFooter>
        </ComposedModal>
    )
}
export default AddConnectionDetails