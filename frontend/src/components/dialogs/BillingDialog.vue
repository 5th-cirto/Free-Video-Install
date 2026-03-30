<script setup>
const props = defineProps({
  visible: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  orders: { type: Array, default: () => [] },
  paymentSandbox: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'close'])

function onClose() {
  emit('update:visible', false)
  emit('close')
}
</script>

<template>
  <el-dialog :model-value="visible" width="640px" destroy-on-close @close="onClose">
    <template #header>
      <h3 class="dialog-title">账单与订单历史</h3>
    </template>
    <p class="dialog-subtitle">最近 100 条会员订单记录（按时间倒序）。</p>
    <el-alert
      v-if="paymentSandbox"
      class="sandbox-tip"
      title="当前为 Stripe 测试环境：账单与会员状态仅用于开源学习演示，不代表真实交易。"
      type="warning"
      :closable="false"
      show-icon
    />
    <p v-if="paymentSandbox" class="sandbox-note">
      测试卡示例：4242 4242 4242 4242，任意未来日期、任意 CVC、任意邮编即可完成测试支付。
    </p>

    <el-skeleton :loading="loading" animated :rows="5">
      <template #default>
        <el-empty v-if="!orders.length" description="暂无订单记录。" />
        <el-table v-else :data="orders" size="small" stripe>
          <el-table-column prop="order_id" label="订单号" min-width="90" />
          <el-table-column prop="status" label="状态" min-width="88" />
          <el-table-column prop="plan_code" label="套餐" min-width="88" />
          <el-table-column label="金额" min-width="100">
            <template #default="{ row }">
              {{ (Number(row.amount_cents || 0) / 100).toFixed(2) }} {{ String(row.currency || '').toUpperCase() }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="170" />
          <el-table-column prop="paid_at" label="支付时间" min-width="170" />
        </el-table>
      </template>
    </el-skeleton>

    <template #footer>
      <el-button @click="onClose">关闭</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.dialog-title {
  margin: 0;
  font-size: 20px;
}
.dialog-subtitle {
  margin: 0 0 12px;
  color: #5f6f8c;
}

.sandbox-tip {
  margin: 0 0 8px;
}

.sandbox-note {
  margin: 0 0 12px;
  color: #8a5b12;
  font-size: 12px;
}
</style>
