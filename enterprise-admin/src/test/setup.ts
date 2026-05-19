import '@testing-library/jest-dom'

// Ant Design 的 Row/Col 组件使用 window.matchMedia，jsdom 环境需要 mock
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

// jsdom 不支持 getComputedStyle 的伪元素参数，Ant Design Table 会触发大量噪音
const originalGetComputedStyle = window.getComputedStyle
window.getComputedStyle = (elt: Element, pseudoElt?: string | null): CSSStyleDeclaration => {
  if (pseudoElt) {
    return {} as CSSStyleDeclaration
  }
  return originalGetComputedStyle(elt)
}
