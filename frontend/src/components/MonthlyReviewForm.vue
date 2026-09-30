<template>
  <div class="review-form">
    <el-form-item v-for="field in reviewFields" :key="field.key" :label="field.label" required>
      <el-input :model-value="values[field.key]" @update:model-value="value => change(field.key, value)" type="textarea" :rows="3" :maxlength="limit" :disabled="disabled" :placeholder="field.placeholder" show-word-limit />
    </el-form-item>
  </div>
</template>
<script setup>
import { computed } from 'vue'
import { reviewFields, parseReview, formatReview } from '../utils/monthlyReview'
const props = defineProps({ modelValue: { type: String, default: '' }, disabled: Boolean, limit: { type: Number, default: 2500 } })
const emit = defineEmits(['update:modelValue'])
const values = computed(() => parseReview(props.modelValue))
function change(key, value) { emit('update:modelValue', formatReview({ ...values.value, [key]: value })) }
</script>
