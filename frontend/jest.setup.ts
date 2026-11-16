import "@testing-library/jest-dom";

// jsdom does not provide fetch in every supported Jest/Node combination.
// Keep the global available so API tests can replace it with a scenario-specific mock.
if (typeof global.fetch === "undefined") {
  global.fetch = jest.fn() as unknown as typeof fetch;
}

// Polyfill ResizeObserver for Jest/jsdom environment (required by @xyflow/react)
if (typeof global.ResizeObserver === "undefined") {
  global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

// Polyfill HTMLCanvasElement.prototype.getContext for Jest/jsdom environment
if (typeof HTMLCanvasElement !== "undefined") {
  HTMLCanvasElement.prototype.getContext = () => null;
}

