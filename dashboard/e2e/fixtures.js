import { test as base, expect } from "@playwright/test";
// Each integration scenario uses the same loopback IP. Pace scenarios so the
// complete suite exercises the real rate limiter without exhausting its window.
export const test = base.extend({
  rateWindow: [
    async ({}, use) => {
      await new Promise((resolve) => setTimeout(resolve, 20000));
      await use();
    },
    { auto: true },
  ],
});
export { expect };
