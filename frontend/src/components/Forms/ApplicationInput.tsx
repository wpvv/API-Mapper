import {
    Button,
    Checkbox,
    FileUploaderButton,
    FileUploaderItem,
    Form,
    InlineNotification,
    ModalBody,
    ModalFooter,
    ModalHeader,
    NumberInput,
    TextInput,
    Tooltip,
} from "@carbon/react"
import React from "react"
import {FileStatus} from "carbon-components-react/lib/components/FileUploader/shared"


interface APIinputInterface {
    automaticImport: boolean,
    setAutomaticImport: (state: boolean) => void,
    setTab: (index: number) => void,
    setOpen: (state: boolean) => void,
    id: string,
    setId: (id: string) => void,
}

export const ApplicationInput: React.FC<APIinputInterface> = ({
                                                          automaticImport,
                                                          setAutomaticImport,
                                                          setTab,
                                                          setOpen,
                                                          id,
                                                          setId
                                                      }) => {
    const [name, setName] = React.useState("")
    const [description, setDescription] = React.useState("")
    const [baseUrl, setBaseUrl] = React.useState("")
    const [version, setVersion] = React.useState(0.1)
    const [formError, setFormError] = React.useState(false)
    const [formMsg, setFormMsg] = React.useState("")
    const [automaticImportURL, setAutomaticImportURL] = React.useState("")
    const [automaticImportFile, setAutomaticImportFile] = React.useState("")
    const [automaticImportFileName, setAutomaticImportFileName] = React.useState("")
    const [automaticImportFileIsSet, setAutomaticImportFileIsSet] = React.useState("uploading")

    React.useEffect(() => {
        if (id !== "") {
            fetch("api/application/" + id)
                .then((res) => res.json())
                .then((res) => res["config"])
                .then((res) => {
                    setName(res["name"])
                    setDescription(res["description"])
                    setBaseUrl(res["baseUrl"])
                    setVersion(res["version"] ?? 0.1)
                    setAutomaticImport(res["automaticImport"])
                    if (res["automaticImport"]) {
                        if ("automaticImportURL" in res && res["automaticImportURL"] !== "") {
                            setAutomaticImportURL(res["automaticImportURL"])
                        }
                        if ("automaticImportFileName" in res && res["automaticImportFileName"] !== "") {
                            setAutomaticImportFileName(res["automaticImportFileName"])
                            setAutomaticImportFileIsSet("edit")
                        }
                    }

                })
                .catch(error => {
                    console.log(error)
                })

        }
    }, [setAutomaticImport, id])

    const initialState = () => {
        setName("")
        setDescription("")
        setBaseUrl("")
        setVersion(0.1)
        setAutomaticImport(false)
        setAutomaticImportURL("")
        setAutomaticImportFile("")
        setAutomaticImportFileName("")
        setAutomaticImportFileIsSet("uploading")
        setId("")
    }

    const close = () => {
        initialState()
        setTab(0)
        setOpen(false)
    }

    const saveAPI = (e) => {
        e.preventDefault()
        if (automaticImport && !automaticImportFileName && !automaticImportURL) {
            setFormError(true)
            setFormMsg("Upload either an OpenApi file or add an file URL")
        } else {
            fetch("/api/application/save/" + id, {
                method: "POST",
                mode: "cors",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    name: name,
                    description: description,
                    baseUrl: baseUrl,
                    version: version,
                    automaticImport: automaticImport,
                    automaticImportURL: automaticImportURL,
                    automaticImportFile: automaticImportFile,
                    automaticImportFileName: automaticImportFileName
                })
            }).then(response => response.json())
                .then(response => {
                    if (!response["success"]) {
                        setFormError(true)
                        setFormMsg(response["message"])
                    } else {
                        initialState()
                        setId(response["id"])
                        setTab(1)
                    }
                })
                .catch(error => {
                    console.log(error)
                })
        }
    }

    const handleAutomaticImportFileUpload = async (e) => {
        if (!e.currentTarget.files) {
            return
        } else {
            const fileReader = new FileReader()
            fileReader.onload = (e) => {
                if (e.target && e.target.result) {
                    setAutomaticImportFile(e.target.result as string)
                }
            }
            setAutomaticImportFileName(e.currentTarget.files[0].name)
            fileReader.readAsText(e.currentTarget.files[0], "UTF-8")
            setAutomaticImportFileIsSet("uploading")
            setTimeout(() => {
                setTimeout(() => {
                    setAutomaticImportFileIsSet("edit")
                }, 500)
                setAutomaticImportFileIsSet("complete")
            }, 1500)
        }
    }

    const handleAutomaticImportFileUploadDelete = async () => {
        setAutomaticImportFileIsSet("uploading")
        setAutomaticImportFileName("")
    }
    return (
        <>
            <ModalHeader closeModal={() => {
                close()
            }}>
                <h3 className="bx--modal-header__heading">Add an Application</h3>
            </ModalHeader>
            <ModalBody className="enable-scrollbar" aria-label="Add an Application" hasScrollingContent hasForm>
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
                <br/>
                <Tooltip
                        label={"OpenApi formally known as Swagger is a specifications file that describes APIs. Generally this file is available through the vendor or if you are the vendor can be automatically generated by the API framework in the application."}
                        align={"bottom-left"}>
                        <a href="https://swagger.io/solutions/getting-started-with-oas/" className="bx--link"> Learn More</a>
                    </Tooltip>

                <Form id="newApi" onSubmit={e => saveAPI(e)}>

                    <TextInput data-modal-primary-focus id="name" style={{marginBottom: "1rem"}}
                               labelText="Application Name"
                               required
                               value={name} onChange={e => {
                        setName(e.currentTarget.value)
                    }}/>

                    <TextInput id="description" style={{marginBottom: "1rem"}}
                               labelText="Application Description"
                               required
                               value={description}
                               onChange={e => {
                                   setDescription(e.currentTarget.value)
                               }}/>

                    <TextInput id="baseUrl" style={{marginBottom: "1rem"}} labelText="API Base URL" required
                               value={baseUrl} placeholder="https://" onChange={e => {
                        setBaseUrl(e.currentTarget.value)
                    }}/>

                    <NumberInput id="version" style={{fontFamily: "unset"}} label="API Version" required step={0.1}
                                 value={version} min={0.1} onChange={e => setVersion(e.imaginaryTarget.valueAsNumber)}
                                 iconDescription={"increase / decrease version"}/>

                    <div style={{marginBottom: "1rem", marginTop: "1rem"}}>
                        <Checkbox id="automaticImport"
                                  checked={automaticImport}
                                  labelText="Automatic import with OpenAPI" onChange={(e) => setAutomaticImport(e.target.checked)}/>
                    </div>

                    {automaticImport &&
                        <div>
                            <h6>Add a file</h6>

                            <FileUploaderButton labelText="Add OpenAPI file" buttonKind="tertiary" onChange={e => {
                                handleAutomaticImportFileUpload(e)
                            }} accept={[".yaml", ".yml", ".json"]}
                            />
                            {automaticImportFileName &&
                                <FileUploaderItem status={automaticImportFileIsSet as FileStatus}
                                                  name={automaticImportFileName}
                                                  onDelete={() => handleAutomaticImportFileUploadDelete()}/>
                            }
                            <h6>Or enter a file URL</h6>

                            <TextInput id="automaticImportURL" style={{marginBottom: "1rem", marginTop: "1rem"}}
                                       labelText="OpenApi spec URL" hideLabel placeholder="https://"
                                       value={automaticImportURL} disabled={!automaticImport} onChange={e => {
                                setAutomaticImportURL(e.currentTarget.value)
                            }}/>

                        </div>
                    }
                </Form>
            </ModalBody>
            {formError &&
                <InlineNotification className={"modal-notification"} kind="error" title="Error"
                                    subtitle={formMsg}/>
            }
            <ModalFooter>
                <Button
                    kind="secondary"
                    onClick={() => {
                        close()
                    }}>
                    Cancel
                </Button>
                <Button
                    kind="primary"
                    type="submit"
                    form="newApi"
                >
                    Next
                </Button>
            </ModalFooter>
        </>
    )
}

export default ApplicationInput