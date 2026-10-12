import React from 'react';
import {act, fireEvent, render, screen, cleanup} from '@testing-library/react';
import {afterEach, expect, test, vi} from 'vitest';
import {t, setLocale, getLocale, normalizeLocale, useLocale} from './runtime.js';
import LanguagePicker from './language_picker.js';
import en from './en.json';
afterEach(cleanup);
test('normalizes language codes and falls back for unsupported locales',()=>{
 expect(normalizeLocale('en-GB')).toBe('en'); expect(normalizeLocale('vi-VN')).toBe('vi');expect(normalizeLocale('../../evil')).toBe('vi');
});
test('translates only explicit messages and interpolates once without executing content',()=>{
 setLocale('en'); expect(t('Bước {0}', ['<script>{1}</script>'])).toBe('Step <script>{1}</script>');expect(t('Custom user text')).toBe('Custom user text');setLocale('vi');expect(t('Lưu')).toBe('Lưu');
});
test('switching language updates the UI without remounting or losing typed content',()=>{
 function Editor(){useLocale();const [draft,update]=React.useState('');return React.createElement('div',null,React.createElement(LanguagePicker),React.createElement('label',null,t('Nội dung'),React.createElement('input',{value:draft,onChange:e=>update(e.target.value)})),React.createElement('p',null,draft));}
 render(React.createElement(Editor));fireEvent.change(screen.getByRole('textbox'),{target:{value:'Lưu'}});fireEvent.change(screen.getByRole('combobox'),{target:{value:'en'}});expect(screen.getByLabelText('Content').value).toBe('Lưu');expect(screen.getByText('Lưu')).toBeTruthy();expect(document.documentElement.lang).toBe('en');expect(localStorage.getItem('soloos.locale')).toBe('en');expect(document.cookie).toContain('soloos_locale=en');
});
test('works when local storage is unavailable',()=>{
 const spy=vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('blocked')});expect(()=>setLocale('en')).not.toThrow();expect(getLocale()).toBe('en');spy.mockRestore();
});
test('all translated messages retain the same interpolation fields',()=>{
 const slots=s=>[...s.matchAll(/\{\d+\}/g)].map(x=>x[0]).sort();for(const [key,value]of Object.entries(en)){expect(value.length,key).toBeGreaterThan(0);expect(slots(value),key).toEqual(slots(key));}
});
