<template><view /></template>
<script setup>
import { onShow } from '@dcloudio/uni-app'
// 旧学生端地址统一进入家长查阅页。
onShow(() => uni.reLaunch({ url: '/subParent/children/index' }))
</script>
