import { t as uiText, localeTag } from "../i18n/runtime.js";
import { useEffect, useRef } from "react";
export function useUnsaved(dirty, onDirtyChange) {
  const current = useRef(dirty);
  current.current = dirty;
  useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);
  useEffect(() => () => onDirtyChange?.(false), [onDirtyChange]);
  useEffect(() => {
    const warn = (e) => {
      if (current.current) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, []);
  return () =>
    !current.current || window.confirm(uiText("Bản đang sửa chưa lưu. Bỏ thay đổi?"));
}
