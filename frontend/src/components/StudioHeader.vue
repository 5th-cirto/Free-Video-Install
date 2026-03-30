<script setup>
// 顶部状态栏仅负责展示汇总信息，不包含业务逻辑。
defineProps({
  runningCount: { type: Number, default: 0 },
  successCount: { type: Number, default: 0 },
  failedCount: { type: Number, default: 0 },
  userEmail: { type: String, default: '' },
  isVip: { type: Boolean, default: false },
  vipValidUntil: { type: String, default: '' },
  billingLoading: { type: Boolean, default: false },
  paymentSandbox: { type: Boolean, default: false },
})
defineEmits(['login', 'register', 'logout', 'buy-vip', 'open-billing'])
</script>

<template>
  <!-- 页面顶部：品牌 + 任务统计 -->
  <header class="top-nav">
    <div class="brand-wrap">
      <span class="badge">PRO</span>
      <div class="brand-text">
        <h1 class="brand-heading">万能视频下载总结器</h1>
        <span>下载与 AI 总结一体化工作台</span>
      </div>
    </div>
    <div class="account-panel">
      <template v-if="userEmail">
        <el-tag class="account-tag">账号 {{ userEmail }}</el-tag>
        <el-tag v-if="isVip" class="member-tag member-tag-vip" type="warning">VIP {{ vipValidUntil || '有效期内' }}</el-tag>
        <el-tag v-else class="member-tag" type="info">免费版</el-tag>
        <el-tag v-if="paymentSandbox" class="member-tag member-tag-sandbox" type="warning">支付沙盒模式</el-tag>
        <el-button class="action-btn" @click="$emit('open-billing')">账单记录</el-button>
        <el-button v-if="!isVip" class="action-btn action-primary" type="primary" :loading="billingLoading" @click="$emit('buy-vip')">
          {{ billingLoading ? '跳转中...' : paymentSandbox ? '开通 VIP（测试）' : '开通 VIP' }}
        </el-button>
        <el-button class="action-btn" @click="$emit('logout')">退出登录</el-button>
      </template>
      <template v-else>
        <el-button class="action-btn action-primary" type="primary" @click="$emit('login')">登录</el-button>
        <el-button class="action-btn" @click="$emit('register')">注册</el-button>
      </template>
    </div>
  </header>
</template>

<style scoped>
/* 顶部容器 */
.top-nav {
  border-radius: 16px;
  border: 1px solid #d7e2f3;
  background: linear-gradient(180deg, #ffffff 0%, #f6f9ff 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  gap: 14px;
  box-shadow: 0 8px 24px rgba(21, 45, 90, 0.08);
}

/* 左侧品牌区 */
.brand-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.badge {
  border-radius: 999px;
  padding: 4px 10px;
  background: linear-gradient(130deg, #1f6fff, #4a8bff);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.brand-text .brand-heading {
  margin: 0;
  color: #162544;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.1;
}

.brand-text span {
  color: #62739a;
  font-size: 12px;
}

/* 右侧统计标签 */
.quick-stats {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.quick-stats span {
  border: 1px solid #d4dded;
  background: #f7faff;
  color: #43557d;
  border-radius: 999px;
  font-size: 12px;
  padding: 5px 10px;
  white-space: nowrap;
}

.account-panel {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.account-tag,
.member-tag {
  border: 1px solid #d4dded;
  background: #f7faff;
  color: #43557d;
  border-radius: 999px;
  font-size: 12px;
  padding: 5px 10px;
  white-space: nowrap;
}

.member-tag-vip {
  border-color: #ffd57c;
  background: #fff7e3;
  color: #996900;
}

.member-tag-sandbox {
  border-color: #ffd1a6;
  background: #fff2e5;
  color: #9f4e00;
}

.action-btn {
  border: 1px solid #d4dded;
  background: #ffffff;
  color: #33476f;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 10px;
  cursor: pointer;
}

.action-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.action-primary {
  border-color: #1f6fff;
  background: #1f6fff;
  color: #fff;
}

/* 小屏下改为纵向布局，避免挤压 */
@media (max-width: 960px) {
  .top-nav {
    flex-direction: column;
    align-items: flex-start;
  }

  .quick-stats {
    width: 100%;
  }

  .account-panel {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
