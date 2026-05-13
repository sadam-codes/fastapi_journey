import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
import './index.css'
import App from './App.jsx'
import { ConfirmProvider } from './components/ConfirmProvider.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ConfirmProvider>
        <App />
      </ConfirmProvider>
      <ToastContainer
        position="top-right"
        autoClose={4800}
        newestOnTop
        closeOnClick
        pauseOnFocusLoss
        draggable
        pauseOnHover
        limit={5}
        theme="light"
        toastClassName="!rounded-xl !text-sm !shadow-lg"
        bodyClassName="!font-sans"
        className="!z-[10000]"
      />
    </BrowserRouter>
  </StrictMode>,
)
