import { Navigate, Route, Routes } from 'react-router-dom'
import AdminLayout from './pages/AdminLayout.jsx'
import AdminLogin from './pages/AdminLogin.jsx'
import AdminTemplates from './pages/AdminTemplates.jsx'
import AdminUpload from './pages/AdminUpload.jsx'
import Home from './pages/Home.jsx'
import UserFormFill from './pages/UserFormFill.jsx'
import UserForms from './pages/UserForms.jsx'
import UserLogin from './pages/UserLogin.jsx'
import UserSubmissions from './pages/UserSubmissions.jsx'
import Signup from './pages/Signup.jsx'

export default function App() {
  return (
    <div className="min-h-svh bg-slate-100 text-slate-900 antialiased">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Navigate to="upload" replace />} />
          <Route path="upload" element={<AdminUpload />} />
          <Route path="templates" element={<AdminTemplates />} />
        </Route>
        <Route path="/user/login" element={<UserLogin />} />
        <Route path="/user/forms" element={<UserForms />} />
        <Route path="/user/forms/:id" element={<UserFormFill />} />
        <Route path="/user/submissions" element={<UserSubmissions />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}
