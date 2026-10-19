import { NavLink, Outlet } from "react-router-dom";
import { GitBranch, Upload } from "lucide-react";
import { useLanguage } from "@/context/LanguageContext";
import type { Language } from "@/i18n";
import logo from "@/assets/audiocodes-logo.png";

const languages: { id: Language; label: string }[] = [
  { id: "en", label: "English" },
  { id: "nl", label: "Dutch" },
];

export default function Layout() {
  const { t, language, setLanguage } = useLanguage();
  const links = [
    { to: "/", label: t.upload, icon: Upload },
    { to: "/sessions", label: t.sessions, icon: GitBranch },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-10 bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <NavLink to="/" end className="flex items-center" aria-label="AudioCodes">
            <img src={logo} alt="AudioCodes" className="h-8 w-auto" />
          </NavLink>
          <nav className="flex items-center gap-1">
            {links.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive ? "bg-brand text-white" : "text-gray-600 hover:bg-gray-100"
                  }`
                }
              >
                <Icon size={16} />
                <span className="hidden md:inline">{label}</span>
              </NavLink>
            ))}
            <div className="ml-2 flex items-center rounded-lg border border-gray-200 p-0.5" role="group" aria-label={t.language}>
              {languages.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setLanguage(item.id)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium ${
                    language === item.id ? "bg-brand text-white" : "text-gray-600 hover:bg-gray-100"
                  }`}
                  aria-pressed={language === item.id}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
