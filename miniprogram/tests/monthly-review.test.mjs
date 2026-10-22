import test from 'node:test'
import assert from 'node:assert/strict'
import * as web from '../../frontend/src/utils/monthlyReview.js'
import * as mini from '../src/utils/monthlyReview.js'

for (const [name, review] of [['Web', web], ['小程序', mini]]) {
  const valid = { summary: '结'.repeat(50), problems: '问'.repeat(50), plan: '继续改进' }
  test(`${name}：总结和问题分别至少50字，计划只要求非空`, () => {
    assert.equal(review.completeReview(review.formatReview(valid)), true)
    for (const [key, label] of [['summary', '总结'], ['problems', '问题']]) {
      const short = review.formatReview({ ...valid, [key]: '字'.repeat(49) })
      assert.equal(review.completeReview(short), false)
      assert.equal(review.reviewError(short), `${label}至少填写50字（不含空白）`)
      assert.equal(review.completeReview(review.formatReview({ ...valid, [key]: '字'.repeat(51) })), true)
      assert.equal(review.completeReview(review.formatReview({ ...valid, [key]: '字'.repeat(49) + ' \n\t　' })), false)
    }
    assert.equal(review.reviewError(review.formatReview({ ...valid, plan: ' \n' })), '请填写计划')
  })
  test(`${name}：中文、英文、数字和补充平面字符按字符计数，空白不计数`, () => {
    assert.equal(review.reviewWordCount('中 a1𠮷 \n\t　'), 4)
    const values = { ...valid, summary: '𠮷'.repeat(49), problems: 'a'.repeat(50) }
    assert.equal(review.completeReview(review.formatReview(values)), false)
    values.summary += '𠮷'
    assert.equal(review.completeReview(review.formatReview(values)), true)
  })
  test(`${name}：历史短文本保留原文，编辑后需补齐`, () => {
    const old = '原有总结'
    assert.deepEqual(review.parseReview(old), { summary: old, problems: '', plan: '' })
    assert.equal(review.completeReview(old), false)
    assert.deepEqual(review.parseReview(review.formatReview(valid)), valid)
  })
}
