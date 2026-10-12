import React from 'react';
import { useLocale } from './runtime.js';
export default function LanguagePicker() {
  const [locale, setLocale] = useLocale();
  return React.createElement('label', {className:'language-picker'},
    React.createElement('span', null, locale === 'vi' ? 'Ngôn ngữ' : 'Language'),
    React.createElement('select', {value:locale, 'aria-label':'Language / Ngôn ngữ', onChange:event=>setLocale(event.target.value)},
      React.createElement('option', {value:'vi'}, 'Tiếng Việt'),
      React.createElement('option', {value:'en'}, 'English')));
}
