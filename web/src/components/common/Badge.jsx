export default function Badge({ count, max = 99, className = '' }) {
  if (!count || count <= 0) return null
  const display = count > max ? `${max}+` : count
  return (
    <span className={`inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-accent text-white text-[10px] font-bold ${className}`}>
      {display}
    </span>
  )
}