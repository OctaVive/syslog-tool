import { NavLink, Outlet } from "react-router-dom";
import { GitBranch, Moon, Sun, Upload } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";
import logo from "@/assets/audiocodes-logo.png";

const links = [
  { to: "/", label: "Upload", icon: Upload },
  { to: "/sessions", label: "Sessies", icon: GitBranch },
];

export default function Layout() {
  const { theme, toggle } = useTheme();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-10 bg-white dark:bg-black border-b border-gray-200 dark:border-neutral-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <NavLink to="/" end className="flex items-center" aria-label="AudioCodes">
            <img src={logo} alt="AudioCodes" className="h-8 w-auto dark:bg-white dark:rounded-md dark:px-2 dark:py-1" />
          </NavLink>
          <nav className="flex items-center gap-1">
            {links.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-brand text-white"
                      : "text-gray-600 dark:text-neutral-400 hover:bg-gray-100 dark:hover:bg-neutral-900"
                  }`
                }
              >
                <Icon size={16} />
                <span className="hidden md:inline">{label}</span>
              </NavLink>
            ))}
            <button
              onClick={toggle}
              className="ml-2 p-2 rounded-lg text-gray-600 dark:text-neutral-400 hover:bg-gray-100 dark:hover:bg-neutral-900"
              aria-label="Thema wisselen"
            >
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
