import React from "react"
import {
    DataTable,
    Table,
    TableBatchAction,
    TableBatchActions,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableHeader,
    TableRow,
    TableSelectRow,
    TableToolbar,
    TableToolbarContent,
    TableToolbarSearch
} from "@carbon/react"
import {GatewayApi} from "@carbon/react/icons"

interface configSimpleInterface {
    rows: object[],
    headers: object[],
    onselect: (e: object, id1: number, id2: number) => void,
}

export const ConfigTableSimple: React.FC<configSimpleInterface> = ({rows, headers, onselect}) => {
    const createConnection = (e, id1, id2) => {
        onselect(e, id1, id2)
    }

    return (
        <DataTable rows={rows} headers={headers}>
            {({
                  rows,
                  headers,
                  getSelectionProps,
                  getBatchActionProps,
                  getTableProps,
                  getRowProps,
                  selectedRows,
                  onInputChange,
              }) => {
                const batchActionProps = getBatchActionProps()

                return (
                    <TableContainer>
                        <TableToolbar>
                            <TableBatchActions {...batchActionProps}>
                                {selectedRows.length === 2 && selectedRows[0]["cells"][3]["value"] === "Complete" && selectedRows[1]["cells"][3]["value"] === "Complete" &&
                                    <TableBatchAction
                                        tabIndex={batchActionProps.shouldShowBatchActions ? 0 : -1}
                                        renderIcon={GatewayApi}
                                        onClick={e => createConnection(e, selectedRows[0]["id"], selectedRows[1]["id"])}>
                                        Connect application
                                    </TableBatchAction>
                                }

                            </TableBatchActions>
                            <TableToolbarContent
                                aria-hidden={batchActionProps.shouldShowBatchActions}>
                                <TableToolbarSearch
                                    persistent={true}
                                    tabIndex={batchActionProps.shouldShowBatchActions ? -1 : 0}
                                    onChange={onInputChange}
                                />
                            </TableToolbarContent>
                        </TableToolbar>
                        <Table {...getTableProps()}>
                            <TableHead>
                                <TableRow>
                                    <th scope="col"/>
                                    {headers.map((header, i) => (
                                        <TableHeader key={i}>
                                            {header.header}
                                        </TableHeader>
                                    ))}
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {rows.map((row, i) => (
                                    <TableRow key={i} {...getRowProps({row})}>
                                        <TableSelectRow {...getSelectionProps({row})}
                                                        onSelect={(evt) => {
                                                            getSelectionProps({row}).onSelect(evt)
                                                        }}
                                        />
                                        {row.cells.map((cell) => {
                                            if (cell.value === "Incomplete") {
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
export default ConfigTableSimple