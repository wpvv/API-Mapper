import "./_serverManagement.scss"
import React from "react"
import {ButtonSet, Checkbox, Dropdown, IconButton, InlineNotification, Layer, OverflowMenu, Toggle} from "@carbon/react"
import {LazyLog, ScrollFollow} from "react-lazylog"
import {Play, Stop, Reset, Settings} from "@carbon/react/icons"

interface serverManagementInterface {
    error: boolean
}

export const ServerManagement: React.FC<serverManagementInterface> = ({error}) => {
    const [connectionsArray, setConnectionsArray] = React.useState<Array<String>>([])
    const [config, setConfig] = React.useState("")
    const [log, setLog] = React.useState<Array<String>>(["Sync Server is off\n", "Select a connection config to start"])
    const [pageError, setError] = React.useState(false)
    const [errorMsg, setErrorMsg] = React.useState("")
    const [logInterval, setLogInterval] = React.useState<any>("")
    const [pollingInterval, setPollingInterval] = React.useState(0)
    const [clearCache, setClearCache] = React.useState(true)
    const [syncServer, setSyncServer] = React.useState(false)

    React.useEffect(() => {
        fetch("/api/state/")
            .then((res) => res.json())
            .then((res) => {
                setSyncServer(res["syncServer"])
                if (res["syncServer"]) {
                    setLogInterval(setInterval(function () {
                        getLog(log.length)
                    }, 1000))
                }
            })
        fetch("/api/connection/complete")
            .then((res) => res.json())
            .then((res) => {
                setConnectionsArray(res["configs"])
                console.log(res)
            })
            .catch(error => {
                console.log(error)
            })
    }, [])

    React.useEffect(() => {
        if (!syncServer && logInterval !== "") {
            setTimeout(() => {
                clearInterval(logInterval)
                setLogInterval("")
                setSyncServer(false)
            }, 2000)
        }
    }, [syncServer])

    const interval = [
        {
            "name": "5 seconds",
            "value": 5
        },
        {
            "name": "30 seconds",
            "value": 30
        },
        {
            "name": "1 minute",
            "value": 60
        },
        {
            "name": "5 minutes",
            "value": 300
        },
        {
            "name": "10 minutes",
            "value": 600
        },
        {
            "name": "15 minutes",
            "value": 900
        }
    ]
    const clearLog = () => {
        setLog([])
        setLog(["Sync Server is off\n", "Select a connection config to start"])
        setError(false)
        setErrorMsg("")
        clearInterval(logInterval)
        setLogInterval("")
        setSyncServer(false)
    }

    const getLog = (length) => {
        fetch("/api/server/log")
            .then((res) => res.json())
            .then((res) => {
                if (!res["success"]) {
                    setError(true)
                    setErrorMsg(res["reason"])
                } else {
                    if ("data" in res) {
                        setSyncServer(res["syncServer"])
                        setLog(res["data"])
                    }
                }
            })
            .catch(error => {
                console.log(error)
            })
    }

    const startServer = () => {
        setLog([""])
        fetch("/api/server/start/?id=" + config + "&interval=" + pollingInterval + "&cache=" + clearCache)
            .then((res) => res.json())
            .then((res) => {
                if (!res["success"]) {
                    setError(true)
                    setErrorMsg(res["reason"])
                } else {
                    setSyncServer(true)
                    setLogInterval(setInterval(function () {
                        getLog(log.length)
                    }, 1000))
                }
            })
            .catch(error => {
                console.log(error)
            })
    }

    const stopServer = () => {
        fetch("/api/server/stop/")
            .then((res) => res.json())
            .then((res) => {
                if (!res["success"]) {
                    setError(true)
                    setErrorMsg(res["reason"])
                } else {
                    setTimeout(() => {
                        clearInterval(logInterval)
                        setLogInterval("")
                        setSyncServer(false)
                    }, 2000)
                }
            })
            .catch(error => {
                console.log(error)
            })
    }

    return (
        <div className="main-container">
            {
                pageError &&
                <InlineNotification className={"modal-notification"} kind="error" title="Error"
                                    subtitle={errorMsg}/>
            }
            <Layer>
                <h1>Synchronization Server</h1>
                <p>Here you can select a connection configuration to be used by the sync server to sync the two
                    application
                    that are defined in the connection configuration.</p>
                <Layer>
                    <ButtonSet className="server-button-panel">
                        <Dropdown
                            id="selectConfig"
                            items={connectionsArray}
                            size="lg"
                            label="Select Connection Config"
                            itemToString={(item) =>
                                item.state === "Complete" &&
                                (item.application1 + " - " + item.application2)
                            }
                            onChange={(e) => setConfig(e.selectedItem.id)}
                        />
                        <Dropdown
                            id="selectInterval"
                            items={interval}
                            size="lg"
                            label="Select polling interval"
                            itemToString={(item) =>
                                (item.name)
                            }
                            onChange={(e) => setPollingInterval(e.selectedItem.value)}
                        />

                        <IconButton kind="primary" label="Start Sync Server" size="lg"
                                    disabled={syncServer || config === "" || pollingInterval === 0}
                                    onClick={() => startServer()}><Play/> &nbsp; Start</IconButton>
                        <IconButton kind="danger" label="Stop Sync Server" size="lg" disabled={!syncServer}
                                    onClick={() => stopServer()}><Stop/> &nbsp; Stop</IconButton>
                        <IconButton kind="secondary" label="Clear console" size="lg"
                                    disabled={syncServer || log.length == 2}
                                    onClick={() => clearLog()}><Reset/> &nbsp; Clear Log</IconButton>
                        <OverflowMenu
                            renderIcon={Settings}
                            size="lg"
                        >
                            <Toggle size="sm" id={"clear cache"} labelA={"Clear cache"} labelB={"Retain cache"}  onToggle={setClearCache} toggled={clearCache} className={"clear-cache-toggle"}/>
                        </OverflowMenu>
                    </ButtonSet>

                    <div className="log-panel">
                        <ScrollFollow
                            startFollowing={true}
                            render={({onScroll, follow, startFollowing, stopFollowing}) => (


                                <LazyLog text={log.join("")} onScroll={onScroll} follow={follow}/>
                            )}
                        />
                    </div>
                </Layer>
            </Layer>
        </div>

    )
}
export default ServerManagement