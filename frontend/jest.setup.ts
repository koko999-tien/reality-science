import "@testing-library/jest-dom";

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


