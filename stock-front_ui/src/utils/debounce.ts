/**
 * 防抖工具函数
 */

/**
 * 防抖装饰器：fn 被包装为在 wait ms 内不会被重复调用
 * 适用于事件处理器、watch 等高频触发场景
 * 返回带有 cancel() 方法的对象，用于在组件卸载时取消待执行的调用
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  wait: number
): { (...args: Parameters<T>): void; cancel: () => void } {
  let timer: ReturnType<typeof setTimeout> | null = null
  const debounced = function (...args: Parameters<T>) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn(...args)
      timer = null
    }, wait)
  }
  debounced.cancel = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }
  return debounced
}