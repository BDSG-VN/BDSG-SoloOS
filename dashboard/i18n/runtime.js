import { useSyncExternalStore } from 'react';
import en from './en.json';

export const supportedLocales = ['vi', 'en'];
export function normalizeLocale(value) {
  const base = String(value || '').toLowerCase().split(/[-_]/)[0];
  return supportedLocales.includes(base) ? base : 'vi';
}
function initialLocale() {
  if (typeof window === 'undefined') return 'vi';
  const explicit = new URLSearchParams(location.search).get('lang');
  if (supportedLocales.includes(explicit)) return explicit;
  const cookie = document.cookie.match(/(?:^|;\s*)soloos_locale=(vi|en)(?:;|$)/)?.[1];
  if (cookie) return cookie;
  try { return normalizeLocale(localStorage.getItem('soloos.locale') || navigator.language); }
  catch { return normalizeLocale(navigator.language); }
}
let current = initialLocale();
const listeners = new Set();
export const getLocale = () => current;
export const localeTag = () => current === 'en' ? 'en-US' : 'vi-VN';
function reflectLocale() {
  if (typeof document !== 'undefined') document.documentElement.lang = current;
}
reflectLocale();
export function setLocale(value) {
  current = normalizeLocale(value);
  reflectLocale();
  try { localStorage.setItem('soloos.locale', current); } catch { /* Storage may be disabled. */ }
  if (typeof document !== 'undefined') document.cookie = `soloos_locale=${current}; Path=/; Max-Age=31536000; SameSite=Lax${location.protocol === 'https:' ? '; Secure' : ''}`;
  if (typeof window !== 'undefined') {
    const url = new URL(location.href);
    if (url.searchParams.has('lang')) { url.searchParams.set('lang', current); history.replaceState(null, '', url); }
  }
  listeners.forEach(fn => fn());
}
export function useLocale() {
  return [useSyncExternalStore(fn => { listeners.add(fn); return () => listeners.delete(fn); }, getLocale, () => 'vi'), setLocale];
}
// Only call for application-owned UI messages. User documents and AI replies stay untouched.
export function t(message, values = []) {
  const translated = current === 'en' && Object.hasOwn(en, message) ? en[message] : message;
  return String(translated).replace(/\{(\d+)\}/g, (match, index) => index < values.length ? String(values[index]) : match);
}
