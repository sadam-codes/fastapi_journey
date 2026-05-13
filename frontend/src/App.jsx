import { Navigate, Route, Routes } from 'react-router-dom'
import AdminLayout from './pages/AdminLayout.jsx'
import AdminLogin from './pages/AdminLogin.jsx'
import AdminSubmissionDetail from './pages/AdminSubmissionDetail.jsx'
import AdminSubmissionsList from './pages/AdminSubmissionsList.jsx'
import AdminTemplateDetail, {
  AdminTemplateEditTab,
  AdminTemplatePreviewTab,
} from './pages/AdminTemplateDetail.jsx'
import AdminTemplatesList from './pages/AdminTemplatesList.jsx'
import AdminUpload from './pages/AdminUpload.jsx'
import Home from './pages/Home.jsx'
import UserFormFill from './pages/UserFormFill.jsx'
import UserForms from './pages/UserForms.jsx'
import UserLogin from './pages/UserLogin.jsx'
import UserSubmissions from './pages/UserSubmissions.jsx'
import Signup from './pages/Signup.jsx'

export default function App() {
  return (
    <div className="min-h-svh bg-slate-100 text-slate-900 antialiased mx-auto container max-w-7xl">
      <Routes>
        <Route path="/" element={<Navigate to="/user/login" replace />} />
        <Route path="/home" element={<Home />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Navigate to="templates" replace />} />
          <Route path="upload" element={<AdminUpload />} />
          <Route path="submissions" element={<AdminSubmissionsList />} />
          <Route path="submissions/:submissionId" element={<AdminSubmissionDetail />} />
          <Route path="templates" element={<AdminTemplatesList />} />
          <Route path="templates/:templateId" element={<AdminTemplateDetail />}>
            <Route index element={<Navigate to="preview" replace />} />
            <Route path="preview" element={<AdminTemplatePreviewTab />} />
            <Route path="edit" element={<AdminTemplateEditTab />} />
          </Route>
        </Route>
        <Route path="/user/login" element={<UserLogin />} />
        <Route path="/user/forms" element={<UserForms />} />
        <Route path="/user/forms/:id" element={<UserFormFill />} />
        <Route path="/user/submissions" element={<UserSubmissions />} />
        <Route path="*" element={<Navigate to="/user/login" replace />} />
      </Routes>
    </div>
  )
}
