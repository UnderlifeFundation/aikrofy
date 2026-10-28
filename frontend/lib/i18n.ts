import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from '@/locales/en/translation.json';
import es from '@/locales/es/translation.json';
import pt from '@/locales/pt/translation.json';
import de from '@/locales/de/translation.json';
import fr from '@/locales/fr/translation.json';

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    es: { translation: es },
    pt: { translation: pt },
    de: { translation: de },
    fr: { translation: fr },
  },
  // Always start with 'en' to match SSR output and avoid hydration mismatch.
  // The saved language is restored client-side in Providers after mount.
  lng: 'en',
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false, // React already escapes
  },
});

export default i18n;
