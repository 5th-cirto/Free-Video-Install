import { ref } from 'vue'
import { checkoutSessionApi, membershipStatusApi, ordersApi } from '../api/billing'

export function useBilling({ isLoggedIn, openAuthDialog, membershipStatus, actionError }) {
  const billingLoading = ref(false)
  const billingDialogVisible = ref(false)
  const billingHistoryLoading = ref(false)
  const billingOrders = ref([])

  async function loadMembershipStatus() {
    if (!isLoggedIn.value) return
    try {
      const resp = await membershipStatusApi()
      membershipStatus.value = {
        is_vip: Boolean(resp?.data?.is_vip),
        plan_code: String(resp?.data?.plan_code || 'free'),
        valid_until: String(resp?.data?.valid_until || ''),
      }
    } catch (_error) {
      membershipStatus.value = {
        is_vip: false,
        plan_code: 'free',
        valid_until: '',
      }
    }
  }

  async function loadBillingOrders() {
    if (!isLoggedIn.value) return
    billingHistoryLoading.value = true
    try {
      const resp = await ordersApi()
      billingOrders.value = resp?.data?.orders || []
    } catch (error) {
      if (actionError) actionError.value = error.message || '加载账单记录失败'
    } finally {
      billingHistoryLoading.value = false
    }
  }

  function openBillingDialog() {
    if (!isLoggedIn.value) {
      openAuthDialog('login')
      return
    }
    billingDialogVisible.value = true
    loadBillingOrders()
  }

  function closeBillingDialog() {
    billingDialogVisible.value = false
  }

  async function startVipCheckout() {
    if (!isLoggedIn.value) {
      openAuthDialog('login')
      return
    }
    billingLoading.value = true
    if (actionError) actionError.value = ''
    try {
      const resp = await checkoutSessionApi({ plan_code: 'vip_1m', idempotency_key: `web-${Date.now()}` })
      const url = resp?.data?.checkout_url || ''
      if (!url) throw new Error('未获取到支付链接')
      window.location.href = url
    } catch (error) {
      if (actionError) actionError.value = error.message || '创建支付会话失败'
    } finally {
      billingLoading.value = false
    }
  }

  return {
    billingLoading,
    billingDialogVisible,
    billingHistoryLoading,
    billingOrders,
    loadMembershipStatus,
    loadBillingOrders,
    openBillingDialog,
    closeBillingDialog,
    startVipCheckout,
  }
}
