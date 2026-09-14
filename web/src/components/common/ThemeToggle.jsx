import { useTheme } from '../../context/ThemeContext'
import IconButton from './IconButton'
import { SunIcon, MoonIcon } from '../icons'

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  return (
    <IconButton label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'} onClick={toggleTheme}>
      {theme === 'light' ? <SunIcon className="w-[18px] h-[18px]" /> : <MoonIcon className="w-[18px] h-[18px]" />}
    </IconButton>
  )
}