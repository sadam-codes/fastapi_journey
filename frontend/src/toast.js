import { toast } from 'react-toastify'

/** API / validation failures */
export function toastError(message) {
  if (message) toast.error(String(message))
}

/** Successful saves, uploads, etc. */
export function toastSuccess(message, options) {
  if (message) toast.success(message, options)
}

/** Warnings (e.g. no placeholders detected) */
export function toastWarning(message, options) {
  if (message) toast.warning(message, options)
}

/** Neutral info (e.g. OnlyOffice hints) */
export function toastInfo(message, options) {
  if (message) toast.info(String(message), options)
}
