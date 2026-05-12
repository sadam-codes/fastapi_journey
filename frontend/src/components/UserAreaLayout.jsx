/** Primary CTA — gradient button (site-wide). */
export const btnPrimaryClass =
  'rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition hover:from-indigo-500 hover:to-violet-500 focus:outline-none focus:ring-4 focus:ring-indigo-500/30 disabled:cursor-not-allowed disabled:opacity-60'

/** Secondary outline control. */
export const btnSecondaryClass =
  'inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white/90 px-4 py-2.5 text-sm font-semibold text-slate-800 shadow-sm transition hover:border-indigo-300 hover:bg-indigo-50/80'

/** Destructive / logout outline. */
export const btnMutedClass =
  'inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white/90 px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-red-200 hover:bg-red-50/80 hover:text-red-800'

/** Native file input styled to match the app. */
export const fileInputClass =
  'mt-2 block w-full text-sm text-slate-600 file:mr-4 file:cursor-pointer file:rounded-xl file:border-0 file:bg-gradient-to-r file:from-indigo-600 file:to-violet-600 file:px-4 file:py-2.5 file:text-sm file:font-semibold file:text-white file:shadow-md hover:file:from-indigo-500 hover:file:to-violet-500'

/** Shared light gradient shell (signup, login, forms, admin, home). */
export function UserAreaLayout({ children, wide = false, centerContent = true }) {
  const maxW = wide ? 'max-w-4xl' : 'max-w-lg'
  const yPad = centerContent ? 'py-12 sm:py-16' : 'py-10 sm:py-12'
  const justify = centerContent ? 'justify-center' : 'justify-start'

  return (
    <div className="relative left-1/2 right-1/2 -ml-[50vw] -mr-[50vw] w-screen min-h-svh overflow-x-hidden bg-gradient-to-br from-indigo-50 via-white to-violet-100 text-slate-800">
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.35]"
        aria-hidden
        style={{
          backgroundImage:
            'radial-gradient(circle at 20% 20%, rgb(99 102 241 / 0.18), transparent 45%), radial-gradient(circle at 80% 10%, rgb(168 85 247 / 0.15), transparent 40%), radial-gradient(circle at 50% 80%, rgb(56 189 248 / 0.12), transparent 50%)',
        }}
      />
      <div
        className={`relative mx-auto flex min-h-svh flex-col px-5 sm:px-8 ${maxW} ${justify} ${yPad}`}
      >
        {children}
      </div>
    </div>
  )
}

export function GlassCard({ children, className = '' }) {
  return (
    <div
      className={`rounded-2xl border border-white/60 bg-white/80 p-6 shadow-xl shadow-indigo-950/10 ring-1 ring-slate-200/60 backdrop-blur-md sm:p-8 ${className}`}
    >
      {children}
    </div>
  )
}

/** Inputs matching the signup page. */
export const userAreaInputClass =
  'mt-2 w-full rounded-xl border border-slate-200/90 bg-white/90 px-4 py-3 text-sm text-slate-900 shadow-sm outline-none ring-indigo-500/20 transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-4'
