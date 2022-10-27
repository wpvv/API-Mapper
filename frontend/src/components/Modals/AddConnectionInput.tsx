import {Modal} from "@carbon/react";
import React from "react"
import APIconfigSimple from "../Tables/ApplicationConfigSimple";
import {useNavigate} from "react-router-dom";

interface AddConnectionInputInterface {
    open: boolean,
    setopen: (state: boolean) => void,
    rows: any
    headers: any,
}

export const AddConnectionInput: React.FC<AddConnectionInputInterface> = ({open, setopen, rows, headers}) => {
    const navigate = useNavigate();

    const creatConnection = (e, id1, id2) => {
        e.preventDefault()
        fetch("/api/connection/generate/" + id1 + "/" + id2)
            .then((res) => res.json())
            .then((res) => {
                navigate("/connection/" + res["id"]);
            })
            .catch(error => {
                console.log(error)
            })
        // navigate("/connection/" + id1 + "/" + id2 + "/");
    }

    return (
        <Modal
            modalHeading="Select 2 applications to connect"
            modalLabel="Create Connection"
            open={open}
            passiveModal
            onRequestClose={() => setopen(false)}
        >
            <APIconfigSimple rows={rows} headers={headers} onselect={creatConnection}/>
        </Modal>
    )

}
export default AddConnectionInput