import React from "react"
import {
    ComboBox,
    DataTable,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableHeader,
    TableRow,

} from "@carbon/react"

interface LowLevelEndpointInterface {
    name: string,
    rows: object[],
    dataSources: object[]
}

export const LowLevelEndpoint: React.FC<LowLevelEndpointInterface> = ({
                                                                          name,
                                                                          rows,
                                                                          dataSources
                                                                      }) => {
    const headers = [{key: "name", header: "Name"}, {key: "type", header: "Data type"}, {key: "required", header: "Required"}]

    return (
        <DataTable rows={rows} headers={headers}>
            {({
                  rows,
                  headers,
                  getHeaderProps,
                  getRowProps,
                  getTableProps,
              }) => (
                <TableContainer title={name + " endpoint mapping"}
                                description={"description"}>
                    <Table {...getTableProps()}>
                        <TableHead>
                            <TableRow>
                                {headers.map((header) => (
                                    <TableHeader
                                        key={header.key} {...getHeaderProps({header})}>
                                        {header.header}
                                    </TableHeader>
                                ))}
                                <TableHeader>Data source</TableHeader>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {rows.map((row) => (
                                <TableRow key={row.id} {...getRowProps({row})}>
                                    {row.cells.map((cell) => {
                                        if (cell.value === true) {
                                            return <TableCell key={cell.id}
                                                              className="application-incomplete">Required</TableCell>
                                        } else if (cell.value === false) {
                                            return <TableCell key={cell.id}
                                                              className="application-complete">Optional</TableCell>
                                        } else {
                                            return <TableCell
                                                key={cell.id}>{cell.value}</TableCell>
                                        }
                                    })}
                                    <TableCell key={row.id + "source"}>
                                        <ComboBox
                                            onChange={() => {
                                            }}
                                            id="carbon-combobox"
                                            items={dataSources}
                                            itemToString={(item) => (item ? item.name : '')}
                                            placeholder="Filter..."
                                        />
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
            )}
        </DataTable>
    )
}
export default LowLevelEndpoint