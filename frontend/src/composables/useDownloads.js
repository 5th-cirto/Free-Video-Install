import { computed, ref, watch } from 'vue'
import {
  createBatchDownloadApi,
  createDownloadApi,
  inspectVideoApi,
  openPathApi,
  runtimeConfigApi,
  tasksApi,
} from '../api/video'

export function useDownloads() {
  const mode = ref('single')
  const singleUrl = ref('')
  const batchInput = ref('')
  const inspectLoading = ref(false)
  const inspectError = ref('')
  const inspectInfo = ref(null)
  const selectedFormatId = ref('')
  const actionError = ref('')
  const actionLoading = ref(false)
  const downloadsDir = ref('')

  const tasks = ref([])
  const taskCenterExpanded = ref(false)
  let pollTimer = null

  const parsedBatchUrls = computed(() =>
    batchInput.value
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean),
  )

  const successCount = computed(() => tasks.value.filter((task) => task.status === 'success').length)
  const failedCount = computed(() => tasks.value.filter((task) => task.status === 'failed').length)
  const runningCount = computed(() =>
    tasks.value.filter((task) => task.status === 'running' || task.status === 'queued').length,
  )

  watch(runningCount, (count) => {
    if (count > 0) {
      taskCenterExpanded.value = true
    }
  })

  async function inspectVideo(onInspectSuccess) {
    inspectError.value = ''
    actionError.value = ''
    inspectInfo.value = null
    selectedFormatId.value = ''
    if (!singleUrl.value.trim()) {
      inspectError.value = '请先输入视频链接'
      return
    }
    inspectLoading.value = true
    try {
      const resp = await inspectVideoApi({ url: singleUrl.value.trim() })
      inspectInfo.value = resp.data
      if (typeof onInspectSuccess === 'function') {
        await onInspectSuccess(singleUrl.value.trim())
      }
    } catch (error) {
      inspectError.value = error.message
    } finally {
      inspectLoading.value = false
    }
  }

  async function createSingleDownload() {
    actionError.value = ''
    actionLoading.value = true
    try {
      await createDownloadApi({ url: singleUrl.value.trim(), format_id: selectedFormatId.value || null })
      await loadTasks()
    } catch (error) {
      actionError.value = error.message
    } finally {
      actionLoading.value = false
    }
  }

  async function createBatchDownload() {
    actionError.value = ''
    actionLoading.value = true
    try {
      if (!parsedBatchUrls.value.length) throw new Error('请至少输入一条链接')
      await createBatchDownloadApi({
        urls: parsedBatchUrls.value,
        format_id: selectedFormatId.value || null,
      })
      await loadTasks()
    } catch (error) {
      actionError.value = error.message
    } finally {
      actionLoading.value = false
    }
  }

  async function loadTasks() {
    try {
      const resp = await tasksApi()
      tasks.value = resp?.data?.tasks || []
    } catch (_error) {
      // Keep silent for polling to avoid noisy UI.
    }
  }

  async function loadRuntimeConfig() {
    try {
      const resp = await runtimeConfigApi()
      downloadsDir.value = resp?.data?.downloads_dir || ''
    } catch (_error) {
      downloadsDir.value = ''
    }
  }

  async function openLocalPath(path) {
    if (!path) return
    try {
      await openPathApi(path)
    } catch (error) {
      actionError.value = error.message
    }
  }

  function startTaskPolling(intervalMs = 2000) {
    if (pollTimer) clearInterval(pollTimer)
    pollTimer = setInterval(loadTasks, intervalMs)
  }

  function stopTaskPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  return {
    mode,
    singleUrl,
    batchInput,
    inspectLoading,
    inspectError,
    inspectInfo,
    selectedFormatId,
    actionError,
    actionLoading,
    downloadsDir,
    tasks,
    taskCenterExpanded,
    parsedBatchUrls,
    successCount,
    failedCount,
    runningCount,
    inspectVideo,
    createSingleDownload,
    createBatchDownload,
    loadTasks,
    loadRuntimeConfig,
    openLocalPath,
    startTaskPolling,
    stopTaskPolling,
  }
}
