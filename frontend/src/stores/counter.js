import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

// 这是 Vite + Pinia 模板自带的示例 store。
// 当前业务未使用它，保留用于演示 Pinia 的基础写法。
export const useCounterStore = defineStore('counter', () => {
  // 响应式状态
  const count = ref(0)
  // 计算属性
  const doubleCount = computed(() => count.value * 2)
  // 行为（action）
  function increment() {
    count.value++
  }

  return { count, doubleCount, increment }
})
