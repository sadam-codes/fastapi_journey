import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <div className="px-5 py-10 sm:px-8">
      <h1 className="text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        Form workflow
      </h1>
      <p className="mt-3 max-w-2xl text-base leading-relaxed text-zinc-600 dark:text-zinc-400">
        Admins upload PDF, DOCX, or images with placeholders. End users sign in, fill a dynamic
        form, and download the merged file.
      </p>
      <p className="mt-4">
        <Link
          to="/signup"
          className="inline-flex rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-violet-700"
        >
          Create account
        </Link>
      </p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <Link
          to="/admin/login"
          className="rounded-xl border border-zinc-200 bg-zinc-50/80 p-5 shadow-sm transition hover:border-violet-400/60 hover:shadow-md dark:border-zinc-700 dark:bg-zinc-800/50 dark:hover:border-violet-500/50"
        >
          <h2 className="text-lg font-medium text-zinc-900 dark:text-zinc-100">Admin</h2>
          <p className="mt-2 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
            Log in and upload a template. Use{' '}
            <code className="rounded bg-zinc-200 px-1.5 py-0.5 font-mono text-xs text-zinc-800 dark:bg-zinc-700 dark:text-zinc-200">
              {'{{field_name}}'}
            </code>{' '}
            or{' '}
            <code className="rounded bg-zinc-200 px-1.5 py-0.5 font-mono text-xs text-zinc-800 dark:bg-zinc-700 dark:text-zinc-200">
              {'[[FIELD_NAME]]'}
            </code>{' '}
            in the document.
          </p>
        </Link>
        <Link
          to="/user/login"
          className="rounded-xl border border-zinc-200 bg-zinc-50/80 p-5 shadow-sm transition hover:border-violet-400/60 hover:shadow-md dark:border-zinc-700 dark:bg-zinc-800/50 dark:hover:border-violet-500/50"
        >
          <h2 className="text-lg font-medium text-zinc-900 dark:text-zinc-100">End user</h2>
          <p className="mt-2 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
            Log in as client, paralegal, or attorney to open forms and submit answers.
          </p>
        </Link>
      </div>
      <p className="mt-10 text-sm text-zinc-500">
        Prefer the API? Open{' '}
        <a
          href="http://127.0.0.1:8000/docs"
          className="font-medium text-violet-600 underline-offset-2 hover:underline dark:text-violet-400"
          target="_blank"
          rel="noreferrer"
        >
          Swagger docs
        </a>
        .
      </p>
    </div>
  )
}
