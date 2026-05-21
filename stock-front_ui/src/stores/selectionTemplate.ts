import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_KEY = 'selection-templates'

export interface SelectionTemplate {
  id: number
  name: string
  filters: Record<string, unknown>
  createdAt: string
}

function loadFromStorage(): SelectionTemplate[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveToStorage(templates: SelectionTemplate[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(templates))
}

export const useSelectionTemplateStore = defineStore('selectionTemplate', () => {
  // 初始化时从 localStorage 读取
  const templates = ref<SelectionTemplate[]>(loadFromStorage())

  const addTemplate = (template: SelectionTemplate) => {
    templates.value.push(template)
    saveToStorage(templates.value)
  }

  const removeTemplate = (id: number) => {
    templates.value = templates.value.filter((t) => t.id !== id)
    saveToStorage(templates.value)
  }

  return {
    templates,
    addTemplate,
    removeTemplate,
  }
})
