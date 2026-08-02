export default function Spinner({ size = 'md', className = '' }) {
  const sizes = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-2',
    lg: 'w-8 h-8 border-3',
  }
  return (
    <div
      className={`${sizes[size]} rounded-full border-accent border-t-transparent animate-spin ${className}`}
      role="status"
      aria-label="Loading"
    />
  )
}