import { computed, ref } from 'vue'
import { configureApiClient } from '../api/client'
import { loginApi, meApi, registerApi, requestPasswordResetApi, resetPasswordApi } from '../api/auth'

const ACCESS_TOKEN_KEY = 'uvd_access_token'

export function useAuth() {
  const savedToken = localStorage.getItem(ACCESS_TOKEN_KEY) || ''
  const accessToken = ref(savedToken)

  const currentUser = ref(null)
  const membershipStatus = ref({
    is_vip: false,
    plan_code: 'free',
    valid_until: '',
  })

  const authDialogVisible = ref(false)
  const authMode = ref('login')
  const authEmail = ref('')
  const authPassword = ref('')
  const authConfirmPassword = ref('')
  const authActionToken = ref('')
  const authLoading = ref(false)
  const authError = ref('')
  const authInfo = ref('')

  const isLoggedIn = computed(() => Boolean(currentUser.value?.email))
  const isVipUser = computed(() => Boolean(membershipStatus.value?.is_vip))
  const vipValidUntilText = computed(() => membershipStatus.value?.valid_until || '')

  function setAccessToken(token) {
    accessToken.value = token || ''
    if (accessToken.value) {
      localStorage.setItem(ACCESS_TOKEN_KEY, accessToken.value)
    } else {
      localStorage.removeItem(ACCESS_TOKEN_KEY)
    }
  }

  function resetMembershipStatus() {
    membershipStatus.value = {
      is_vip: false,
      plan_code: 'free',
      valid_until: '',
    }
  }

  function clearSession() {
    setAccessToken('')
    currentUser.value = null
    resetMembershipStatus()
  }

  configureApiClient({
    getAccessToken: () => accessToken.value,
    onUnauthorized: clearSession,
  })

  function openAuthDialog(mode = 'login') {
    authMode.value = mode
    authError.value = ''
    authInfo.value = ''
    authDialogVisible.value = true
  }

  function closeAuthDialog() {
    authDialogVisible.value = false
    authError.value = ''
    authInfo.value = ''
    authPassword.value = ''
    authConfirmPassword.value = ''
    authActionToken.value = ''
  }

  function switchAuthMode() {
    if (authMode.value === 'register') authMode.value = 'login'
    else if (authMode.value === 'login') authMode.value = 'register'
    else authMode.value = 'login'
    authError.value = ''
    authInfo.value = ''
    authPassword.value = ''
    authConfirmPassword.value = ''
    authActionToken.value = ''
  }

  async function loadCurrentUser(onLoaded) {
    if (!accessToken.value) return
    try {
      const resp = await meApi()
      currentUser.value = {
        user_id: resp?.data?.user_id,
        email: resp?.data?.email || '',
      }
      membershipStatus.value = {
        is_vip: Boolean(resp?.data?.membership?.is_vip),
        plan_code: resp?.data?.membership?.is_vip ? 'vip_1m' : 'free',
        valid_until: String(resp?.data?.membership?.vip_valid_until || ''),
      }
      if (typeof onLoaded === 'function') {
        await onLoaded()
      }
    } catch (_error) {
      clearSession()
    }
  }

  async function registerAccount() {
    authError.value = ''
    authInfo.value = ''
    if (!authEmail.value.trim()) {
      authError.value = '请输入邮箱'
      return false
    }
    if (authPassword.value.length < 8) {
      authError.value = '密码至少 8 位'
      return false
    }
    if (authPassword.value !== authConfirmPassword.value) {
      authError.value = '两次输入密码不一致'
      return false
    }
    authLoading.value = true
    try {
      await registerApi({ email: authEmail.value.trim(), password: authPassword.value })
      authMode.value = 'login'
      authInfo.value = '注册成功，请登录。'
      authConfirmPassword.value = ''
      return true
    } catch (error) {
      authError.value = error.message || '注册失败'
      return false
    } finally {
      authLoading.value = false
    }
  }

  async function loginAccount(onSuccess) {
    authError.value = ''
    authInfo.value = ''
    authLoading.value = true
    try {
      const resp = await loginApi({ email: authEmail.value.trim(), password: authPassword.value })
      const token = resp?.data?.access_token || ''
      if (!token) throw new Error('登录成功但未返回 token')
      setAccessToken(token)
      if (typeof onSuccess === 'function') {
        await onSuccess()
      }
      closeAuthDialog()
      return true
    } catch (error) {
      authError.value = error.message || '登录失败'
      return false
    } finally {
      authLoading.value = false
    }
  }

  async function requestPasswordResetEmail() {
    authError.value = ''
    authInfo.value = ''
    if (!authEmail.value.trim()) {
      authError.value = '请输入邮箱地址后再发送重置邮件'
      return false
    }
    authLoading.value = true
    try {
      await requestPasswordResetApi({ email: authEmail.value.trim() })
      authInfo.value = '重置密码邮件已发送，请到邮箱点击链接继续。'
      return true
    } catch (error) {
      authError.value = error.message || '发送重置邮件失败'
      return false
    } finally {
      authLoading.value = false
    }
  }

  async function completePasswordReset() {
    authError.value = ''
    authInfo.value = ''
    if (!authActionToken.value.trim()) {
      authError.value = '重置令牌缺失，请重新打开邮箱中的重置链接'
      return false
    }
    if (authPassword.value.length < 8) {
      authError.value = '新密码至少 8 位'
      return false
    }
    if (authPassword.value !== authConfirmPassword.value) {
      authError.value = '两次输入密码不一致'
      return false
    }
    authLoading.value = true
    try {
      await resetPasswordApi({ token: authActionToken.value.trim(), new_password: authPassword.value })
      authMode.value = 'login'
      authActionToken.value = ''
      authPassword.value = ''
      authConfirmPassword.value = ''
      authInfo.value = '密码重置成功，请使用新密码登录。'
      return true
    } catch (error) {
      authError.value = error.message || '密码重置失败'
      return false
    } finally {
      authLoading.value = false
    }
  }

  function handleResetPasswordQuery() {
    const params = new URLSearchParams(window.location.search)
    const action = params.get('action') || ''
    const token = params.get('token') || ''
    if (action === 'reset_password' && token) {
      openAuthDialog('reset')
      authActionToken.value = token
      authInfo.value = '请输入新密码完成重置。'
      window.history.replaceState({}, '', window.location.pathname + window.location.hash)
      return true
    }
    return false
  }

  function logoutAccount() {
    clearSession()
  }

  return {
    accessToken,
    currentUser,
    membershipStatus,
    isLoggedIn,
    isVipUser,
    vipValidUntilText,
    authDialogVisible,
    authMode,
    authEmail,
    authPassword,
    authConfirmPassword,
    authActionToken,
    authLoading,
    authError,
    authInfo,
    setAccessToken,
    resetMembershipStatus,
    clearSession,
    openAuthDialog,
    closeAuthDialog,
    switchAuthMode,
    loadCurrentUser,
    registerAccount,
    loginAccount,
    requestPasswordResetEmail,
    completePasswordReset,
    handleResetPasswordQuery,
    logoutAccount,
  }
}
