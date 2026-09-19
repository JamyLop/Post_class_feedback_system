<template>
  <el-image
    v-if="imageUrl"
    :src="imageUrl"
    :preview-src-list="[imageUrl]"
    fit="cover"
    class="checkin-thumb"
  >
    <template #error>
      <div class="checkin-thumb image-state" :title="failureMessage">
        <span>图片不可用</span>
        <el-button link size="small" @click.stop="loadImage">重试</el-button>
      </div>
    </template>
  </el-image>
  <div v-else class="checkin-thumb image-state" :title="failureMessage" @click="failed ? loadImage() : undefined">
    <span>{{ loading ? '加载中…' : (failed ? '图片不可用，点击重试' : '图片不可用') }}</span>
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import http from '../api'

const props = defineProps({
  checkinId: {
    type: Number,
    required: true,
  },
  attachmentIndex: {
    type: Number,
    required: true,
  },
  attachment: {
    type: Object,
    required: true,
  },
})

const imageUrl = ref('')
const loading = ref(false)
const failed = ref(false)
const failureMessage = ref('')
let seq = 0

function revokeImageUrl() {
  if (imageUrl.value.startsWith('blob:')) URL.revokeObjectURL(imageUrl.value)
  imageUrl.value = ''
}

function isDirectUrl(url) {
  // OSS/MinIO 预签名 https/http 直链可直接展示，无需走鉴权代理；
  // 本地存储相对路径（/api/storage/files/...）<img> 无法携带 token，必须走鉴权下载。
  return /^https?:\/\//i.test(url || '')
}

async function loadImage() {
  const cur = ++seq
  revokeImageUrl()
  failureMessage.value = ''
  failed.value = false
  const direct = props.attachment?.url
  if (isDirectUrl(direct)) {
    imageUrl.value = direct
    return
  }
  if (!props.attachment?.object_name) {
    failed.value = true
    failureMessage.value = direct ? '附件直链不可用且缺少存储标识' : '附件缺少存储标识'
    return
  }

  loading.value = true
  try {
    // 图片标签无法携带 Bearer 令牌；先走打卡附件专用的鉴权接口，再用 Blob URL 渲染。
    const blob = await http.get(`/student-cases/task-checkins/${props.checkinId}/attachments/${props.attachmentIndex}`, { responseType: 'blob' })
    if (cur !== seq) return
    if (!(blob instanceof Blob) || blob.size === 0) {
      throw new Error('图片内容为空')
    }
    imageUrl.value = URL.createObjectURL(blob)
  } catch (error) {
    if (cur !== seq) return
    failed.value = true
    const detail = error?.response?.data?.detail
    failureMessage.value = typeof detail === 'string' && detail ? detail : (error?.message || '图片读取失败')
  } finally {
    if (cur === seq) loading.value = false
  }
}

watch(() => [props.checkinId, props.attachmentIndex, props.attachment?.object_name, props.attachment?.url], loadImage, { immediate: true })
onBeforeUnmount(() => { seq += 1; revokeImageUrl() })
</script>

<style scoped>
.checkin-thumb { width: 64px; height: 64px; border-radius: 8px; border: 1px solid var(--line); cursor: pointer; }
.image-state { display: grid; place-items: center; align-content: center; gap: 2px; padding: 6px; box-sizing: border-box; color: var(--ink-muted); background: var(--surface-soft); cursor: default; font-size: 11px; text-align: center; }
</style>
