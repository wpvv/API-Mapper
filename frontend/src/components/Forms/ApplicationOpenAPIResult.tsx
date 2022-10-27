import {
    Button,
    InlineNotification,
    ModalBody,
    ModalFooter,
    ModalHeader,
    InlineLoading,
} from "@carbon/react"
import React from "react"
import SwaggerUI from "swagger-ui-react"
import "swagger-ui-react/swagger-ui.css"

interface ApplicationOpenAPIResultInterface {
    id: string,
    setTab: (index: number) => void,
    setOpen: (state: boolean) => void,
    setId: (id: string) => void,
}

export const ApplicationOpenAPIResult: React.FC<ApplicationOpenAPIResultInterface> = ({id, setTab, setOpen, setId}) => {
    const [formIsSubmitting, setFormIsSubmitting] = React.useState(false)
    const [formSuccess, setFormSuccess] = React.useState(false)
    const [formError, setFormError] = React.useState(false)
    const [formMessage, setFormMessage] = React.useState("")
    const [formMessageShort, setFormMessageShort] = React.useState("")
    const [openAPISpec, setOpenAPISpec] = React.useState({})
    const [darkMode, setDarkMode] = React.useState(false)

    React.useEffect(() => {
        if (id !== "") {
            fetch("api/application/" + id)
                .then((res) => res.json())
                .then((res) => res["config"])
                .then((res) => {
                    if ("specs" in res) {
                        setOpenAPISpec(res["specs"])
                    } else {
                        setFormError(true)
                        setFormMessage("There was an error retrieving the OpenAPI specifications")
                    }
                })
                .catch(error => {
                    console.log(error)
                })
        }
        if (document.documentElement.getAttribute("data-carbon-theme") === "g100") {
            setDarkMode(true)
        } else {
            setDarkMode(false)
        }
    }, [id])

    const initialState = () => {
        setFormIsSubmitting(false)
        setFormSuccess(false)
        setFormError(false)
        setFormMessage("")
        setFormMessageShort("")

        setId("")
    }

    const close = () => {
        setOpen(false)
        initialState()
        setTab(0)
    }

    const submit = (e) => {
        e.preventDefault()
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
    return (
        <>
            <ModalHeader>
                <h3 className="bx--modal-header__heading">OpenAPI Result</h3>
            </ModalHeader>
            <ModalBody className="enable-scrollbar" aria-label="Add Endpoints" hasScrollingContent hasForm>
                <div style={{backgroundColor: "white", paddingTop: "0.1rem"}}>
                    {Object.keys(openAPISpec).length != 0 &&
                        <SwaggerUI spec={JSON.stringify(openAPISpec)} />
                    }
                </div>

            </ModalBody>
            {formError &&
                <InlineNotification className={"modal-notification"} kind="error" title="Error"
                                    subtitle={formMessage}/>
            }
            <ModalFooter>
                <Button
                    kind="secondary"
                    onClick={() => {
                        setTab(2)
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
                        onClick={(e) => submit(e)}
                    >
                        Save
                    </Button>
                )}
            </ModalFooter>
        </>

    )
}
export default ApplicationOpenAPIResult