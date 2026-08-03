const TASK_ID_KEY = 'lumina_active_task_id'
const PROJECT_NAME_KEY = 'lumina_active_project_name'

export function persistActiveTask(taskId: string, projectName = ''): void {
  sessionStorage.setItem(TASK_ID_KEY, taskId)
  sessionStorage.setItem(PROJECT_NAME_KEY, projectName)
}

export function readActiveTaskId(): string | null {
  return sessionStorage.getItem(TASK_ID_KEY)
}

export function readActiveProjectName(): string {
  return sessionStorage.getItem(PROJECT_NAME_KEY) || ''
}

export function clearActiveTask(): void {
  sessionStorage.removeItem(TASK_ID_KEY)
  sessionStorage.removeItem(PROJECT_NAME_KEY)
}
