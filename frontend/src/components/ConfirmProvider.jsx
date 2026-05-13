import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
} from 'react'
import { btnPrimaryClass, btnSecondaryClass } from './UserAreaLayout.jsx'

const ConfirmContext = createContext(null)

const btnDangerClass =
  'inline-flex min-h-[2.75rem] flex-1 items-center justify-center rounded-xl bg-gradient-to-r from-red-600 to-rose-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-red-500/25 transition hover:from-red-500 hover:to-rose-500 focus:outline-none focus:ring-4 focus:ring-red-500/30 sm:flex-initial sm:min-w-[7.5rem]'

/**
 * @typedef {Object} ConfirmOptions
 * @property {string} [title]
 * @property {string} message
 * @property {string} [confirmLabel]
 * @property {string} [cancelLabel]
 * @property {'danger' | 'default'} [variant]
 */

/**
 * @returns {(opts: ConfirmOptions | string) => Promise<boolean>}
 */
export function useConfirm() {
  const ctx = useContext(ConfirmContext)
  if (!ctx) {
    throw new Error('useConfirm must be used inside <ConfirmProvider>. Wrap your app in main.jsx.')
  }
  return ctx.confirm
}

export function ConfirmProvider({ children }) {
  const [dialog, setDialog] = useState(null)
  const cancelRef = useRef(null)
  const titleId = useId()

  const confirm = useCallback((opts) => {
    const normalized =
      typeof opts === 'string'
        ? { title: 'Confirm', message: opts, confirmLabel: 'OK', cancelLabel: 'Cancel', variant: 'default' }
        : {
            title: opts.title ?? 'Confirm',
            message: opts.message ?? '',
            confirmLabel: opts.confirmLabel ?? 'OK',
            cancelLabel: opts.cancelLabel ?? 'Cancel',
            variant: opts.variant ?? 'default',
          }

    return new Promise((resolve) => {
      setDialog({
        ...normalized,
        resolve,
      })
    })
  }, [])

  const finish = useCallback(
    (value) => {
      setDialog((d) => {
        if (d) d.resolve(Boolean(value))
        return null
      })
    },
    [],
  )

  useLayoutEffect(() => {
    if (!dialog) return
    cancelRef.current?.focus()
  }, [dialog])

  useEffect(() => {
    if (!dialog) return
    function onKey(e) {
      if (e.key === 'Escape') {
        e.preventDefault()
        finish(false)
      }
    }
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [dialog, finish])

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}
      {dialog ? (
        <div
          className="fixed inset-0 z-[10050] flex items-end justify-center p-0 sm:items-center sm:p-4"
          role="presentation"
        >
          <button
            type="button"
            className="absolute inset-0 cursor-default bg-slate-950/60 backdrop-blur-[3px] transition-opacity"
            aria-label="Dismiss"
            onClick={() => finish(false)}
          />
          <div
            className="relative z-10 flex max-h-[min(90vh,32rem)] w-full max-w-md flex-col overflow-hidden rounded-t-2xl border border-slate-200/90 bg-white shadow-2xl shadow-slate-950/25 ring-1 ring-slate-900/[0.06] sm:rounded-2xl"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={`${titleId}-desc`}
          >
            <div className="border-b border-slate-100 bg-gradient-to-br from-slate-50/90 to-white px-5 pb-4 pt-5 sm:px-6 sm:pb-5 sm:pt-6">
              <h2 id={titleId} className="text-lg font-bold tracking-tight text-slate-900 sm:text-xl">
                {dialog.title}
              </h2>
              <p id={`${titleId}-desc`} className="mt-2 text-sm leading-relaxed text-slate-600">
                {dialog.message}
              </p>
            </div>
            <div className="flex flex-col-reverse gap-2 border-t border-slate-200/80 bg-slate-50/90 px-4 py-4 sm:flex-row sm:justify-end sm:gap-3 sm:px-6">
              <button
                ref={cancelRef}
                type="button"
                className={`${btnSecondaryClass} w-full justify-center sm:w-auto`}
                onClick={() => finish(false)}
              >
                {dialog.cancelLabel}
              </button>
              <button
                type="button"
                className={
                  dialog.variant === 'danger'
                    ? `${btnDangerClass} w-full sm:w-auto`
                    : `${btnPrimaryClass} w-full justify-center sm:w-auto`
                }
                onClick={() => finish(true)}
              >
                {dialog.confirmLabel}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </ConfirmContext.Provider>
  )
}
