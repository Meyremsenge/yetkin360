import "@testing-library/jest-dom/vitest";
import { beforeEach, vi } from "vitest";

// Mock next/font/google for testing
vi.mock("next/font/google", () => ({
  Inter: () => ({
    className: "mock-inter-font",
  }),
  Source_Serif_4: () => ({
    className: "mock-source-serif-font",
    variable: "--font-source-serif",
  }),
  IBM_Plex_Sans: () => ({
    className: "mock-plex-sans-font",
    variable: "--font-plex-sans",
  }),
  IBM_Plex_Mono: () => ({
    className: "mock-plex-mono-font",
    variable: "--font-plex-mono",
  }),
}));

// localStorage mock for test suites
const mockStorage: Record<string, string> = {};

const storageMock = {
  getItem: (key: string) => mockStorage[key] ?? null,
  setItem: (key: string, value: string) => {
    mockStorage[key] = String(value);
  },
  removeItem: (key: string) => {
    delete mockStorage[key];
  },
  clear: () => {
    Object.keys(mockStorage).forEach((key) => {
      delete mockStorage[key];
    });
  },
  key: (index: number) => {
    return Object.keys(mockStorage)[index] ?? null;
  },
  get length() {
    return Object.keys(mockStorage).length;
  },
};

if (typeof window !== "undefined") {
  Object.defineProperty(window, "localStorage", {
    value: storageMock,
    writable: false,
  });
}

// Fallback for global scope
if (typeof global !== "undefined" && !global.localStorage) {
  (global as any).localStorage = storageMock;
}
