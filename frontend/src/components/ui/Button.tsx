import { type ButtonHTMLAttributes, forwardRef } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
}

const buttonVariants = {
  primary: 'bg-gradient-to-br from-sky-400 via-blue-500 to-indigo-500 text-slate-950 shadow-lg shadow-sky-500/30 hover:shadow-sky-400/50 hover:shadow-xl hover:from-sky-300 hover:via-blue-400 hover:to-indigo-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/60 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900',
  secondary: 'bg-slate-800/60 text-slate-200 border border-slate-500/30 hover:border-sky-400/50 hover:text-sky-200 hover:bg-slate-700/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/60 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900',
  ghost: 'text-sky-200/90 hover:text-sky-100 hover:bg-sky-500/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/60 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900',
}

const buttonSizes = {
  sm: 'px-3 py-2 text-sm',
  md: 'px-5 py-3 text-sm',
  lg: 'px-6 py-4 text-base',
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, className, children, ...props }, ref) => {
    const baseClasses = 'inline-flex items-center justify-center rounded-xl font-semibold transition-all duration-200 disabled:cursor-wait disabled:opacity-60 transform hover:scale-105 active:scale-95'
    const variantClasses = buttonVariants[variant]
    const sizeClasses = buttonSizes[size]

    return (
      <button
        ref={ref}
        className={`${baseClasses} ${variantClasses} ${sizeClasses} ${className || ''}`}
        disabled={loading || props.disabled}
        {...props}
      >
        {loading ? 'Please wait…' : children}
      </button>
    )
  }
)

Button.displayName = 'Button'

export { Button }