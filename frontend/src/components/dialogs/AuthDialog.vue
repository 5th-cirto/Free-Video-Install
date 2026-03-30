<script setup>
const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'login' },
  email: { type: String, default: '' },
  password: { type: String, default: '' },
  confirmPassword: { type: String, default: '' },
  actionToken: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  info: { type: String, default: '' },
})

const emit = defineEmits([
  'update:visible',
  'update:email',
  'update:password',
  'update:confirmPassword',
  'update:actionToken',
  'close',
  'switchMode',
  'register',
  'login',
  'resetPassword',
  'requestResetEmail',
  'backLogin',
])

function onClose() {
  emit('update:visible', false)
  emit('close')
}
</script>

<template>
  <el-dialog :model-value="visible" width="460px" destroy-on-close :close-on-click-modal="true" @close="onClose">
    <template #header>
      <h3 class="dialog-title">{{ mode === 'register' ? '注册账号' : mode === 'reset' ? '重置密码' : '登录账号' }}</h3>
    </template>
    <p class="dialog-subtitle">登录后可使用 AI 总结并购买 VIP。</p>

    <el-form label-position="top">
      <el-form-item label="邮箱">
        <el-input
          :model-value="email"
          type="email"
          placeholder="you@example.com"
          :disabled="mode === 'reset'"
          @update:model-value="emit('update:email', $event)"
        />
      </el-form-item>

      <template v-if="mode === 'reset'">
        <el-form-item label="重置令牌（来自邮箱链接）">
          <el-input
            :model-value="actionToken"
            placeholder="自动填充或手动粘贴 token"
            @update:model-value="emit('update:actionToken', $event)"
          />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input :model-value="password" type="password" placeholder="至少 8 位" show-password @update:model-value="emit('update:password', $event)" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input
            :model-value="confirmPassword"
            type="password"
            placeholder="再次输入密码"
            show-password
            @update:model-value="emit('update:confirmPassword', $event)"
          />
        </el-form-item>
      </template>

      <template v-else>
        <el-form-item label="密码">
          <el-input :model-value="password" type="password" placeholder="至少 8 位" show-password @update:model-value="emit('update:password', $event)" />
        </el-form-item>
        <el-form-item v-if="mode === 'register'" label="确认密码">
          <el-input
            :model-value="confirmPassword"
            type="password"
            placeholder="再次输入密码"
            show-password
            @update:model-value="emit('update:confirmPassword', $event)"
          />
        </el-form-item>
      </template>
    </el-form>

    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <el-alert v-if="info" :title="info" type="success" :closable="false" show-icon style="margin-top: 8px" />

    <div class="dialog-actions">
      <el-button @click="onClose">取消</el-button>
      <el-button v-if="mode === 'register'" type="primary" :loading="loading" @click="emit('register')">注册</el-button>
      <el-button v-else-if="mode === 'login'" type="primary" :loading="loading" @click="emit('login')">登录</el-button>
      <el-button v-else type="primary" :loading="loading" @click="emit('resetPassword')">重置密码</el-button>
    </div>

    <div class="dialog-extra" v-if="mode !== 'reset'">
      <el-button text type="primary" @click="emit('switchMode')">
        {{ mode === 'register' ? '已有账号？去登录' : '没有账号？去注册' }}
      </el-button>
      <el-button text type="primary" v-if="mode === 'login'" @click="emit('requestResetEmail')">忘记密码</el-button>
    </div>
    <div class="dialog-extra" v-else>
      <el-button text type="primary" @click="emit('backLogin')">返回登录</el-button>
    </div>
  </el-dialog>
</template>

<style scoped>
.dialog-title {
  margin: 0;
  font-size: 20px;
}
.dialog-subtitle {
  margin: 0 0 10px;
  color: #5f6f8c;
}
.dialog-actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.dialog-extra {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
}
</style>
