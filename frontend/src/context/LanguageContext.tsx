import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { copy, type Language } from "@/i18n";

const STORAGE_KEY = "language";

const LanguageContext = createContext<{
  language: Language;
  setLanguage: (language: Language) => void;
  t: (typeof copy)[Language];
}>({
  language: "nl",
  setLanguage: () => undefined,
  t: copy.nl,
});

function storedLanguage(): Language {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "en" || stored === "nl" ? stored : "nl";
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(storedLanguage);

  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.classList.remove("dark");
    localStorage.setItem(STORAGE_KEY, language);
  }, [language]);

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t: copy[language] }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
