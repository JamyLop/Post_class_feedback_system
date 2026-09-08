<template>
  <view v-if="attachments?.length" class="checkin-photos">
    <image
      v-for="(item, idx) in displayList"
      :key="`${checkinId}-${item.index}`"
      :src="item.url"
      class="photo-thumb"
      mode="aspectFill"
      @error="onImageError(idx)"
      @click="preview(idx)"
    />
    <text v-if="failedCount && !displayList.length" class="photo-fallback">图片不可用</text>
  </view>
</template>

<script setup>
/**
 * 打卡附件缩略图：对齐 Web 端 SecureCheckinImage 的鉴权思路。
 * - OSS 预签名 https 直链可直接展示（无需鉴权）。
 * - 本地存储相对路径（/api/storage/files/...）<image> 无法携带 Authorization，
 *   必须经鉴权附件接口下载到临时文件再展示，否则 admin/德育主任等督查角色看不到照片。
 * 因此挂载即预加载全部附件，@error 仅作兜底重试。
 */
import { ref, watch } from 'vue'
import { getApiBase, getApiHost } from '../utils/request'

const props = defineProps({
  checkinId: { type: Number, required: true },
  attachments: { type: Array, default: () => [] },
})

const displayList = ref([])
const failedCount = ref(0)
const downloaded = ref({})

function resolveDirectUrl(att) {
  const raw = att?.url || ''
  if (!raw) return ''
  if (/^https?:\/\//i.test(raw)) return raw
  if (raw.startsWith('/')) return `${getApiHost()}${raw}`
  return raw
}

function isDirectHttps(att) {
  return /^https:\/\//i.test(att?.url || '')
}

function downloadViaAuth(attIndex) {
  const token = uni.getStorageSync('token') || ''
  return new Promise((resolve, reject) => {
    uni.downloadFile({
      url: `${getApiBase()}/student-cases/task-checkins/${props.checkinId}/attachments/${attIndex}`,
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300 && res.tempFilePath) {
          resolve(res.tempFilePath)
        } else {
          reject(new Error(`download ${res.statusCode}`))
        }
      },
      fail(err) {
        reject(err)
      },
    })
  })
}

async function reset() {
  failedCount.value = 0
  downloaded.value = {}
  const list = (props.attachments || []).map((att, index) => ({
    index,
    url: resolveDirectUrl(att),
    ready: isDirectHttps(att),
  })).filter(item => item.url || true)
  // 先整体赋值保证响应式，再对非直链附件逐个鉴权下载并替换为新数组触发更新
  displayList.value = list.filter(item => item.url)
  for (const item of list) {
    if (item.ready) continue
    try {
      const tmp = await downloadViaAuth(item.index)
      downloaded.value[item.index] = tmp
      displayList.value = displayList.value.map(row =>
        row.index === item.index ? { ...row, url: tmp, ready: true } : row,
      )
    } catch (_) {
      // 保留直链（后端新增 /storage/files 鉴权路由后，真机直链 401 仍会走 onImageError 兜底）
    }
  }
}

function preview(idx) {
  const urls = displayList.value.map(item => item.url).filter(Boolean)
  if (!urls.length) return
  uni.previewImage({ urls, current: urls[idx] || urls[0] })
}

async function onImageError(idx) {
  const item = displayList.value[idx]
  if (!item || downloaded.value[item.index]) {
    failedCount.value += 1
    return
  }
  // 兜底：直链失效（过期/本地存储 401）时经鉴权接口下载
  try {
    const tmp = await downloadViaAuth(item.index)
    downloaded.value[item.index] = tmp
    displayList.value = displayList.value.map(row =>
      row.index === item.index ? { ...row, url: tmp, ready: true } : row,
    )
  } catch (_) {
    failedCount.value += 1
  }
}

watch(() => props.attachments, reset, { immediate: true, deep: true })
watch(() => props.checkinId, reset)
</script>

<style scoped>
.checkin-photos { display: flex; flex-wrap: wrap; gap: 12rpx; margin-top: 10rpx; }
.photo-thumb { width: 140rpx; height: 140rpx; border-radius: 8rpx; background: #EDF1F7; }
.photo-fallback { font-size: 22rpx; color: #98A4B5; }
</style>
