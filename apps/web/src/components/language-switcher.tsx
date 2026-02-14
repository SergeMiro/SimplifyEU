'use client';

import { useLocale } from 'next-intl';
import { usePathname, useRouter } from '@/i18n/routing';

export default function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  const switchLocale = (newLocale: string) => {
    router.replace(pathname, { locale: newLocale });
  };

  return (
    <div className="flex items-center gap-1 border rounded-md p-1">
      {(['en', 'fr', 'es'] as const).map((l) => (
        <button
          key={l}
          onClick={() => switchLocale(l)}
          className={`px-3 py-1 rounded-sm text-sm font-medium transition-all ${
            locale === l
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
          }`}
        >
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
