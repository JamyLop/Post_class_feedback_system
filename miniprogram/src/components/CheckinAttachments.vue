<template>
  <view v-if="attachments?.length" class="checkin-photos">
    <view
      v-for="(item, idx) in displayList"
      :key="`${checkinId}-${item.index}`"
      class="photo-cell"
      @click="onTap(idx)"
    >
      <image
        v-if="!item.failed && item.url"
        :src="item.url"
        class="photo-thumb"
        mode="aspectFill"
        @error="onImageError(idx)"
        @load="onImageLoad(idx)"
      />
      <view v-else-if="item.failed" class="photo-thumb photo-failed">
        <text class="photo-failed-text">图片不可用\n点击重试</text>
      </view>
      <view v-else class="photo-thumb photo-loading">
        <text class="photo-loading-text">加载中...</text>
      </view>
      <view v-if="item.loading && item.url" class="photo-loading">
        <text class="photo-loading-text">加载中...</text>
      </view>
    </view>
  </view>
</template>

<script setup>
/**
 * 打卡附件缩略图：对齐 Web 端 SecureCheckinImage 的鉴权思路。
 * - OSS/MinIO 预签名 http(s) 直链可直接展示（无需鉴权）。
 * - 本地存储相对路径（/api/storage/files/...）<image> 无法携带 Authorization，
 *   必须经鉴权附件接口下载到临时文件再展示，否则 admin/德育主任等督查角色看不到照片。
 * 非直链附件展示“加载中...”占位，失败展示“图片不可用，点击重试”，点击可重试。
 */
import { ref, watch } from 'vue'
import { getApiBase, getApiHost } from '../utils/request'

const props = defineProps({
  checkinId: { type: Number, required: true },
  attachments: { type: Array, default: () => [] },
})

const displayList = ref([])
let runId = 0
const fetching = new Set()

function resolveDirectUrl(att) {
  const raw = att?.url || ''
  if (!raw) return ''
  if (/^https?:\/\//i.test(raw)) return raw
  if (raw.startsWith('/')) {
    const host = getApiHost()
    // H5 同源部署时 host 为空，保持相对路径即可
    return host ? `${host}${raw}` : raw
  }
  return raw
}

function isDirectUrl(att) {
  // 绝对 http(s) 直链（OSS/MinIO 预签名）直接展示；相对路径需鉴权下载
  return /^https?:\/\//i.test(att?.url || '')
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

function setItem(run, index, patch) {
  if (run !== runId) return
  displayList.value = displayList.value.map(row =>
    row.index === index ? { ...row, ...patch } : row,
  )
}

async function fetchOne(run, item) {
  if (fetching.has(item.index)) return
  fetching.add(item.index)
  setItem(run, item.index, { loading: true, failed: false })
  try {
    const tmp = await downloadViaAuth(item.index)
    setItem(run, item.index, { url: tmp, loading: false, failed: false })
  } catch (_) {
    // 真机 localhost 等网络问题或文件缺失：展示失败态，点击可重试
    setItem(run, item.index, { loading: false, failed: true })
  } finally {
    fetching.delete(item.index)
  }
}

async function reset() {
  const run = ++runId
  const list = (props.attachments || []).map((att, index) => {
    const direct = isDirectUrl(att)
    return {
      index,
      // 非直链（本地相对路径）先留空展示加载占位，避免 <image> 先请求无鉴权 URL 触发多余失败
      url: direct ? resolveDirectUrl(att) : '',
      loading: !direct,
      failed: false,
    }
  })
  displayList.value = list
  if (run !== runId) return
  for (const item of displayList.value) {
    if (run !== runId) return
    if (isDirectUrl((props.attachments || [])[item.index])) continue
    await fetchOne(run, item)
  }
}

function onTap(idx) {
  const item = displayList.value[idx]
  if (!item) return
  if (item.failed || (item.loading && !item.url)) {
    fetchOne(runId, item)
    return
  }
  preview(idx)
}

function preview(idx) {
  const urls = displayList.value.filter(item => !item.failed && item.url).map(item => item.url)
  if (!urls.length) return
  const current = displayList.value[idx]?.url
  uni.previewImage({ urls, current: urls.includes(current) ? current : urls[0] })
}

function onImageLoad(idx) {
  const item = displayList.value[idx]
  if (item) setItem(runId, item.index, { loading: false })
}

async function onImageError(idx) {
  const item = displayList.value[idx]
  if (!item) return
  // 直链失效（过期/本地存储 401）时经鉴权接口下载兜底
  await fetchOne(runId, item)
}

watch(() => props.attachments, reset, { immediate: true, deep: true })
watch(() => props.checkinId, reset)
</script>

<style scoped>
.checkin-photos { display: flex; flex-wrap: wrap; gap: 12rpx; margin-top: 10rpx; }
.photo-cell { position: relative; width: 140rpx; height: 140rpx; }
.photo-thumb { width: 140rpx; height: 140rpx; border-radius: 8rpx; background: #EDF1F7; }
.photo-loading { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: #EDF1F7; border-radius: 8rpx; }
.photo-loading-text { font-size: 22rpx; color: #98A4B5; }
.photo-failed { display: flex; align-items: center; justify-content: center; background: #F3F5F8; }
.photo-failed-text { font-size: 20rpx; color: #98A4B5; text-align: center; line-height: 1.5; }
</style>
