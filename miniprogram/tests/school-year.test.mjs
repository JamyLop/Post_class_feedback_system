import test from 'node:test'
import assert from 'node:assert/strict'
import { currentSchoolYear } from '../src/utils/schoolYear.js'

test('默认学年以8月为分界自动计算', () => {
  assert.equal(currentSchoolYear(new Date(2027, 6, 31)), '2026-2027')
  assert.equal(currentSchoolYear(new Date(2027, 7, 1)), '2027-2028')
})
