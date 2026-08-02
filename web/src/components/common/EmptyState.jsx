export default function EmptyState({ icon = '💬', title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="text-4xl mb-3">{icon}</div>
      {title && <h3 className="text-lg font-semibold text-text-primary mb-1">{title}</h3>}
      {description && <p className="text-sm text-text-secondary mb-4 max-w-sm">{description}</p>}
      {action}
    </div>
  )
}