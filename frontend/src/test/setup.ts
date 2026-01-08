import '@testing-library/jest-dom';

// Mock scrollIntoView which is not implemented in jsdom
Element.prototype.scrollIntoView = () => {};

// Mock __APP_VERSION__ which is injected by Vite at build time
(globalThis as Record<string, unknown>).__APP_VERSION__ = '0.12.0-test';
