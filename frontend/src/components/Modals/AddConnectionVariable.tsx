import React from "react"
import {
    InlineNotification,
    Modal,
    OverflowMenu,
    OverflowMenuItem,
    StructuredListBody,
    StructuredListCell,
    StructuredListHead,
    StructuredListRow,
    StructuredListWrapper,
    TextArea,
    TextInput
} from "@carbon/react"

interface AddConnectionVariableInterface {
    open: boolean,
    setOpen: (state: boolean) => void,
    id: string | undefined,
}

export const AddConnectionVariable: React.FC<AddConnectionVariableInterface> = ({open, setOpen, id}) => {
    const [name, setName] = React.useState("")
    const [value, setValue] = React.useState("")
    const [description, setDescription] = React.useState("")

    const [editMode, setEditMode] = React.useState(false)
    const [selectedVariable, setSelectedVariable] = React.useState(-1)
    const [refresh, setRefresh] = React.useState(false)
    const [variables, setVariables] = React.useState<Array<{ "id", "name", "value", "type", "description" }>>([])

    const [formError, setFormError] = React.useState(false)
    const [errorMsg, setErrorMsg] = React.useState("")

    React.useEffect(() => {
        if (id !== "") {
            fetch("/api/connection/get/variables/" + id)
                .then((res) => res.json())
                .then((res) => {
                    if (res["success"]) {
                        if ("data" in res && res["data"]) {
                            setVariables(res["data"])
                        }
                        if (refresh) {
                            setRefresh(false)
                        }
                    }

                })
                .catch(error => {
                    console.log(error)
                })

        } else {
            setFormError(true)
            setErrorMsg("Connection ID not set")

        }
    }, [id, open, refresh])

    const saveVariable = (e) => {
        e.preventDefault()
        if (!editMode) {
            fetch("/api/connection/variable/" + id, {
                method: "POST",
                mode: "cors",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    name: name,
                    value: value,
                    description: description,
                })
            }).then(response => response.json())
                .then(response => {
                    if (!response["success"]) {
                        setFormError(true)
                        setErrorMsg(response["message"])
                    } else {
                        setRefresh(true)
                        initialState()
                    }
                })
                .catch(error => {
                    console.log(error)
                })
        } else {
            fetch("/api/connection/variable/" + id, {
                method: "PUT",
                mode: "cors",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    id: variables[selectedVariable]["id"],
                    name: name,
                    value: value,
                    description: description,
                })
            }).then(response => response.json())
                .then(response => {
                    if (!response["success"]) {
                        setFormError(true)
                        setErrorMsg(response["message"])
                    } else {
                        setRefresh(true)
                        initialState()
                        setEditMode(false)
                        setSelectedVariable(-1)
                    }
                })
                .catch(error => {
                    console.log(error)
                })
        }
    }
    const editVariable = (e, i) => {
        e.preventDefault()
        setEditMode(true)
        setSelectedVariable(i)
        setName(variables[i].name)
        setValue(variables[i].value)
        setDescription(variables[i].description)

    }

    const deleteVariable = (e, i) => {
        e.preventDefault()
        fetch("/api/connection/variable/" + id + "/" + variables[1].id, {
            method: "DELETE",
            mode: "cors",
        })
            .then(response => response.json())
            .then(response => {
                if (!response["success"]) {
                    setFormError(true)
                    setErrorMsg(response["message"])
                } else {
                    variables.splice(i, 1)
                    setVariables([...variables])
                }
            })
            .catch(error => {
                console.log(error)
            })
    }

    const initialState = () => {
        setName("")
        setValue("")
        setDescription("")
    }

    const close = () => {
        setOpen(false)
        initialState()

        setVariables([])
        setEditMode(false)
        setSelectedVariable(-1)
        setFormError(false)
        setErrorMsg("")
        setRefresh(false)
    }
    return (
        <Modal
            modalHeading="Add a connection wide variable"
            modalLabel="Add a variable"
            open={open}
            onRequestClose={() => close()}
            primaryButtonText= {editMode ? "Save" : "Add"}
            secondaryButtonText="Cancel"
            onRequestSubmit={(e) => saveVariable(e)}
        >
            <p>Sometimes a variable is needed to make a connection work. For example the project id or some kind of
                application
                project identifier is needed. This can be added as a variable. Another example is that you want to
                temporarily save data to use on a connection between other endpoints. Variables can be used as data
                target and source, if used as target the value that you have given will be overwritten </p>
            {(variables.length !== 0 && !editMode) &&
              <div>
                <h6 className="variable-title">Current variables: </h6>
                <StructuredListWrapper>
                  <StructuredListHead>
                    <StructuredListRow head>
                      <StructuredListCell head>Name</StructuredListCell>
                      <StructuredListCell head>Value</StructuredListCell>
                      <StructuredListCell head>Type</StructuredListCell>
                      <StructuredListCell head>Description</StructuredListCell>
                      <StructuredListCell head> </StructuredListCell>
                    </StructuredListRow>
                  </StructuredListHead>
                  <StructuredListBody>
                      {variables.map((variable, i) => (
                          <StructuredListRow key={i}>
                              <StructuredListCell key={i + ".1"}>{variable.name}</StructuredListCell>
                              <StructuredListCell key={i + ".2"}>{variable.value}</StructuredListCell>
                              <StructuredListCell key={i + ".3"}>{variable.type}</StructuredListCell>
                              <StructuredListCell key={i + ".4"}>{variable.description}</StructuredListCell>
                              <StructuredListCell key={i + ".5"}>
                                  <OverflowMenu ariaLabel="overflow-menu">
                                      <OverflowMenuItem key={i + ".5.1"} itemText="Edit"
                                                        onClick={(e) => editVariable(e, i)}/>
                                      <OverflowMenuItem key={i + ".5.2"} isDelete itemText="Delete"
                                                        onClick={(e) => deleteVariable(e, i)}/>
                                  </OverflowMenu>
                              </StructuredListCell>
                          </StructuredListRow>
                      ))}
                  </StructuredListBody>
                </StructuredListWrapper>
              </div>
            }
            <div>
                {editMode ?
                    <h6 className="variable-title">Edit a variable: </h6>
                    :
                    <h6 className="variable-title">Add a variable: </h6>
                }
                <TextInput data-modal-primary-focus id="name" style={{marginBottom: "1rem"}}
                           labelText="Variable Name"
                           required
                           value={name} onChange={e => {
                    setName(e.currentTarget.value)
                }}/>

                <TextInput id="value" style={{marginBottom: "1rem"}}
                           labelText="Variable Value"
                           required
                           value={value}
                           onChange={e => {
                               setValue(e.currentTarget.value)
                           }}/>
                <TextArea
                    labelText="Variable description"
                    placeholder="(Optional) add a description about the variable"
                    onChange={(e) => setDescription(e.currentTarget.value)}
                    value={description}

                />
            </div>
            {formError &&
              <InlineNotification className={"modal-notification"} kind="error" title="Error"
                                  subtitle={errorMsg}/>
            }
        </Modal>
    )
}
export default AddConnectionVariable