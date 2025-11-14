interface ProjectInfoSectionProps {
  title: string
  description: string
  onTitleChange: (value: string) => void
  onDescriptionChange: (value: string) => void
}

export function ProjectInfoSection({
  title,
  description,
  onTitleChange,
  onDescriptionChange,
}: ProjectInfoSectionProps) {
  return (
    <div className="space-y-6">
      {/* Project Title */}
      <div>
        <label
          htmlFor="projectTitle"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Project Title
        </label>
        <input
          type="text"
          id="projectTitle"
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder="E.g., Summer Travel Vlog"
          className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 
                     bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                     placeholder-gray-400 dark:placeholder-gray-500
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     transition-colors"
          required
        />
      </div>

      {/* Description (Optional) */}
      <div>
        <label
          htmlFor="description"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Description <span className="text-gray-500 dark:text-gray-400">(optional)</span>
        </label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder="Add more context about your project..."
          rows={3}
          className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 
                     bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                     placeholder-gray-400 dark:placeholder-gray-500
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     transition-colors resize-none"
        />
      </div>
    </div>
  )
}

