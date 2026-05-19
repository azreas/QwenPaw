import { ConfigProvider, theme as antdTheme } from "antd"
import { RouterProvider } from "react-router-dom"
import { AuthProvider } from "@/features/auth/AuthProvider"
import router from "@/app/router"
import "@/styles/global.css"

const { defaultAlgorithm } = antdTheme

// 主题配置
const themeConfig = {
  algorithm: defaultAlgorithm,
  token: {
    colorPrimary: "#667eea",
    borderRadius: 8,
  },
  components: {
    Button: {
      borderRadius: 8,
    },
    Card: {
      borderRadius: 12,
    },
    Input: {
      borderRadius: 8,
    },
  },
}

function App() {
  return (
    <ConfigProvider theme={themeConfig}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </ConfigProvider>
  )
}

export default App
