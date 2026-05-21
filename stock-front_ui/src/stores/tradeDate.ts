import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useTradeDateStore = defineStore('tradeDate', () => {
  // 当前系统交易日
  const currentTradeDate = ref<string>('')
  // 是否交易日
  const isTradeDay = ref<boolean>(false)

  const setTradeDate = (date: string, isTrade: boolean) => {
    currentTradeDate.value = date
    isTradeDay.value = isTrade
  }

  return {
    currentTradeDate,
    isTradeDay,
    setTradeDate,
  }
})
