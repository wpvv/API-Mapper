import React from "react"
import {
    Button,
    CodeSnippet,
    ComposedModal,
    ModalBody,
    ModalFooter,
    ModalHeader,
    UnorderedList,
    ListItem,
    StructuredListBody,
    StructuredListCell,
    StructuredListHead,
    StructuredListRow,
    StructuredListWrapper,
} from "@carbon/react";




interface IncompleteAPIsInterface {
    open: boolean,
    setOpen: (state: boolean) => void,
    id: string | undefined,
    reason: string,
    incompleteAPIs: string[],

}

export const IncompleteMapping: React.FC<IncompleteAPIsInterface> = ({open, setOpen, id, reason, incompleteAPIs}) => {

    const close = () => {
        setOpen(false)
    }
    return (
        <ComposedModal open={open} onClose={() => false} preventCloseOnClickOutside size="md">
            <ModalHeader closeClassName={"hide-close-button"} label="Incomplete Mapping"
                         title="Saving the connection failed">
                <h3 className="bx--modal-header__heading"></h3>
            </ModalHeader>
            <ModalBody>
                <p style={{marginBottom: "1rem"}}>
                    To ensure the integrity of the connection, every aspect of the mapping is checked for completeness.
                    During this process the following elements where makred required but where not mapped.
                </p>
                <h5>Reason: {reason}</h5>
                {incompleteAPIs.length != 0 &&
                    <div style={{padding:"1rem"}} >
                        <h5>Incomplete APIs:</h5>
                        <UnorderedList style={{padding:"1rem"}}>
                            {incompleteAPIs.map((API, i) => (
                                <ListItem>{API}</ListItem>
                                ))}
                        </UnorderedList>
                    </div>
                }
            </ModalBody>
            <ModalFooter>
                <Button
                    kind="primary"
                    onClick={() => close()}

                >
                    Close
                </Button>
            </ModalFooter>
        </ComposedModal>
    )
}
export default IncompleteMapping