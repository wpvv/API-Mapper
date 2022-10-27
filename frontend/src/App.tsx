import * as React from "react"
import {BrowserRouter as Router, Route, Routes} from "react-router-dom"
import Navigation from "./components/Navigation"
import {Config, ConnectionGenerator, Main, ServerManagement} from "./components/Pages"
import { GlobalTheme, Theme } from '@carbon/react'

export const App: React.FC = () => {
    const [error, setError] = React.useState(false)
    const [theme, setTheme] = React.useState("white")
    React.useEffect(() => {
        const intervalId = setInterval(() => {
            fetch("/api/state/")
                .then((response) => {
                    response.json().then(responseJson =>{
                        if (!response.ok) {
                            console.log(response.statusText)
                            setError(true)
                        } else {
                            setError(false)
                        }
                    })

            })
        }, 5000)
        return () => clearInterval(intervalId)

    }, [])
    React.useEffect(() => {
            setTheme(window.localStorage.getItem('theme') || "white")
    }, [])

    React.useEffect(() => {
        window.localStorage.setItem('theme', theme)
        document.documentElement.setAttribute('data-carbon-theme', theme)
    }, [theme])

    return (
        <Router>
            <GlobalTheme theme={theme}>
                <Navigation error={error} theme={theme} setTheme={setTheme}/>
                <Routes>
                    <Route path="/" element={<Main/>}/>
                    <Route path="/config/" element={<Config error={error}/>}/>
                    <Route path="/connection/:id" element={<ConnectionGenerator error={error}/>}/>
                    <Route path="/server" element={<ServerManagement error={error}/>}/>
                </Routes>
            </GlobalTheme>
        </Router>
    )
}
export default App