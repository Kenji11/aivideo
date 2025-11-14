interface PromptInputProps {
  value: string
  onChange: (value: string) => void
}

export function PromptInput({ value, onChange }: PromptInputProps) {
  return (
    <div>
      <label
        htmlFor="prompt"
        className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
      >
        What would you like to create?
      </label>
      <textarea
        id="prompt"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Describe your video in detail. E.g., Create a promotional video about sustainable living with nature scenes, uplifting music, and inspirational quotes..."
        rows={6}
        className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 
                   bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                   placeholder-gray-400 dark:placeholder-gray-500
                   focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   transition-colors resize-none"
        required
      />
    </div>
  )
}

