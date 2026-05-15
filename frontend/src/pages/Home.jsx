import { Link } from 'react-router-dom'
import { btnPrimaryClass, UserAreaLayout } from '../components/UserAreaLayout.jsx'

const codeClass =
  'rounded-lg bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-800 ring-1 ring-slate-200/80'

export default function Home() {
  return (
    <UserAreaLayout wide centerContent={false}>
      <div className="mb-10 text-center sm:mb-12 sm:text-left">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-600">Templates & merge</p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">Form workflow</h1>
        <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-slate-600 sm:mx-0">
          Admins upload PDF, DOCX, or images with <code className={codeClass}>{'{placeholders}'}</code>. People
          sign in, fill only those fields, and download the merged file.
        </p>
        <p className="mt-6">
          <Link
            to="/signup"
            className={`inline-flex ${btnPrimaryClass} px-6 py-3 text-base`}
          >
            Create account
          </Link>
        </p>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Link
          to="/admin/login"
          className="group rounded-2xl border border-white/60 bg-white/80 p-6 shadow-xl shadow-indigo-950/10 ring-1 ring-slate-200/60 backdrop-blur-md transition hover:border-indigo-200 hover:shadow-indigo-500/10 sm:p-8"
        >
          <h2 className="text-lg font-bold text-slate-900 group-hover:text-indigo-900">Admin</h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-600">
            Upload templates; only <code className={codeClass}>{'{field_name}'}</code> in the document becomes a
            form field. Manage uploads on separate tabs after login.
          </p>
          <span className="mt-5 inline-flex items-center text-sm font-semibold text-indigo-600 group-hover:text-indigo-500">
            Admin login →
          </span>
        </Link>
        <Link
          to="/user/login"
          className="group rounded-2xl border border-white/60 bg-white/80 p-6 shadow-xl shadow-indigo-950/10 ring-1 ring-slate-200/60 backdrop-blur-md transition hover:border-indigo-200 hover:shadow-indigo-500/10 sm:p-8"
        >
          <h2 className="text-lg font-bold text-slate-900 group-hover:text-indigo-900">End user</h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-600">
            Open assigned forms, submit answers, and download filled files. Admin access is assigned separately.
          </p>
          <span className="mt-5 inline-flex items-center text-sm font-semibold text-indigo-600 group-hover:text-indigo-500">
            User login →
          </span>
        </Link>
      </div>

      <p className="mt-12 text-center text-sm text-slate-500 sm:text-left">
        Prefer the API?{' '}
        <a
          href="http://127.0.0.1:8000/docs"
          className="font-semibold text-indigo-600 underline-offset-2 hover:underline"
          target="_blank"
          rel="noreferrer"
        >
          Open Swagger docs
        </a>
        .
      </p>
    </UserAreaLayout>
  )
}
