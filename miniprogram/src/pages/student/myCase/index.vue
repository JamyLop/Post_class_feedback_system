<template><view class="redirect-page" /></template>
<script setup>
import { onShow } from '@dcloudio/uni-app'
// 旧学生端地址统一进入家长查阅页。
onShow(() => uni.reLaunch({ url: '/subParent/children/index' }))
</script>
<style scoped>
/* 为已注册的旧地址保留 WXSS 文件，兼容开发者工具的页面缓存。 */
.redirect-page { min-height: 100vh; }
</style>
