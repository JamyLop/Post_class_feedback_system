<template>
  <el-image
    v-if="imageUrl"
    :src="imageUrl"
    :preview-src-list="[imageUrl]"
    fit="cover"
    class="checkin-thumb"
  />
  <div v-else class="checkin-thumb image-state" :title="failureMessage">
    {{ loading ? '加载中…' : '图片不可用' }}
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
const failureMessage = ref('')

function revokeImageUrl() {
  if (imageUrl.value) URL.revokeObjectURL(imageUrl.value)
  imageUrl.value = ''
}

async function loadImage() {
  revokeImageUrl()
  failureMessage.value = ''
  if (!props.attachment?.object_name) {
    failureMessage.value = '附件缺少存储标识'
    return
  }

  loading.value = true
  try {
    // 图片标签无法携带 Bearer 令牌；先走打卡附件专用的鉴权接口，再用 Blob URL 渲染。
    const blob = await http.get(`/student-cases/task-checkins/${props.checkinId}/attachments/${props.attachmentIndex}`, { responseType: 'blob' })
    imageUrl.value = URL.createObjectURL(blob)
  } catch (error) {
    failureMessage.value = error?.response?.data?.detail || '图片读取失败'
  } finally {
    loading.value = false
  }
}

watch(() => [props.checkinId, props.attachmentIndex, props.attachment?.object_name], loadImage, { immediate: true })
onBeforeUnmount(revokeImageUrl)
</script>

<style scoped>
.checkin-thumb { width: 64px; height: 64px; border-radius: 8px; border: 1px solid var(--line); cursor: pointer; }
.image-state { display: grid; place-items: center; padding: 6px; box-sizing: border-box; color: var(--ink-muted); background: var(--surface-soft); cursor: default; font-size: 11px; text-align: center; }
</style>
