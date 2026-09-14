export default function EmptyState({ icon = '💬', title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center panel-enter">
      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500/15 via-blue-500/15 to-violet-500/15 border border-accent/20 flex items-center justify-center text-3xl mb-4">
        {icon}
      </div>
      {title && <h3 className="text-base font-semibold text-text-primary mb-1">{title}</h3>}
      {description && <p className="text-sm text-text-secondary mb-4 max-w-sm">{description}</p>}
      {action}
    </div>
  )
}