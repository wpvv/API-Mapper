import React from "react"
import {
    Header,
    HeaderGlobalAction,
    HeaderGlobalBar,
    HeaderMenuItem,
    HeaderName,
    HeaderNavigation,
    InlineNotification,
} from "@carbon/react"

import {AsleepFilled, AudioConsole, Home, Light, ServerProxy} from "@carbon/react/icons"

interface NavigationInterface {
    error: boolean,
    theme: string,
    setTheme: (string) => void,
}


export const Navigation: React.FC<NavigationInterface> = ({error, theme, setTheme}) => {
    const [darkMode, setDarkMode] = React.useState(false)
    const setThemeAndMode = (dark) => {
        setDarkMode(dark)
        if (dark) {
            setTheme("g100")
        } else {
            setTheme("white")
        }
    }

    React.useEffect(() => {
        if (theme === "g100") {
            setDarkMode(true)
        } else {
            setDarkMode(false)
        }
    }, [theme])

    return (
        <>
            <Header aria-label="ngUML API Mapping Framework">
                <HeaderName href="/" prefix="ngUML">
                    API Mapping
                </HeaderName>
                <HeaderNavigation aria-label="ngUML [API Mapping Framework]">
                    <HeaderMenuItem href={"/"}><Home style={{verticalAlign: "middle"}}/>&nbsp; Home</HeaderMenuItem>
                    <HeaderMenuItem href={"/config"}><AudioConsole style={{verticalAlign: "middle"}}/>&nbsp; Configurations</HeaderMenuItem>
                    <HeaderMenuItem href={"/server"}><ServerProxy style={{verticalAlign: "middle"}}/>&nbsp; Server Management</HeaderMenuItem>
                </HeaderNavigation>
                <HeaderGlobalBar>
                    <HeaderGlobalAction aria-label="Theme Switcher" onClick={() => setThemeAndMode(!darkMode)}
                                        tooltipAlignment="end">
                        {darkMode ?
                            <Light size={20}/>
                            :
                            <AsleepFilled size={20}/>
                        }
                    </HeaderGlobalAction>
                </HeaderGlobalBar>
            </Header>
            {error &&
                <InlineNotification style={{top: "3rem", maxWidth: "100%", position: "sticky", zIndex: "8000"}}
                                    kind={"error"} title={"Server error"} hideCloseButton={true}
                                    statusIconDescription="Server down alert"
                                    subtitle={"The backend server is currently unavailable, see console for more information"}
                                    role="alert"/>
            }
        </>

    )
}
export default Navigation