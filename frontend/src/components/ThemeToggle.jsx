import { Moon, Sun } from 'lucide-react';
import { toggleTheme, useTheme } from '../theme.js';
import IconButton from './IconButton.jsx';

export default function ThemeToggle() {
  const isDark = useTheme() === 'dark';

  return (
    <IconButton
      label="Dark theme"
      icon={isDark ? Moon : Sun}
      aria-pressed={isDark}
      onClick={toggleTheme}
    />
  );
}
