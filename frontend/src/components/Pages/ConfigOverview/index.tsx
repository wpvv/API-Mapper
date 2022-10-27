import React from "react"
import {DataTableSkeleton} from "@carbon/react"
import AddApplication from "../../Modals/AddApplication"
import AddConnectionInput from "../../Modals/AddConnectionInput"
import ConfigTable from "../../Tables/ApplicationConfig"
import "./_configOverview.scss"
import {useNavigate} from "react-router-dom"

interface ConfigInterface {
    error: boolean,
}

export const Config: React.FC<ConfigInterface> = ({error}) => {
    const [openNewAPI, setOpenNewAPI] = React.useState(false)
    const [openNewConnection, setOpenNewConnection] = React.useState(false)
    const [applicationRows, setApplicationRows] = React.useState([])
    const [applicationId, setApplicationId] = React.useState("")
    const [connectionRows, setConnectionRows] = React.useState([])
    const [loading, setLoading] = React.useState(true)

    const navigate = useNavigate()

    React.useEffect(() => {
        fetch("/api/application/")
            .then((res) => res.json())
            .then((res) => {
                setApplicationRows(res["applications"])
                setLoading(false)
            })
            .catch(error => {
                console.log(error)
            })
    }, [loading, openNewAPI])

    React.useEffect(() => {
        fetch("/api/connection/")
            .then((res) => res.json())
            .then((res) => {
                setConnectionRows(res["connections"])
                setLoading(false)
            })
            .catch(error => {
                console.log(error)
            })
    }, [loading, openNewConnection])

    const deleteApplication = (rows) => {
        rows.forEach((row) => {
                fetch("/api/application/" + row["id"], {
                    method: "DELETE",
                    mode: "cors",
                })
                    .then((res) => res.json())
                    .then((res) => {
                        setLoading(true)
                    })
                    .catch(error => {
                        console.log(error)
                    })
            }
        )
    }
    const editApplication = (id) => {
        setApplicationId(id)
        setOpenNewAPI(true)
    }

    const editConnection = (id) => {
        fetch("/api/connection/" + id, {
            method: "PUT",
            mode: "cors",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                state: "Incomplete"
            })
        }).then(response => response.json())
            .then(response => {
                if (response["success"]) {
                    navigate("/connection/" + id)
                }

            })
            .catch(error => {
                console.log(error)
            })
    }

    const deleteConnection = (rows) => {
        rows.forEach((row) => {
                fetch("/api/connection/" + row["id"], {
                        method: "DELETE",
                        mode: "cors",
                    }
                )
                    .then((res) => res.json())
                    .then((res) => {
                        setLoading(true)
                    })
                    .catch(error => {
                        console.log(error)
                    })
            }
        )
    }
    const downloadOpenAPI = (id) => {
        fetch("/api/application/download/" + id, {
                method: "GET",
                mode: "cors",
            }
        )
            .then((res) => res.json())
            .then((res) => {
                const jsonString = `data:text/json;chatset=utf-8,${encodeURIComponent(
                    JSON.stringify(res)
                )}`;
                const link = document.createElement("a");
                link.href = jsonString;
                link.download = "OpenAPI.json";

                link.click();
            })
            .catch(error => {
                console.log(error)
            })
    }

    const applicationHeaders = [{key: "name", header: "Name"}, {key: "description", header: "Description"},
        {key: "version", header: "Version"}, {key: "state", header: "Status"}]

    const connectionHeaders = [{key: "application1", header: "Application 1"}, {
        key: "application2",
        header: "Application 2"
    }, {key: "description", header: "Description"}, {key: "version", header: "Version"},
        {key: "state", header: "Status"}]

    return (
        <div className="main-container">
            <div className="config-table">
                {error || loading ?
                    <DataTableSkeleton columnCount={3} rowCount={5}/>
                    :
                    <ConfigTable title={"Applications"} description={"Individual Applications"}
                                 rows={applicationRows}
                                 headers={applicationHeaders} type={1} buttonAction={setOpenNewAPI}
                                 deleteAction={deleteApplication} editAction={editApplication} downloadAction={downloadOpenAPI}/>
                }
            </div>
            <AddApplication open={openNewAPI} setOpen={setOpenNewAPI} id={applicationId} setId={setApplicationId}/>

            <div className="config-table">
                {error || loading ?
                    <DataTableSkeleton columnCount={4} rowCount={5}/>
                    :
                    <ConfigTable title={"Mapped connections"} description={"Applications mapped with each other"}
                                 rows={connectionRows}
                                 headers={connectionHeaders} type={2} buttonAction={setOpenNewConnection}
                                 deleteAction={deleteConnection} editAction={editConnection}/>
                }
            </div>
            <AddConnectionInput open={openNewConnection} setopen={setOpenNewConnection} headers={applicationHeaders}
                                rows={applicationRows}/>
        </div>

    )
}
export default Config

