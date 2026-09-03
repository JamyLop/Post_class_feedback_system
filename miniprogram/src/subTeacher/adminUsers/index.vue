<template>
  <view class="page">
    <view class="tabs">
      <view class="tab-bar">
        <text class="tab" :class="{ active: tab==='users' }" @click="tab='users'">用户管理</text>
        <text class="tab" :class="{ active: tab==='invite' }" @click="tab='invite'">邀请码</text>
      </view>

      <view v-if="tab==='users'" class="tab-panel">
        <view class="filters">
          <picker :range="roleOptions" range-key="label" @change="onRoleChange">
            <view class="filter-btn">
              <text class="filter-text">{{ currentRoleLabel }}</text>
              <text class="filter-arrow">›</text>
            </view>
          </picker>
          <input v-model="keyword" placeholder="搜索姓名" class="search-input" @confirm="loadUsers" />
        </view>
        <view v-if="loadingUsers" class="loading-bar">
          <text class="loading-text">加载中...</text>
        </view>
        <template v-else>
          <view v-if="users.length" class="list">
            <view v-for="(u, idx) in users" :key="u.id" class="user-row" :class="{ 'has-border': idx > 0 }">
              <view class="user-avatar">{{ (u.name || '?').slice(0,1) }}</view>
              <view class="user-info">
                <text class="user-name">{{ u.name }}</text>
                <text class="user-meta">{{ u.username }} · {{ roleLabel(u.role) }}</text>
              </view>
              <view class="user-status" :class="u.status === 'active' ? 'active' : 'disabled'">
                {{ u.status === 'active' ? '正常' : '禁用' }}
              </view>
              <text class="edit-link" @click="editUser(u)">编辑</text>
            </view>
          </view>
          <view v-else class="empty-text">暂无用户</view>
          <button class="btn-outline" @click="showCreateUser = true">+ 新建用户</button>
        </template>
      </view>

      <view v-if="tab==='invite'" class="tab-panel">
        <view v-if="loadingInvite" class="loading-bar">
          <text class="loading-text">加载中...</text>
        </view>
        <template v-else>
          <view v-if="inviteCodes.length" class="list">
            <view v-for="(c, idx) in inviteCodes" :key="c.id" class="invite-row" :class="{ 'has-border': idx > 0 }">
              <view class="invite-info">
                <text class="invite-code">{{ c.code }}</text>
                <text class="invite-meta">{{ roleLabel(c.role) }} · {{ (c.created_at||'').slice(0,10) }}</text>
              </view>
              <text v-if="c.status==='active'" class="danger-link" @click="disableCode(c)">停用</text>
              <text v-else class="disabled-text">已停用</text>
            </view>
          </view>
          <view v-else class="empty-text">暂无邀请码</view>
          <view class="create-row">
            <picker :range="inviteRoleOptions" range-key="label" @change="newInviteRole = inviteRoleOptions[e.detail.value].value">
              <view class="filter-btn">
                <text class="filter-text">{{ inviteRoleLabel }}</text>
                <text class="filter-arrow">›</text>
              </view>
            </picker>
            <button class="btn-primary-sm" :loading="creatingInvite" @click="createCode">生成</button>
          </view>
        </template>
      </view>
    </view>

    <view v-if="showCreateUser" class="modal-mask" @click.self="showCreateUser=false">
      <view class="modal">
        <view class="modal-header">
          <text class="modal-title">新建用户</text>
          <text class="modal-close" @click="showCreateUser=false">✕</text>
        </view>
        <view class="form">
          <view class="field">
            <text class="label">用户名</text>
            <input v-model="newUser.username" class="input" placeholder="用户名" />
          </view>
          <view class="field">
            <text class="label">密码</text>
            <input v-model="newUser.password" class="input" password placeholder="密码" />
          </view>
          <view class="field">
            <text class="label">姓名</text>
            <input v-model="newUser.name" class="input" placeholder="姓名" />
          </view>
          <view class="field">
            <text class="label">角色</text>
            <picker :range="createRoleOptions" range-key="label" @change="e => newUser.role = createRoleOptions[e.detail.value].value">
              <view class="picker">{{ createRoleLabel }}</view>
            </picker>
          </view>
        </view>
        <view class="modal-btns">
          <button class="btn-outline" @click="showCreateUser=false">取消</button>
          <button class="btn-primary" :loading="creatingUser" @click="doCreateUser">创建</button>
        </view>
      </view>
    </view>

    <view v-if="editingUser" class="modal-mask" @click.self="editingUser=null">
      <view class="modal">
        <view class="modal-header">
          <text class="modal-title">编辑 {{ editingUser.name }}</text>
          <text class="modal-close" @click="editingUser=null">✕</text>
        </view>
        <view class="form">
          <view class="field">
            <text class="label">姓名</text>
            <input v-model="editForm.name" class="input" placeholder="姓名" />
          </view>
          <view class="field">
            <text class="label">新密码（留空不改）</text>
            <input v-model="editForm.password" class="input" password placeholder="新密码" />
          </view>
          <view class="field">
            <text class="label">状态</text>
            <picker :range="statusOptions" range-key="label" @change="e => editForm.status = statusOptions[e.detail.value].value">
              <view class="picker">{{ editStatusLabel }}</view>
            </picker>
          </view>
        </view>
        <view class="modal-btns">
          <button class="btn-outline" @click="editingUser=null">取消</button>
          <button class="btn-primary" :loading="savingUser" @click="doSaveUser">保存</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listUsers, createUser, updateUser, listInviteCodes, createInviteCode, disableInviteCode } from '../../api/studentCases'

