import { Navigate, Route, Routes } from 'react-router-dom'
import AdminDashboard from './pages/AdminDashboard.jsx'
import AdminLogin from './pages/AdminLogin.jsx'
import Home from './pages/Home.jsx'
import UserFormFill from './pages/UserFormFill.jsx'
import UserForms from './pages/UserForms.jsx'
import UserLogin from './pages/UserLogin.jsx'
import UserSubmissions from './pages/UserSubmissions.jsx'
import Signup from './pages/Signup.jsx'

export default function App() {
  return (
    <div className="min-h-svh bg-zinc-100 text-zinc-900 antialiased dark:bg-zinc-950 dark:text-zinc-100">
      <div className="mx-auto min-h-svh max-w-3xl border-x border-zinc-200/80 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/user/login" element={<UserLogin />} />
          <Route path="/user/forms" element={<UserForms />} />
          <Route path="/user/forms/:id" element={<UserFormFill />} />
          <Route path="/user/submissions" element={<UserSubmissions />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  )
}
