import {
    Button,
    Form,
    FormGroup,
    InlineLoading,
    InlineNotification,
    ModalBody,
    ModalFooter,
    ModalHeader,
    PasswordInput,
    Select,
    SelectItem,
    TextInput,
    Tooltip,
} from "@carbon/react"
import React from "react"
import {Add, TrashCan} from "@carbon/react/icons"

interface APIAuthInterface {
    id: string,
    setTab: (index: number) => void,
    setOpen: (state: boolean) => void,
    automaticImport: boolean,
    setId: (id: string) => void,
}

export const ApplicationAuth: React.FC<APIAuthInterface> = ({id, setTab, setOpen, automaticImport, setId}) => {
    const [type, setType] = React.useState("none")
    const [basicUsername, setBasicUsername] = React.useState("")
    const [basicPassword, setBasicPassword] = React.useState("")
    const [apiTokenList, setApiTokenList] = React.useState([{key: "x-api-key", value: ""}])
    const [formError, setFormError] = React.useState(false)
    const [formMessage, setFormMessage] = React.useState("")
    const [formMessageShort, setFormMessageShort] = React.useState("")
    const [formIsSubmitting, setFormIsSubmitting] = React.useState(false)
    const [formSuccess, setFormSuccess] = React.useState(false)

    React.useEffect(() => {
        if (id !== "") {
            fetch("api/application/" + id)
                .then((res) => res.json())
                .then((res) => res["config"])
                .then((res) => {
                        switch (res["securityScheme"]) {
                            case "none": {
                                setType(res["securityScheme"])
                                break
                            }
                            case "BasicAuth": {
                                if ("basicUsername" in res) {
                                    setBasicUsername(res["basicUsername"])
                                }
                                if ("basicPassword" in res) {
                                    setBasicPassword(res["basicPassword"])
                                }
                                setType(res["securityScheme"])
                                break
                            }
                            case "ApiKeyAuth": {
                                if ("headerItems" in res) {
                                    let temp: { key: string, value: string }[] = []
                                    for (const [key, value] of Object.entries(res["headerItems"])) {
                                        temp.push({key: key, value: String(value)})
                                        setApiTokenList(temp)
                                    }
                                }
                                setType(res["securityScheme"])
                                break
                            }
                        }
                    }
                )
                .catch(error => {
                    console.log(error)
                })
        } else {
            setFormError(true)
            setFormMessage("Application ID not set")
        }
    }, [id])

    const initialState = () => {
        setType("none")
        setBasicUsername("")
        setBasicPassword("")
        setApiTokenList([{key: "x-api-key", value: ""}])
        setFormError(false)
        setFormMessage("")
        setFormIsSubmitting(false)
        setFormSuccess(false)
        setFormMessageShort("")
        setId("")
    }

    const close = () => {
        initialState()
        setTab(0)
        setOpen(false)
    }

    const saveAuth = (e) => {
        e.preventDefault()
        let authConfig = JSON.stringify({})
        switch (type) {
            case "none": {
                authConfig = JSON.stringify({
                    securityScheme: type,
                })
                break
            }
            case "BasicAuth": {
                authConfig = JSON.stringify({
                    securityScheme: type,
                    basicUsername: basicUsername,
                    basicPassword: basicPassword,
                })
                break
            }
            case "ApiKeyAuth": {
                authConfig = JSON.stringify({
                    securityScheme: type,
                    headerItems: apiTokenList,
                })
                break
            }
        }
        fetch("/api/application/auth/save/" + id, {
                method: "POST",
                mode: "cors",
                headers: {
                    "Content-Type": "application/json"
                },
                body: authConfig,
            }
        ).then(response => response.json())
            .then(response => {
                if (!response["success"]) {
                    setFormError(true)
                    setFormMessage(response["message"])
                } else {
                    if (!automaticImport) {
                        setId(response["id"])
                        setTab(2)
                    } else {
                        setFormIsSubmitting(true)
                        setFormMessageShort("Saving")
                        setTimeout(() => {

                            setFormIsSubmitting(false)
                            setFormSuccess(true)
                            setFormMessageShort("Saved!")
                            setTimeout(() => {
                                close()
                                setTimeout(() => {
                                    setFormSuccess(false)
                                    setFormMessageShort("Saving")
                                }, 1500)
                            }, 1000)
                        }, 2000)
                    }
                }
            })
            .catch(error => {
                console.log(error)
            })

    }

    const handleInputChange = (e, index) => {
        const {name, value} = e.target
        const list = [...apiTokenList]
        list[index][name] = value
        setApiTokenList(list)
    }

    const handleRemoveClick = index => {
        const list = [...apiTokenList]
        list.splice(index, 1)
        setApiTokenList(list)
    }

    const handleAddClick = () => {
        setApiTokenList(apiTokenList => [...apiTokenList, {key: "", value: ""}])
    }

    return (
        <>
            <ModalHeader closeModal={() => {
                close()
            }}>
                <h3 className="bx--modal-header__heading">Add an Authentication Token</h3>
            </ModalHeader>
            <ModalBody aria-label="Add an Auth" className="enable-scrollbar" hasScrollingContent hasForm>
                <span style={{marginBottom: "1rem"}}>
                    Here you can add applications. Later on these configurations will be used to connect two
                    applications.
                    The APIs of the application you want to connect need to configured. This can be done either
                    manually
                    or automatically. Manually means that all endpoints will be needed to described, this will
                    be asked
                    in the next step.
                    Automatically is done by importing an OpenAPI specifications file.
                </span>

                <Form id="newAuth" onSubmit={e => saveAuth(e)}>
                    <Select id="select-1" value={type}
                            onChange={(e) => setType(e.currentTarget.value)}>
                        <SelectItem value="none" text="None"/>
                        <SelectItem value="BasicAuth" text="Basic Auth"/>
                        <SelectItem value="ApiKeyAuth" text="API Key"/>
                    </Select>
                    {type === "BasicAuth" &&
                        <FormGroup legendText="">
                            <TextInput id="basicUsername" style={{marginBottom: "1rem"}} labelText="Username"
                                       required
                                       value={basicUsername} onChange={e => {
                                setBasicUsername(e.currentTarget.value);
                            }}/>
                            <PasswordInput tooltipPosition="left" id="basicPassword" style={{marginBottom: "1rem"}}
                                           labelText="Password"
                                           required
                                           value={basicPassword} onChange={e => {
                                setBasicPassword(e.currentTarget.value);
                            }}/>
                        </FormGroup>
                    }
                    {type === "ApiKeyAuth" &&
                        [
                            (apiTokenList.map((x, i) => {
                                return (
                                    <FormGroup legendText="" className="api-formgroup" key={i}>
                                        <TextInput id={"key" + i} className="small-input" labelText="Key"
                                                   value={x.key} key={i + ".1"}
                                                   name="key" onChange={e => handleInputChange(e, i)} required/>
                                        <TextInput id={"value" + i} className="small-input" labelText="Value"
                                                   value={x.value} key={i + ".2"} name="value"
                                                   onChange={e => handleInputChange(e, i)}
                                                   required/>
                                        {apiTokenList.length !== 1 &&
                                            [(apiTokenList.length - 1 !== i &&
                                                <Button hasIconOnly renderIcon={TrashCan} size="field" key={i + ".3"}
                                                        className={"margin-add-button"} iconDescription="Delete row"
                                                        tooltipAlignment="end"
                                                        onClick={() => handleRemoveClick(i)}/>

                                            )]
                                        }
                                        {apiTokenList.length - 1 === i &&
                                            <>
                                                {apiTokenList.length !== 1 &&
                                                    <Button hasIconOnly renderIcon={TrashCan} size="field"
                                                            className="button-spacing"
                                                            iconDescription="Delete row"
                                                            tooltipAlignment="end" key={i + ".4"}
                                                            onClick={() => handleRemoveClick(i)}/>
                                                }
                                                <Button hasIconOnly renderIcon={Add} size="field"
                                                        iconDescription="Add row" key={i + ".5"}
                                                        tooltipAlignment="end" onClick={() => handleAddClick()}/>
                                            </>
                                        }
                                    </FormGroup>
                                )
                            }))]
                    }
                </Form>
            </ModalBody>
            {formError &&
                <InlineNotification className={"modal-notification"} kind="error" title="Error"
                                    subtitle={formMessage}/>
            }
            <ModalFooter>
                <Button
                    kind="secondary"
                    onClick={() => {
                        setTab(0)
                    }}
                    disabled={formIsSubmitting || formSuccess || formError}
                >

                    Back
                </Button>
                {formIsSubmitting || formSuccess || formError ? (
                    <InlineLoading
                        style={{marginLeft: "1rem", flex: "0 1 50%"}}
                        description={formMessageShort}
                        status={formSuccess ? "finished" : "active"}
                    />
                ) : (
                    <Button
                        kind="primary"
                        type="submit"
                        form="newAuth"
                    >
                        {automaticImport ?
                            "Save"
                            :
                            "Next"
                        }

                    </Button>
                )}
            </ModalFooter>
        </>
    )
}
export default ApplicationAuth