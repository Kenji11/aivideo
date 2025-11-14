import { Sparkles, Loader2 } from 'lucide-react'

interface SubmitButtonProps {
  disabled: boolean
  loading: boolean
}

export function SubmitButton({ disabled, loading }: SubmitButtonProps) {
  return (
    <button
      type="submit"
      disabled={disabled || loading}
      className="w-full py-4 px-6 rounded-lg font-medium text-white
                 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 dark:disabled:bg-slate-700
                 disabled:cursor-not-allowed disabled:text-gray-500 dark:disabled:text-gray-500
                 transition-colors flex items-center justify-center gap-2"
    >
      {loading ? (
        <>
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Generating...</span>
        </>
      ) : (
        <>
          <Sparkles className="h-5 w-5" />
          <span>Start Creating</span>
        </>
      )}
    </button>
  )
}

