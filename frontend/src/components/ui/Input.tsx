import { type InputHTMLAttributes, forwardRef } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className, ...props }, ref) => {
    const baseClasses = 'w-full rounded-xl border border-slate-500/30 bg-slate-900/70 px-4 py-3 text-base text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-400/60 focus:border-sky-300/40 disabled:cursor-not-allowed disabled:opacity-60 transition-all duration-200 hover:border-slate-400/50'
    const errorClasses = error ? 'border-rose-400/40 focus:ring-rose-400/60 focus:border-rose-300/40 hover:border-rose-400/50' : ''

    return (
      <label className="flex flex-col gap-2 text-sm font-medium text-slate-200/90">
        {label && <span>{label}</span>}
        <input
          ref={ref}
          className={`${baseClasses} ${errorClasses} ${className || ''}`}
          {...props}
        />
        {error && (
          <span className="text-sm text-rose-200">{error}</span>
        )}
      </label>
    )
  }
)

Input.displayName = 'Input'

export { Input }