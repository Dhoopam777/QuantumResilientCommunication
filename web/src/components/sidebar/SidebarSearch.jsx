import { SearchIcon, CloseIcon } from '../icons'

export default function SidebarSearch({ value, onChange, placeholder = 'Search...' }) {
  return (
    <div className="px-4 pb-3">
      <div className="relative group">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 flex text-text-muted transition-colors duration-200 group-focus-within:text-accent">
          <SearchIcon className="w-4 h-4" />
        </span>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="input-base pl-9 pr-8 rounded-full"
          aria-label="Search"
        />
        {value && (
          <button
            type="button"
            onClick={() => onChange('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-md text-text-muted hover:text-text-primary hover:bg-surface-hover transition-colors"
            aria-label="Clear search"
            title="Clear search"
          >
            <CloseIcon className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  )
}