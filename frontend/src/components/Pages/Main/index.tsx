import React from "react"
import "./_main.scss"
import {Button, Grid, Row, Column, Link, Tile} from "@carbon/react"
import {ChevronRight} from "@carbon/react/icons"

// @ts-ignore
import {ReactComponent as BackgroundIllustration} from "./BackgroundIllustration.svg"

export const Main: React.FC = () => {

    return (
        <>
            <section id="hero">
                <Grid id="hero-container">
                    <Column lg={4} sm={16}>
                        <Row>
                            <h1>Connecting APIs, the easy way.</h1>
                        </Row>
                        <Row>
                            <h4>Connect APIs with an easy to use visual editor.</h4>
                        </Row>
                        <Row>
                            <Link href="/config">
                                <Button renderIcon={ChevronRight} id="hero-button">
                                    Get started
                                </Button>
                            </Link>
                        </Row>
                    </Column>

                    <BackgroundIllustration id="background-illustration"/>
                </Grid>
            </section>
            <section>
                <Grid id="explainer-header">
                    <Column lg={16}>
                        <Row>
                            <h2>How it works</h2>
                        </Row>
                        <Row id="explainer-text">
                            <p>Connect APIs on endpoint and data level with ease using a visual approach.</p>
                        </Row>
                        <Row>
                            <Link href="/config">
                                <Button renderIcon={ChevronRight} id="explainer-button">
                                    Connect APIs
                                </Button>
                            </Link>
                        </Row>
                    </Column>
                </Grid>
                <Grid id="explainer-container">
                    <Column lg={4}>
                        <Tile className="step">
                                <span className="step-counter">
                                    1.
                                </span>
                            <h6 className="step-title">
                                Add both applications
                            </h6>
                            <p>
                                For both applications you will need an OpenAPI file. An OpenAPI file describes the APIs
                                of that application in a machine-readable way. If you do not have such a file for either
                                or both of your applications, you can easily generate it!
                            </p>
                        </Tile>
                    </Column>
                    <Column lg={4}>
                        <Tile className="step">
                                <span className="step-counter">
                                    2.
                                </span>
                            <h6 className="step-title">
                                Make an endpoint level mapping
                            </h6>
                            <p>
                                Select both applications and click on Connect Applications. The endpoint level visual
                                editor will open, all endpoint of both applications will be shown. To connect two APIs
                                just draw a line from endpoint to endpoint.
                            </p>
                        </Tile>
                    </Column>
                    <Column lg={4}>
                        <Tile className="step">
                                <span className="step-counter">
                                    3.
                                </span>
                            <h6 className="step-title">
                                Make a data level mapping
                            </h6>
                            <p>
                                When you have connected two endpoints, click on the edit icon on the line connecting
                                them. A window will open where you can map which data field is send where. You have the
                                freedom to change and add data.
                            </p>
                        </Tile>
                    </Column>
                    <Column lg={4}>
                        <Tile className="step">
                                <span className="step-counter">
                                    4.
                                </span>
                            <h6 className="step-title">
                                Start the synchronization server
                            </h6>
                            <p>
                                When you connected all the APIs, you can start the server. The server will synchronize
                                the APIs that you mapped to each other!
                            </p>
                        </Tile>
                    </Column>
                </Grid>
            </section>
        </>

    )
}
export default Main