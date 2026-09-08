<template>
  <view class="page">
    <WorkspaceLink />
    <text class="h1">快速打卡</text>

    <view v-if="loadingCase" class="loading-bar">
      <text class="loading-text">加载档案...</text>
    </view>
    <template v-else>
      <view v-if="!tasks.length" class="empty-text">该档案暂无可打卡任务</view>
      <template v-else>
        <view class="card">
          <view class="field">
            <text class="label">选择任务</text>
            <picker :range="tasks" range-key="label" @change="onTaskChange">
              <view class="picker">{{ selectedTaskLabel || '请选择任务' }}</view>
            </picker>
          </view>

          <view v-if="selectedTask" class="task-preview">
            <text class="preview-subject">{{ selectedTask.subject || '综合' }}</text>
            <text class="preview-title">{{ selectedTask.title }}</text>
            <text class="preview-meta">{{ selectedTask.starts_on }} 至 {{ selectedTask.due_on }} · {{ cadenceLabel(selectedTask.cadence) }}{{ selectedTask.cadence === 'weekly' && selectedTask.weekly_times ? ` · 每周${selectedTask.weekly_times}次` : '' }}</text>
          </view>

          <view class="field">
            <text class="label">积分规则</text>
            <text class="score-note">打卡即得 1 分（单科单日封顶1分、单科周封顶7分）</text>
          </view>

          <view class="field">
            <text class="label">班主任记录</text>
            <textarea v-model="form.self_check" placeholder="实际执行情况、问题与要求" class="textarea" />
          </view>

          <view class="field">
            <text class="label">打卡照片（最多 {{ MAX_PHOTOS }} 张）</text>
            <view class="photo-grid">
              <view v-for="(p, idx) in photos" :key="idx" class="photo-cell">
                <image :src="p.path" class="photo-thumb" mode="aspectFill" @click="previewPhotos(idx)" />
                <text class="photo-remove" @click.stop="removePhoto(idx)">×</text>
              </view>
              <view v-if="photos.length < MAX_PHOTOS" class="photo-add" @click="choosePhotos">
                <text class="photo-add-icon">+</text>
                <text class="photo-add-text">拍照/选图</text>
              </view>
            </view>
            <text v-if="uploading" class="upload-hint">正在上传照片 {{ uploadDone }}/{{ photos.length }}…</text>
            <text v-else-if="!photos.length" class="upload-hint">仅支持 PNG / JPEG / GIF / WebP，单张不超过 10MB</text>
          </view>
        </view>
        <button class="btn-primary" :loading="submitting" :disabled="submitting || uploading" @click="submit">提交打卡</button>
        <text class="hint">打卡即得 1 分，单科单日封顶1分、单科周封顶7分</text>
      </template>
    </template>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, reactive, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { getStudentCase, checkinCaseTask, uploadCheckinAttachment } from '../../api/studentCases'

const loadingCase = ref(false)
const submitting = ref(false)
const uploading = ref(false)
const uploadDone = ref(0)
// 与 Web 端保持一致：一次打卡最多 5 张；后端另限制单张 10MB 内图片
const MAX_PHOTOS = 5
const MAX_PHOTO_BYTES = 10 * 1024 * 1024
const photos = ref([])
const detail = ref(null)
const selectedTaskId = ref(null)
const form = reactive({ self_check: '' })

const tasks = computed(() => (detail.value?.tasks || []).map(t => ({
  ...t,
  label: `${t.subject || '综合'} · ${t.title} (${t.status})`,
})))
const selectedTask = computed(() => tasks.value.find(t => t.id === selectedTaskId.value))
const selectedTaskLabel = computed(() => selectedTask.value?.label || '')

function getParams() {
  const pages = getCurrentPages()
  const cur = pages[pages.length - 1]
  return cur.options || cur.$page?.options || {}
}

function onTaskChange(e) {
  const task = tasks.value[e.detail.value]
  selectedTaskId.value = task?.id || null
}

function cadenceLabel(v) {
  return { daily: '日计划', weekly: '周计划', monthly: '月计划' }[v] || v || ''
}

async function load() {
  loadingCase.value = true
  try {
    const opts = getParams()
    const caseId = opts.caseId || opts.case_id
    if (!caseId) throw new Error('缺少 caseId')
    detail.value = await getStudentCase(caseId)
    const taskId = opts.taskId || opts.task_id
    if (taskId) selectedTaskId.value = Number(taskId)
  } catch (e) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally { loadingCase.value = false }
}

