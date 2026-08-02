export default function SidebarSearch({ value, onChange, placeholder = 'Search...' }) {
  return (
    <div className="px-4 py-3 border-b border-border">
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">🔍</span>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="input-base pl-9"
          aria-label="Search"
        />
      </div>
    </div>
  )
}