const auth = useAuthStore()
const tab = ref('users')

const loadingUsers = ref(false)
const users = ref([])
const keyword = ref('')
const selectedRole = ref('student')
const roleOptions = [
  { value: 'student', label: '学生' },
  { value: 'teacher', label: '教师' },
  { value: 'deyu_director', label: '德育主任' },
  { value: 'parent', label: '家长' },
  { value: 'admin', label: '校长' },
]
const currentRoleLabel = computed(() => roleOptions.find(r => r.value === selectedRole.value)?.label || '')
function roleLabel(v) { return roleOptions.find(r => r.value === v)?.label || v }
function onRoleChange(e) { selectedRole.value = roleOptions[e.detail.value].value; loadUsers() }

const showCreateUser = ref(false)
const creatingUser = ref(false)
const newUser = reactive({ username: '', password: '', name: '', role: 'student' })
const createRoleOptions = roleOptions.filter(r => r.value !== 'admin')
const createRoleLabel = computed(() => createRoleOptions.find(r => r.value === newUser.role)?.label || '')

const editingUser = ref(null)
const savingUser = ref(false)
const editForm = reactive({ name: '', password: '', status: 'active' })
const statusOptions = [{ value: 'active', label: '正常' }, { value: 'disabled', label: '禁用' }]
const editStatusLabel = computed(() => statusOptions.find(s => s.value === editForm.status)?.label || '')

async function loadUsers() {
  loadingUsers.value = true
  try { users.value = await listUsers({ role: selectedRole.value, keyword: keyword.value || undefined }) }
  catch (_) { users.value = [] } finally { loadingUsers.value = false }
}

async function doCreateUser() {
  if (!newUser.username || !newUser.password || !newUser.name) return uni.showToast({ title: '请填写完整', icon: 'none' })
  creatingUser.value = true
  try {
    await createUser(newUser)
    showCreateUser.value = false
    uni.showToast({ title: '创建成功', icon: 'success' })
    loadUsers()
  } catch (e) { uni.showToast({ title: e.message || '创建失败', icon: 'none' }) } finally { creatingUser.value = false }
}

function editUser(u) {
  editingUser.value = u
  editForm.name = u.name
  editForm.password = ''
  editForm.status = u.status || 'active'
}

async function doSaveUser() {
  savingUser.value = true
  try {
    const data = { name: editForm.name, status: editForm.status }
    if (editForm.password) data.password = editForm.password
    await updateUser(editingUser.value.id, data)
    editingUser.value = null
    uni.showToast({ title: '已保存', icon: 'success' })
    loadUsers()
  } catch (e) { uni.showToast({ title: e.message || '保存失败', icon: 'none' }) } finally { savingUser.value = false }
}

const loadingInvite = ref(false)
const inviteCodes = ref([])
const creatingInvite = ref(false)
const newInviteRole = ref('teacher')
const inviteRoleOptions = roleOptions.filter(r => r.value !== 'admin')
const inviteRoleLabel = computed(() => inviteRoleOptions.find(r => r.value === newInviteRole.value)?.label || '')

async function loadInvite() {
  loadingInvite.value = true
  try { inviteCodes.value = await listInviteCodes() }
  catch (_) { inviteCodes.value = [] } finally { loadingInvite.value = false }
}

async function createCode() {
  creatingInvite.value = true
  try {
    await createInviteCode({ role: newInviteRole.value })
    uni.showToast({ title: '已生成', icon: 'success' })
    loadInvite()
  } catch (e) { uni.showToast({ title: e.message || '生成失败', icon: 'none' }) } finally { creatingInvite.value = false }
}

async function disableCode(c) {
  uni.showModal({
    title: '停用邀请码',
    content: `确定停用 ${c.code}？`,
    success: async (res) => {
      if (!res.confirm) return
      try { await disableInviteCode(c.id); loadInvite() } catch (_) {}
    }
  })
}

onShow(() => {
  if (auth.role !== 'admin') { uni.reLaunch({ url: '/pages/index/index' }); return }
  const pages = getCurrentPages()
  const cur = pages[pages.length - 1]
  if (cur.options?.tab === 'invite') tab.value = 'invite'
  loadUsers()
  loadInvite()
})
</script>