async function submit() {
  if (!selectedTaskId.value) return uni.showToast({ title: '请选择任务', icon: 'none' })
  submitting.value = true
  try {
    // 先落打卡记录，再逐张上传照片；照片失败不回滚打卡（与 Web 端一致）
    // 打卡即得满分 1 分：不再填写完成度，固定按 100% 提交
    const saved = await checkinCaseTask(selectedTaskId.value, { completion_rate: 100, self_check: form.self_check })
    let okCount = 0
    let failCount = 0
    if (photos.value.length && saved?.id) {
      uploading.value = true
      uploadDone.value = 0
      for (const p of photos.value) {
        try {
          await uploadCheckinAttachment(saved.id, p.path, { showError: false })
          okCount += 1
        } catch (e) {
          console.warn('[checkin] 照片上传失败', e?.message || e)
          failCount += 1
        } finally {
          uploadDone.value += 1
        }
      }
      uploading.value = false
    }
    if (failCount) {
      uni.showToast({ title: `打卡成功，但${failCount}张照片上传失败`, icon: 'none' })
    } else if (okCount) {
      uni.showToast({ title: `打卡成功，照片${okCount}张`, icon: 'success' })
    } else {
      uni.showToast({ title: '打卡成功', icon: 'success' })
    }
    setTimeout(() => uni.navigateBack(), 1500)
  } catch (e) {
    uni.showToast({ title: e.message || '打卡失败', icon: 'none' })
  } finally { submitting.value = false }
}

function choosePhotos() {
  const remain = MAX_PHOTOS - photos.value.length
  if (remain <= 0) {
    uni.showToast({ title: `最多${MAX_PHOTOS}张照片`, icon: 'none' })
    return
  }
  uni.chooseImage({
    count: remain,
    sizeType: ['compressed'],
    sourceType: ['album', 'camera'],
    success(res) {
      for (const file of res.tempFiles || []) {
        if (file.size > MAX_PHOTO_BYTES) {
          uni.showToast({ title: '单张照片不能超过 10MB', icon: 'none' })
          continue
        }
        if (photos.value.length >= MAX_PHOTOS) break
        photos.value.push({ path: file.path, size: file.size })
      }
    },
    fail(err) {
      // 用户取消选择不提示
      if (!String(err?.errMsg || '').includes('cancel')) {
        uni.showToast({ title: '选择照片失败', icon: 'none' })
      }
    },
  })
}

function removePhoto(idx) {
  photos.value.splice(idx, 1)
}

function previewPhotos(idx) {
  const urls = photos.value.map(p => p.path)
  if (urls.length) uni.previewImage({ urls, current: urls[idx] || urls[0] })
}

onShow(() => load())

</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }
.empty-text { text-align: center; color: var(--mp-muted); padding: 36rpx; font-size: 24rpx; }
.hint { text-align: center; color: var(--mp-muted); font-size: 24rpx; }

.card {
  background: #fff;
  border-radius: 20rpx;
  padding: 28rpx;
  box-shadow: none;
  display: flex; flex-direction: column; gap: 20rpx;
}
.field { display: flex; flex-direction: column; gap: 8rpx; }
.label { font-size: 24rpx; font-weight: 600; color: var(--mp-ink); }
.picker {
  border: 2rpx solid var(--mp-line); border-radius: 14rpx;
  padding: 18rpx 20rpx; background: #fff; font-size: 26rpx; color: var(--mp-ink);
}

.task-preview {
  background: #F7F8FA; border-radius: 14rpx; padding: 18rpx;
}
.preview-subject { font-size: 24rpx; color: var(--mp-primary); font-weight: 500; }
.preview-title { font-size: 28rpx; font-weight: 600; color: var(--mp-ink); display: block; margin-top: 6rpx; }
.preview-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; }

.rate-row { display: flex; align-items: center; gap: 16rpx; }
.score-note { font-size: 26rpx; color: var(--mp-muted); }
.slider { flex: 1; }
.rate-num { font-size: 32rpx; font-weight: 700; color: var(--mp-primary); min-width: 80rpx; text-align: right; }
.textarea {
  border: 2rpx solid var(--mp-line); border-radius: 14rpx;
  padding: 18rpx 20rpx; font-size: 26rpx; min-height: 160rpx; background: #fff;
}

.photo-grid { display: flex; flex-wrap: wrap; gap: 14rpx; }
.photo-cell { position: relative; width: 160rpx; height: 160rpx; }
.photo-thumb { width: 160rpx; height: 160rpx; border-radius: 12rpx; background: #EDF1F7; }
.photo-remove {
  position: absolute; top: -14rpx; right: -14rpx; width: 40rpx; height: 40rpx;
  border-radius: 50%; background: rgba(0, 0, 0, 0.55); color: #fff;
  font-size: 30rpx; line-height: 40rpx; text-align: center;
}
.photo-add {
  width: 160rpx; height: 160rpx; border-radius: 12rpx;
  border: 2rpx dashed #C6D0DE; background: #F7F8FA;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6rpx;
}
.photo-add-icon { font-size: 52rpx; color: #98A4B5; line-height: 1; }
.photo-add-text { font-size: 22rpx; color: #98A4B5; }
.upload-hint { font-size: 22rpx; color: var(--mp-muted); }

.btn-primary {
  background: var(--mp-primary);
  color: #fff; border-radius: 14rpx; padding: 24rpx 0;
  font-size: 30rpx; font-weight: 600; border: none;
}
.btn-primary::after { border: none; }
</style>
