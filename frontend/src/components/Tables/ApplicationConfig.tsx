import React from "react"
import {Button, DataTable} from "@carbon/react"
import {Edit, GatewayApi, TrashCan, DocumentDownload} from "@carbon/react/icons"
import {useNavigate} from "react-router-dom"

interface configInterface {
    title: string,
    description: string,
    rows: object[],
    headers: object[],
    type: number,
    buttonAction: (state: boolean) => void,
    deleteAction: (id: string) => void,
    editAction: (id: string) => void,
    downloadAction?: (id: string) => void,

}

export const ConfigTable: React.FC<configInterface> = ({
                                                           title,
                                                           description,
                                                           rows,
                                                           headers,
                                                           type,
                                                           buttonAction,
                                                           deleteAction,
                                                           editAction,
                                                           downloadAction,
                                                       }) => {
    const navigate = useNavigate()

    const createConnection = (e, id1, id2) => {
        e.preventDefault()
        fetch("/api/connection/generate/" + id1 + "/" + id2)
            .then((res) => res.json())
            .then((res) => {
                navigate("/connection/" + res["id"])
            })
            .catch(error => {
                console.log(error)
            })
    }

    const staticConnectionSelected = (selectedRows) => {
        let staticConnectionFound = false
        selectedRows.forEach((row) => {
            let actualRow = rows.find((obj: any) => {
                return obj?.id === row.id
            })
            if (actualRow) {
                if (actualRow["static"]) {
                    staticConnectionFound = true
                }
            }
        })
        return staticConnectionFound
    }

    const {
        TableContainer,
        Table,
        TableHead,
        TableRow,
        TableBody,
        TableCell,
        TableHeader,
        TableToolbar,
        TableBatchActions,
        TableBatchAction,
        TableToolbarContent,
        TableToolbarSearch,
        TableSelectAll,
        TableSelectRow,
    } = DataTable

    return (
        <DataTable rows={rows} headers={headers}>
            {({
                  rows,
                  headers,
                  getHeaderProps,
                  getRowProps,
                  getSelectionProps,
                  getBatchActionProps,
                  onInputChange,
                  selectedRows,
                  getTableProps,
                  selectAll,
              }) => {
                const batchActionProps = getBatchActionProps()

                return (
                    <TableContainer
                        title={title}
                        description={description}>
                        <TableToolbar>
                            <TableBatchActions {...batchActionProps}>
                                {(type === 1 || (type === 2 && !staticConnectionSelected(selectedRows))) &&
                                    <TableBatchAction
                                        tabIndex={batchActionProps.shouldShowBatchActions ? 0 : -1}
                                        renderIcon={TrashCan}
                                        onClick={() => {
                                            deleteAction(selectedRows)
                                            selectAll()
                                        }}>
                                        Delete
                                    </TableBatchAction>
                                }
                                {type === 1
                                    && [
                                        (selectedRows.length === 2 && selectedRows[0]["cells"][3]["value"] === "Complete" && selectedRows[1]["cells"][3]["value"] === "Complete" &&
                                            <TableBatchAction
                                                tabIndex={batchActionProps.shouldShowBatchActions ? 0 : -1}
                                                renderIcon={GatewayApi}
                                                onClick={e => {
                                                    createConnection(e, selectedRows[0]["id"], selectedRows[1]["id"])
                                                    selectAll()
                                                }}>
                                                Connect applications
                                            </TableBatchAction>
                                        ),
                                        (selectedRows.length === 1 &&
                                            <TableBatchAction
                                                tabIndex={batchActionProps.shouldShowBatchActions ? 0 : -1}
                                                renderIcon={DocumentDownload}
                                                onClick={() => {
                                                    if (downloadAction) {
                                                        downloadAction(selectedRows[0]["id"])
                                                    }
                                                    selectAll()
                                                }}>
                                                Download OpenAPI
                                            </TableBatchAction>
                                        )
                                    ]
                                }
                                {selectedRows.length === 1 &&
                                    <TableBatchAction
                                        tabIndex={batchActionProps.shouldShowBatchActions ? 0 : -1}
                                        renderIcon={Edit}
                                        onClick={() => {
                                            editAction(selectedRows[0]["id"])
                                            selectAll()
                                        }}>
                                        Edit
                                    </TableBatchAction>
                                }
                            </TableBatchActions>
                            <TableToolbarContent
                                aria-hidden={batchActionProps.shouldShowBatchActions}>
                                <TableToolbarSearch
                                    persistent={false}
                                    tabIndex={batchActionProps.shouldShowBatchActions ? -1 : 0}
                                    onChange={onInputChange}
                                />
                                <Button
                                    tabIndex={batchActionProps.shouldShowBatchActions ? -1 : 0}
                                    onClick={() => buttonAction(true)}
                                    size="sm"
                                    kind="primary">
                                    {type === 1 ? "Add new application" : "Make new connection"}
                                </Button>
                            </TableToolbarContent>
                        </TableToolbar>
                        <Table {...getTableProps()}>
                            <TableHead>
                                <TableRow>
                                    <TableSelectAll {...getSelectionProps()} />
                                    {headers.map((header, i) => (
                                        <TableHeader key={i} {...getHeaderProps({header})}>
                                            {header.header}
                                        </TableHeader>
                                    ))}
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {rows.map((row, i) => (
                                    <TableRow key={i} {...getRowProps({row})}>
                                        <TableSelectRow {...getSelectionProps({row})} />
                                        {row.cells.map((cell) => {
                                            if (cell.value === "Incomplete" || String(cell.value).includes("missing") || String(cell.value).includes("incomplete")) {
                                                return <TableCell key={cell.id}
                                                                  className="application-incomplete">{cell.value}</TableCell>
                                            } else if (cell.value === "Complete") {
                                                return <TableCell key={cell.id}
                                                                  className="application-complete">{cell.value}</TableCell>
                                            } else {
                                                return <TableCell key={cell.id}>{cell.value}</TableCell>
                                            }
                                        })}
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                )
            }}
        </DataTable>
    )
}
export default ConfigTable