<style scoped>
.page { padding: 24rpx 20rpx 48rpx; display: flex; flex-direction: column; gap: 16rpx; }
.tabs {
  background: #fff; border-radius: 20rpx; overflow: hidden;
  box-shadow: 0 2rpx 16rpx rgba(107,92,231,0.06);
}
.tab-bar { display: flex; border-bottom: 2rpx solid #F0EFFC; }
.tab {
  flex: 1; text-align: center; padding: 22rpx 0;
  font-size: 26rpx; color: #8E8B9E;
  border-bottom: 4rpx solid transparent;
}
.tab.active { color: #6B5CE7; border-bottom-color: #6B5CE7; font-weight: 600; }
.tab-panel { padding: 22rpx; display: flex; flex-direction: column; gap: 14rpx; }

.filters { display: flex; gap: 12rpx; }
.filter-btn {
  display: flex; align-items: center; gap: 6rpx;
  background: #FAF9F7; border: 2rpx solid #E8E6F0;
  border-radius: 12rpx; padding: 14rpx 18rpx;
}
.filter-text { font-size: 26rpx; color: #1A1636; }
.filter-arrow { font-size: 22rpx; color: #B8B0F6; }
.search-input {
  flex: 1; border: 2rpx solid #E8E6F0; border-radius: 12rpx;
  padding: 14rpx 18rpx; font-size: 26rpx; background: #fff;
}

.loading-bar { text-align: center; padding: 32rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }
.list { display: flex; flex-direction: column; gap: 0; }

.user-row { display: flex; align-items: center; gap: 14rpx; padding: 14rpx 0; }
.user-row.has-border { border-top: 2rpx solid #F0EFFC; }
.user-avatar {
  width: 56rpx; height: 56rpx;
  background: linear-gradient(135deg, #6B5CE7, #8B78F0);
  border-radius: 14rpx; display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 22rpx; font-weight: 700; flex-shrink: 0;
}
.user-info { flex: 1; }
.user-name { font-size: 26rpx; font-weight: 600; color: #1A1636; display: block; }
.user-meta { font-size: 20rpx; color: #A09CB5; display: block; margin-top: 2rpx; }
.user-status {
  font-size: 20rpx; padding: 4rpx 12rpx; border-radius: 12rpx;
  flex-shrink: 0;
}
.user-status.active { background: #DCFCE7; color: #16A34A; }
.user-status.disabled { background: #FEE2E2; color: #EF4444; }
.edit-link { font-size: 24rpx; color: #6B5CE7; flex-shrink: 0; }

.invite-row { display: flex; align-items: center; gap: 14rpx; padding: 14rpx 0; }
.invite-row.has-border { border-top: 2rpx solid #F0EFFC; }
.invite-info { flex: 1; }
.invite-code { font-size: 28rpx; font-weight: 700; color: #1A1636; font-family: monospace; display: block; }
.invite-meta { font-size: 20rpx; color: #A09CB5; display: block; margin-top: 2rpx; }
.danger-link { font-size: 24rpx; color: #EF4444; flex-shrink: 0; }
.disabled-text { font-size: 22rpx; color: #C4C0D4; flex-shrink: 0; }

.empty-text { text-align: center; color: #A09CB5; padding: 28rpx; font-size: 24rpx; }
.create-row { display: flex; gap: 12rpx; align-items: center; }

.btn-primary-sm {
  background: linear-gradient(135deg, #6B5CE7, #8B78F0);
  color: #fff; border-radius: 12rpx; padding: 12rpx 28rpx;
  font-size: 26rpx; font-weight: 600; border: none;
}
.btn-primary-sm::after { border: none; }
.btn-primary {
  background: linear-gradient(135deg, #6B5CE7, #8B78F0);
  color: #fff; border-radius: 14rpx; padding: 22rpx 0;
  font-size: 28rpx; font-weight: 600; border: none;
}
.btn-primary::after { border: none; }
.btn-outline {
  background: #fff; color: #6B5CE7;
  border: 2rpx solid #D5D0F7; border-radius: 14rpx;
  padding: 22rpx 0; font-size: 28rpx;
}
.btn-outline::after { border: none; }

.modal-mask {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(26,22,54,0.45);
  display: flex; align-items: flex-end; z-index: 999;
}
.modal {
  background: #fff; border-radius: 24rpx 24rpx 0 0;
  padding: 28rpx; width: 100%; max-height: 80vh;
  overflow-y: auto; display: flex; flex-direction: column; gap: 14rpx;
}
.modal-header { display: flex; justify-content: space-between; align-items: center; }
.modal-title { font-size: 32rpx; font-weight: 700; color: #1A1636; }
.modal-close { font-size: 28rpx; color: #A09CB5; padding: 8rpx; }
.form { display: flex; flex-direction: column; gap: 12rpx; }
.field { display: flex; flex-direction: column; gap: 6rpx; }
.label { font-size: 24rpx; font-weight: 600; color: #1A1636; }
.input {
  border: 2rpx solid #E8E6F0; border-radius: 14rpx;
  padding: 18rpx 20rpx; font-size: 26rpx; background: #fff;
}
.picker {
  border: 2rpx solid #E8E6F0; border-radius: 14rpx;
  padding: 18rpx 20rpx; background: #fff; font-size: 26rpx; color: #1A1636;
}
.modal-btns { display: flex; gap: 14rpx; margin-top: 8rpx; }
.modal-btns button { flex: 1; }
</style>
