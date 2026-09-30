<template>
  <view class="review-form">
    <view v-for="field in reviewFields" :key="field.key" class="review-field">
      <text class="review-label">{{ field.label }} *</text>
      <textarea :value="values[field.key]" @input="change(field.key, $event.detail.value)" class="review-input" :maxlength="limit" :disabled="disabled" :cursor-spacing="24" :placeholder="field.placeholder" />
      <text class="review-count">{{ values[field.key].length }}/{{ limit }}</text>
    </view>
  </view>
</template>
<script setup>
import { computed } from 'vue'
import { reviewFields, parseReview, formatReview } from '../utils/monthlyReview'
const props = defineProps({ modelValue: { type: String, default: '' }, disabled: Boolean, limit: { type: Number, default: 2500 } })
const emit = defineEmits(['update:modelValue'])
const values = computed(() => parseReview(props.modelValue))
function change(key, value) { emit('update:modelValue', formatReview({ ...values.value, [key]: value })) }
</script>
<style scoped>
.review-field { margin-bottom: 22rpx; }
.review-label { display: block; font-size: 26rpx; margin-bottom: 10rpx; color: #182337; }
.review-input { box-sizing: border-box; width: 100%; height: 200rpx; padding: 16rpx; border: 1rpx solid #DFE5ED; border-radius: 8rpx; background: #F7F8FA; font-size: 26rpx; line-height: 1.7; }
.review-count { display: block; text-align: right; color: #617086; font-size: 22rpx; margin-top: 6rpx; }
</style>
