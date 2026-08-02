import { useTheme } from '../../context/ThemeContext'
import IconButton from './IconButton'

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  return (
    <IconButton label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'} onClick={toggleTheme}>
      {theme === 'light' ? '🌙' : '☀️'}
    </IconButton>
  )
}