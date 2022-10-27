import {
    Button,
    ComposedModal,
    ModalBody,
    ModalFooter,
    ModalHeader,
    ProgressIndicator,
    ProgressStep,
} from "@carbon/react"
import React from "react"
import ApplicationInput from "../Forms/ApplicationInput"
import ApplicationAuth from "../Forms/ApplicationAuth"
import ApplicationEndpoints from "../Forms/ApplicationEndpoints"
import "./_addApplication.scss"
import "rapidoc"
import ApplicationOpenAPIResult from "../Forms/ApplicationOpenAPIResult"

interface AddApplicationInterface {
    open: boolean,
    setOpen: (state: boolean) => void,
    id: string,
    setId: (id:string) => void,

}

declare global {
    namespace JSX {
        interface IntrinsicElements {
            "rapi-doc": any
        }
    }
}
export const AddApplication: React.FC<AddApplicationInterface> = ({open, setOpen, id, setId}) => {

    const [item, setItem] = React.useState(0)
    const [automaticImport, setAutomaticImport] = React.useState(false)

    return (
        <ComposedModal open={open} onClose={() => setOpen(false)} size="lg">
            <ProgressIndicator
                currentIndex={item}
                spaceEqually
                className="progress-padding"
            >

                <ProgressStep
                    label="Add an Application"
                />
                <ProgressStep
                    label="Add API Authentication"
                />
                <ProgressStep
                    label="Add API Endpoints"
                    complete={automaticImport}
                    disabled={automaticImport}
                />
                <ProgressStep
                    label="Result overview"
                    complete={automaticImport}
                    disabled={automaticImport}
                />
            </ProgressIndicator>

            {item === 0 &&
                <div className="bx--tab-content">
                    <ApplicationInput setOpen={setOpen} setTab={setItem} automaticImport={automaticImport}
                                      setAutomaticImport={setAutomaticImport} id={id} setId={setId}/>
                </div>

            }
            {item === 1 &&
                <div className="bx--tab-content">
                    <ApplicationAuth setOpen={setOpen} setTab={setItem} id={id} automaticImport={automaticImport}
                                     setId={setId}/>
                </div>
            }
            {item === 2 &&
                <div className="bx--tab-content">
                    <ApplicationEndpoints setOpen={setOpen} setTab={setItem} id={id} setId={setId}/>
                </div>
            }
            {item === 3 &&
                <div className="bx--tab-content">
                    <ApplicationOpenAPIResult setOpen={setOpen} setTab={setItem} id={id} setId={setId} />
                </div>
            }
        </ComposedModal>
    )
}
export default AddApplication