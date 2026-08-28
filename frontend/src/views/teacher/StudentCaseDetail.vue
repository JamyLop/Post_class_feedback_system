<template>
  <section class="page case-page">
    <el-skeleton v-if="loading" :rows="9" animated class="page-skeleton" />

    <template v-else-if="detail">
      <button class="back-link" type="button" @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon><span>{{ auth.role === 'parent' ? '返回孩子档案' : '返回学生档案' }}</span>
      </button>

      <header class="case-header">
        <div class="case-heading">
          <div class="title-line">
            <h1>{{ detail.student_name || `学生 #${detail.student_id}` }}</h1>
            <span class="title-suffix">学业发展总案</span>
          </div>
          <div class="case-meta">
            <span class="status-badge" :class="`is-${detail.status}`"><span class="status-dot"></span>{{ labels[detail.status] || detail.status }}</span>
            <span>{{ detail.class_name || `班级 #${detail.class_id}` }}</span>
            <span>第 {{ detail.version }} 版</span>
            <span>更新于 {{ formatDate(detail.updated_at) }}</span>
          </div>
        </div>
        <div class="case-actions">
          <el-button :loading="exporting" :disabled="editingOverview || editingPlan || !!editingTask" @click="handleExport"><el-icon><Document /></el-icon>导出 DOCX</el-button>
          <span v-if="detail" class="export-meta">V{{ detail.version }} · {{ labels[detail.status] || detail.status }}</span>
          <template v-if="detail.can_manage && !editingOverview && !editingPlan && !editingTask">
            <el-button v-if="detail.status === 'draft'" type="primary" :loading="submitting" @click="submitForConfirmation">提交待确认</el-button>
            <template v-if="detail.status === 'pending_confirmation'">
              <el-button :loading="submitting" @click="doTransition('draft', '退回草稿', '将总案退回草稿以继续完善，是否继续？', '退回草稿继续完善')">退回草稿</el-button>
              <el-button type="primary" :loading="submitting" @click="doTransition('executing', '确认进入执行', '确认后家长可见正式方案，且总览将锁定，是否继续？', '班主任确认进入执行')">确认进入执行</el-button>
            </template>
            <el-button v-if="detail.status === 'executing'" type="primary" :loading="submitting" @click="doTransition('pending_review', '发起阶段复盘', '进入复盘后将整理过程与督查记录，是否继续？', '发起阶段复盘')">发起阶段复盘</el-button>
            <template v-if="detail.status === 'pending_review'">
              <el-button type="primary" :loading="submitting" @click="doTransition('adjusted', '确认已调整', '确认调整将生成新版本并保留历史快照，是否继续？', '阶段复盘已调整')">确认已调整</el-button>
              <el-button :loading="submitting" @click="handleArchive">归档</el-button>
            </template>
            <template v-if="detail.status === 'adjusted'">
              <el-button type="primary" :loading="submitting" @click="doTransition('executing', '重新进入执行', '将已调整方案重新进入执行，是否继续？', '再次进入执行')">重新进入执行</el-button>
              <el-button :loading="submitting" @click="doTransition('pending_review', '再次发起复盘', '再次进入复盘以继续跟踪，是否继续？', '再次发起复盘')">再次发起复盘</el-button>
              <el-button :loading="submitting" @click="handleArchive">归档</el-button>
            </template>
          </template>
          <span v-else-if="detail.status === 'archived'" class="archived-tip">已归档</span>
        </div>
      </header>

      <div class="state-banner" :class="`is-${detail.status}`">
        <el-icon class="state-icon"><WarningFilled v-if="detail.status === 'draft'" /><CircleCheckFilled v-else /></el-icon>
        <div><strong>{{ stateTitle }}</strong><p>{{ stateDescription }}</p></div>
      </div>
      <div v-if="transitionError" class="transition-error"><el-icon><WarningFilled /></el-icon><span>{{ transitionError }}</span></div>

      <el-tabs v-model="active" class="case-tabs">
        <el-tab-pane label="总览" name="overview">
          <div v-if="editingOverview" class="editing-note overview-editing-note"><el-icon><EditPen /></el-icon><span>正在编辑总览，保存后将更新总体问题、升学目标和当前状态说明。</span></div>
          <div class="overview-toolbar" v-if="canEditOverview">
            <span class="overview-toolbar-tip">总览由班主任维护，正式执行前可直接完善</span>
            <template v-if="!editingOverview">
              <el-button plain @click="startOverviewEdit"><el-icon><EditPen /></el-icon>编辑总览</el-button>
            </template>
            <template v-else>
              <el-button :disabled="savingOverview" @click="cancelOverviewEdit">取消</el-button>
              <el-button type="primary" :loading="savingOverview" @click="saveOverview">保存总览</el-button>
            </template>
          </div>
          <div v-if="!editingOverview" class="overview-layout">
            <main class="reading-column">
              <article class="content-section">
                <div class="section-heading"><div><span class="section-marker"></span><h2>总体问题</h2></div><span>历史材料诊断摘要</span></div>
                <div v-if="problemSections.length" class="insight-list">
                  <div v-for="item in problemSections" :key="`${item.label}-${item.text}`" class="insight-row"><span class="subject-label">{{ item.label }}</span><p>{{ item.text }}</p></div>
                </div>
                <p v-else class="placeholder-copy">尚未填写总体问题。</p>
              </article>

              <article class="content-section">
                <div class="section-heading"><div><span class="section-marker"></span><h2>升学目标</h2></div><span>分阶段目标</span></div>
                <div v-if="targetSections.length" class="target-list">
                  <div v-for="item in targetSections" :key="`${item.label}-${item.text}`" class="target-row"><span>{{ item.label }}</span><p>{{ item.text }}</p></div>
                </div>
                <p v-else class="placeholder-copy">尚未填写升学目标。</p>
              </article>
            </main>

            <aside class="case-rail">
              <section class="rail-section"><span class="rail-label">当前状态</span><strong>{{ labels[detail.status] || detail.status }}</strong><p>{{ detail.current_summary || '尚未填写状态说明' }}</p><small v-if="detail.owner_teacher_id" class="rail-owner">负责人：班主任 #{{ detail.owner_teacher_id }}</small></section>
              <section class="rail-section compact">
                <div><span>学科方案</span><strong>{{ detail.subject_plans.length }}</strong></div>
                <div><span>阶段目标</span><strong>{{ detail.goals.length }}</strong></div>
                <div><span>执行任务</span><strong>{{ detail.tasks.length }}</strong></div>
                <div><span>督查记录</span><strong>{{ detail.reviews.length }}</strong></div>
              </section>
              <section v-if="auth.role !== 'parent'" class="rail-section source-note"><span class="rail-label">数据来源</span><p>历史 DOCX 试导入</p><small>解析内容尚未成为正式方案，需由班主任核对后提交确认。</small></section>
              <section v-if="detail.status === 'draft'" class="rail-section next-steps">
                <span class="rail-label">确认前检查</span>
                <ol><li><span>1</span>核对诊断与成绩信息</li><li><span>2</span>确认学科方案负责人</li><li><span>3</span>补充可执行目标与任务</li></ol>
              </section>
            </aside>
          </div>
          <el-form v-else label-position="top" class="overview-edit-form">
            <el-form-item label="总体问题"><el-input v-model="overviewForm.overall_problem" type="textarea" :autosize="{ minRows: 4, maxRows: 14 }" placeholder="完整填写学生总体问题诊断，例如各学科薄弱点、共性原因等" /></el-form-item>
            <el-form-item label="升学目标"><el-input v-model="overviewForm.admission_target" type="textarea" :autosize="{ minRows: 3, maxRows: 10 }" placeholder="填写升学目标，例如目标院校、目标分数及分阶段目标" /></el-form-item>
            <el-form-item label="当前状态说明"><el-input v-model="overviewForm.current_summary" type="textarea" :autosize="{ minRows: 2, maxRows: 8 }" placeholder="填写当前状态说明，例如：已完成首轮方案核对、待家长确认等" /></el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="学科方案" name="subjects">
          <div v-if="subjectOptions.length" class="subject-workspace">
            <nav class="subject-nav" aria-label="选择学科">
              <div class="subject-nav-heading"><strong>全部科目</strong><span>{{ subjectOptions.length }} 科</span></div>
              <button
                v-for="subject in subjectOptions"
                :key="subject"
                class="subject-nav-item"
                :class="{ 'is-active': selectedSubject === subject }"
                type="button"
                :disabled="(editingPlan || editingTask || editingOverview) && selectedSubject !== subject"
                :aria-current="selectedSubject === subject ? 'page' : undefined"
                @click="selectSubject(subject)"
              >
                <span class="subject-avatar">{{ subject.slice(0, 1) }}</span>
                <span><strong>{{ subject }}</strong><small>{{ subjectStatusText(subject) }}</small></span>
                <span class="subject-task-count">{{ tasksFor(subject).length }}</span>
                <el-icon><ArrowRight /></el-icon>
              </button>
              <el-dropdown v-if="availableSubjects.length" class="subject-add" trigger="click" :disabled="editingPlan || editingTask || editingOverview" @command="addSubject">
                <el-button link type="primary"><el-icon><Plus /></el-icon>添加学科</el-button>
                <template #dropdown><el-dropdown-menu><el-dropdown-item v-for="subject in availableSubjects" :key="subject" :command="subject">{{ subject }}</el-dropdown-item></el-dropdown-menu></template>
              </el-dropdown>
            </nav>

            <main class="subject-detail">
              <header class="subject-detail-header">
                <div><span class="subject-chip">{{ selectedSubject === '德育' ? '德育' : selectedSubject }}</span><h2>{{ selectedSubject === '德育' ? '德育行为记录' : selectedSubject + '学业提升方案' }}</h2></div>
                <div class="subject-header-actions">
                  <div class="subject-counts"><span>{{ tasksFor(selectedSubject).length }} 项任务</span><span>{{ checkinsFor(selectedSubject).length }} 条执行记录</span></div>
                  <el-button v-if="canEditPlan && !editingPlan && !editingTask" plain @click="startPlanEdit"><el-icon><EditPen /></el-icon>编辑方案</el-button>
                  <template v-else-if="editingPlan">
                    <el-button :disabled="savingPlan" @click="cancelPlanEdit">取消编辑</el-button>
                    <el-button type="primary" :loading="savingPlan" @click="savePlan">保存方案</el-button>
                  </template>
                </div>
              </header>

              <div v-if="editingPlan" class="editing-note"><el-icon><EditPen /></el-icon><span>正在编辑 {{ selectedSubject }}方案，所有字段将按原文完整保存。</span></div>

              <section class="subject-section">
                <div class="subject-section-heading"><div><el-icon><Search /></el-icon><h3>{{ selectedSubject === '德育' ? '行为表现' : '问题' }}</h3></div><span>{{ selectedSubject === '德育' ? '记录日常行为与关键表现' : '明确当前差距与主要原因' }}</span></div>
                <el-form v-if="editingPlan" label-position="top" class="subject-edit-form">
                  <el-form-item :label="selectedSubject === '德育' ? '行为表现' : '问题定位'"><el-input v-model="planForm.problem_location" type="textarea" :autosize="{ minRows: 3, maxRows: 14 }" :placeholder="selectedSubject === '德育' ? '记录课堂、作业、纪律、品行等日常行为表现' : '完整填写该学科的问题定位'" /></el-form-item>
                  <el-form-item :label="selectedSubject === '德育' ? '原因/背景' : '原因剖析'"><el-input v-model="planForm.cause_analysis" type="textarea" :autosize="{ minRows: 3, maxRows: 14 }" :placeholder="selectedSubject === '德育' ? '分析行为背后的原因及需要关注的点' : '完整填写问题产生的原因'" /></el-form-item>
                </el-form>
                <dl v-else class="subject-fields">
                  <div><dt>{{ selectedSubject === '德育' ? '行为表现' : '问题定位' }}</dt><dd>{{ (selectedPlan?.problem_location || subjectProblemText) || (selectedSubject === '德育' ? '该生德育尚未记录。' : '该学科尚未完成问题定位。') }}</dd></div>
                  <div><dt>{{ selectedSubject === '德育' ? '原因/背景' : '原因剖析' }}</dt><dd>{{ (selectedPlan?.cause_analysis || '') || (selectedSubject === '德育' ? '尚未补充行为背景分析。' : '尚未补充原因分析，需由对应学科教师确认。') }}</dd></div>
                </dl>
              </section>

              <section class="subject-section">
                <div class="subject-section-heading"><div><el-icon><Calendar /></el-icon><h3>{{ selectedSubject === '德育' ? '养成计划' : '计划' }}</h3></div><span>{{ selectedSubject === '德育' ? '目标与日常优化安排' : '目标要求与具体行动安排' }}</span></div>
                <el-form v-if="editingPlan" label-position="top" class="subject-edit-form plan-edit-form">
                  <el-form-item :label="selectedSubject === '德育' ? '养成目标' : '奋斗目标'"><el-input v-model="planForm.struggle_goal" type="textarea" :autosize="{ minRows: 3, maxRows: 14 }" :placeholder="selectedSubject === '德育' ? '填写品行、习惯等阶段性养成目标' : '完整填写短期、中期和高考目标'" /></el-form-item>
                  <el-form-item :label="selectedSubject === '德育' ? '规范要求' : '高考要求'"><el-input v-model="planForm.gaokao_requirement" type="textarea" :autosize="{ minRows: 3, maxRows: 14 }" :placeholder="selectedSubject === '德育' ? '填写学校/班级对行为规范的要求' : '完整填写该学科的高考要求'" /></el-form-item>
                  <el-form-item :label="selectedSubject === '德育' ? '日常优化措施' : '具体强化'"><el-input v-model="planForm.reinforcement" type="textarea" :autosize="{ minRows: 3, maxRows: 14 }" :placeholder="selectedSubject === '德育' ? '记录家校协同、谈话、激励等优化措施及过程' : '完整填写具体强化措施'" /></el-form-item>
                </el-form>
                <dl v-else class="subject-fields plan-fields">
                  <div><dt>{{ selectedSubject === '德育' ? '养成目标' : '奋斗目标' }}</dt><dd>{{ (selectedPlan?.struggle_goal || subjectTargetText) || (selectedSubject === '德育' ? '尚未建立养成目标。' : '尚未建立该学科奋斗目标。') }}</dd></div>
                  <div><dt>{{ selectedSubject === '德育' ? '规范要求' : '高考要求' }}</dt><dd>{{ (selectedPlan?.gaokao_requirement || '') || (selectedSubject === '德育' ? '尚未补充规范要求。' : '尚未补充高考要求。') }}</dd></div>
                  <div><dt>{{ selectedSubject === '德育' ? '日常优化' : '具体强化' }}</dt><dd>{{ (selectedPlan?.reinforcement || '') || (selectedSubject === '德育' ? '尚未记录日常优化措施。' : '尚未制定具体强化方案。') }}</dd></div>
                </dl>
                <div class="task-list-heading">
                  <div><strong>任务安排</strong><span>{{ tasksFor(selectedSubject).length }} 项</span></div>
                  <el-button v-if="canEditTasks && !editingTask" link type="primary" @click="startTaskEdit()"><el-icon><Plus /></el-icon>新增任务</el-button>
                </div>
                <el-form v-if="editingTask" label-position="top" class="task-edit-form">
                  <el-form-item label="任务名称"><el-input v-model="taskForm.title" placeholder="填写完整任务名称" /></el-form-item>
                  <el-form-item label="任务内容"><el-input v-model="taskForm.description" type="textarea" :autosize="{ minRows: 4, maxRows: 16 }" placeholder="填写完整任务内容和执行要求" /></el-form-item>
                  <div class="task-form-grid">
                    <el-form-item label="任务周期"><el-select v-model="taskForm.cadence"><el-option label="日计划" value="daily" /><el-option label="周计划" value="weekly" /><el-option label="月计划" value="monthly" /></el-select></el-form-item>
                    <el-form-item label="开始日期"><el-date-picker v-model="taskForm.starts_on" type="date" value-format="YYYY-MM-DD" placeholder="选择开始日期" /></el-form-item>
                    <el-form-item label="截止日期"><el-date-picker v-model="taskForm.due_on" type="date" value-format="YYYY-MM-DD" placeholder="选择截止日期" /></el-form-item>
                  </div>
                  <div class="task-form-actions"><el-button :disabled="savingTask" @click="cancelTaskEdit">取消</el-button><el-button type="primary" :loading="savingTask" @click="saveTask">保存任务</el-button></div>
                </el-form>
                <div v-if="tasksFor(selectedSubject).length" class="task-list">
                  <article v-for="task in tasksFor(selectedSubject)" :key="task.id" class="task-row">
                    <div><strong>{{ task.title }}</strong><p>{{ task.description || '暂无补充说明' }}</p></div>
                    <div class="task-side"><div class="task-meta"><span>{{ cadenceLabel(task.cadence) }}</span><span>{{ formatShortDate(task.starts_on) }} 至 {{ formatShortDate(task.due_on) }}</span><span>{{ taskStatusLabel(task.status) }}</span></div><el-button v-if="canEditTasks && !editingTask" link @click="startTaskEdit(task)">编辑任务</el-button></div>
                  </article>
                </div>
                <div v-else class="inline-empty"><p>该学科尚未安排日、周或月任务。</p></div>
              </section>

              <section class="subject-section">
                <div class="subject-section-heading"><div><el-icon><CircleCheck /></el-icon><h3>执行记录</h3></div><span>班主任核实并记录任务完成情况</span></div>
                <el-form v-if="detail.can_manage && tasksFor(selectedSubject).length" label-position="top" class="checkin-form">
                  <div class="checkin-form-grid">
                    <el-form-item label="对应任务"><el-select v-model="checkinForm.task_id" placeholder="选择要记录的任务"><el-option v-for="task in tasksFor(selectedSubject)" :key="task.id" :label="task.title" :value="task.id" /></el-select></el-form-item>
                    <el-form-item label="完成度"><el-input-number v-model="checkinForm.completion_rate" :min="0" :max="100" :step="10" /><span class="percent-suffix">%</span></el-form-item>
                  </div>
                  <el-form-item label="班主任记录"><el-input v-model="checkinForm.self_check" type="textarea" :autosize="{ minRows: 3, maxRows: 10 }" placeholder="完整记录学生实际执行情况、发现的问题和后续要求" /></el-form-item>
                  <div class="task-form-actions"><el-button type="primary" :loading="savingCheckin" @click="saveCheckin">保存执行记录</el-button></div>
                </el-form>
                <div v-if="checkinsFor(selectedSubject).length" class="checkin-list">
                  <article v-for="checkin in checkinsFor(selectedSubject)" :key="checkin.id" class="checkin-row">
                    <div class="completion-rate"><strong>{{ checkin.completion_rate }}%</strong><span>完成度</span></div>
                    <div><strong>{{ taskTitle(checkin.task_id) }}</strong><p>{{ checkin.self_check || '班主任未填写补充说明' }}</p><time>{{ formatDateTime(checkin.checked_in_at) }}</time></div>
                  </article>
                </div>
                <div v-else class="inline-empty"><p>该学科尚无执行记录，班主任核实任务执行情况后在此登记。</p></div>
              </section>
            </main>
          </div>
          <div v-else class="empty-panel subject-empty"><h3>尚未建立学科方案</h3><p>班主任可以直接选择学科，从空白方案开始完整填写。</p><div class="subject-create-actions"><el-button v-for="subject in subjectOrder" :key="subject" type="primary" plain @click="addSubject(subject)">新建{{ subject }}方案</el-button></div></div>
        </el-tab-pane>
        <el-tab-pane label="督查复盘" name="reviews">
          <div v-if="canCreateReview" class="review-form-card">
            <div class="review-form-header"><strong>新增督查复盘</strong><span>{{ reviewRoleTip }}</span></div>
            <el-form label-position="top" class="review-form">
              <div class="review-form-grid">
                <el-form-item label="督查层级">
                  <el-select v-model="reviewForm.review_level">
                    <el-option v-if="auth.role === 'admin'" label="校级督查" value="school" />
                    <el-option v-if="auth.role === 'admin'" label="校长督察" value="principal" />
                    <el-option v-if="detail.can_manage" label="班主任督查" value="head_teacher" />
                    <el-option v-if="detail.can_manage" label="学科督查" value="subject" />
                  </el-select>
                </el-form-item>
                <el-form-item label="关联学科"><el-select v-model="reviewForm.subject" clearable placeholder="可选"><el-option v-for="s in subjectOrder" :key="s" :label="s" :value="s" /></el-select></el-form-item>
                <el-form-item label="整改截止日期"><el-date-picker v-model="reviewForm.correction_due_on" type="date" value-format="YYYY-MM-DD" placeholder="选择截止日期" /></el-form-item>
              </div>
              <el-form-item label="发现问题"><el-input v-model="reviewForm.problem" type="textarea" :autosize="{ minRows: 3, maxRows: 10 }" placeholder="填写督查发现的主要问题" /></el-form-item>
              <el-form-item label="整改要求"><el-input v-model="reviewForm.corrective_action" type="textarea" :autosize="{ minRows: 3, maxRows: 10 }" placeholder="填写整改要求与具体措施" /></el-form-item>
              <el-form-item label="复查结果（可选）"><el-input v-model="reviewForm.recheck_result" type="textarea" :autosize="{ minRows: 2, maxRows: 8 }" placeholder="复查时填写结果，初次督查可留空" /></el-form-item>
              <div class="review-form-actions"><el-button type="primary" :loading="savingReview" @click="saveReview">提交督查记录</el-button></div>
            </el-form>
          </div>
          <div v-else-if="auth.role === 'parent'" class="review-readonly-tip"><el-icon><WarningFilled /></el-icon><span>家长仅可查看督查结论，督查由班主任与校级管理员记录。</span></div>
          <el-timeline v-if="detail.reviews.length" class="review-timeline">
            <el-timeline-item v-for="review in detail.reviews" :key="review.id" :timestamp="formatDateTime(review.reviewed_at)">
              <div class="review-item">
                <div class="review-item-head"><span class="review-level" :class="`is-${review.review_level}`">{{ reviewLevelLabel(review.review_level) }}</span><span v-if="review.subject" class="review-subject">{{ review.subject }}</span><span v-if="review.correction_due_on" class="review-due">整改截止 {{ review.correction_due_on }}</span></div>
                <p class="review-problem">{{ review.problem || '未填写具体问题' }}</p>
                <p v-if="review.corrective_action" class="review-action">整改：{{ review.corrective_action }}</p>
                <p v-if="review.recheck_result" class="review-recheck">复查：{{ review.recheck_result }}</p>
              </div>
            </el-timeline-item>
          </el-timeline>
          <div v-else class="empty-panel"><h3>暂无督查记录</h3><p>方案进入执行阶段后，班主任记录过程，管理员提交校级督查。</p></div>
        </el-tab-pane>
        <el-tab-pane label="历史版本" name="versions"><div class="empty-panel"><h3>当前为第 {{ detail.version }} 版</h3><p>正式调整后，旧版本将在这里保留并支持对比。</p></div></el-tab-pane>
      </el-tabs>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowRight, Calendar, CircleCheck, CircleCheckFilled, Document, EditPen, Plus, Search, WarningFilled } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'
import { checkinCaseTask, createCaseReview, createCaseTask, exportStudentCase, getStudentCase, transitionStudentCase, updateCaseTask, updateStudentCase, upsertSubjectPlan } from '../../api/studentCases'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const auth = useAuthStore()
const loading = ref(false)
const submitting = ref(false)
const editingPlan = ref(false)
const savingPlan = ref(false)
const editingTask = ref(null)
const savingTask = ref(false)
const savingCheckin = ref(false)
const editingOverview = ref(false)
const savingOverview = ref(false)
const savingReview = ref(false)
const exporting = ref(false)
const detail = ref(null)
const active = ref('overview')
const selectedSubject = ref('')
const manualSubjects = ref([])
const planForm = ref(createEmptyPlanForm())
const taskForm = ref(createEmptyTaskForm())
const overviewForm = ref(createEmptyOverviewForm())
const checkinForm = ref({ task_id: null, completion_rate: 0, self_check: '' })
const reviewForm = ref(createEmptyReviewForm())
const labels = { draft: '草稿', pending_confirmation: '待确认', executing: '执行中', pending_review: '待复盘', adjusted: '已调整', archived: '已归档' }
const subjectOrder = ['语文', '数学', '英语', '物理', '化学', '生物', '政治', '历史', '地理', '德育']
const transitionError = ref('')
const statusCopy = {
  draft: { title: '历史材料已导入，等待教师核对', desc: '请由班主任核对总体问题、升学目标和学科方案，确认无误后提交待确认。' },
  pending_confirmation: { title: '等待班主任最终确认', desc: '已提交待确认，请复核后确认进入执行；确认后家长可见正式方案，总览将锁定。' },
  executing: { title: '方案正在执行中', desc: '家长已可见当前版本。请通过任务与执行记录跟踪进展，必要时发起阶段复盘。' },
  pending_review: { title: '已进入阶段复盘', desc: '请完成督查复盘记录，确认调整后将生成新版本，归档则结束本周期。' },
  adjusted: { title: '复盘已调整（已生成新版本）', desc: '已按复盘结论调整并保留历史版本。可重新进入执行或再次复盘。' },
  archived: { title: '已归档', desc: '本档案已归档，内容只读保留，历史版本仍可查看。' },
}
const stateTitle = computed(() => statusCopy[detail.value?.status]?.title || `方案当前处于${labels[detail.value?.status] || '处理中'}状态`)
const stateDescription = computed(() => statusCopy[detail.value?.status]?.desc || '所有后续调整都会保留历史版本，家长始终看到有版本依据的正式内容。')

function splitStructuredText(value, fallbackLabel) {
  if (!value) return []
  return value.split(/[；;]/).map((part) => part.trim()).filter(Boolean).flatMap((part) => {
    const match = part.match(/^([^：:]{1,14})[：:]\s*(.+)$/)
    if (!match) return [{ label: fallbackLabel, text: part }]
    const rawLabel = match[1].trim().replace(/^\d+[.、]\s*/, '')
    const labels = rawLabel.split(/[\/／]/).map((label) => label.trim()).filter(Boolean)
    // 历史文档可能把多门学科写在同一项中；展示时拆开标签，但完整保留共同的原始描述。
    return labels.map((label) => ({ label, text: match[2].trim() }))
  })
}

const problemSections = computed(() => splitStructuredText(detail.value?.overall_problem, '综合'))
const targetSections = computed(() => splitStructuredText(detail.value?.admission_target, '总体目标'))
const subjectOptions = computed(() => {
  const found = new Set()
  problemSections.value.forEach((item) => { if (subjectOrder.includes(item.label)) found.add(item.label) })
  detail.value?.subject_plans?.forEach((item) => { if (item.subject) found.add(item.subject) })
  detail.value?.goals?.forEach((item) => { if (item.subject) found.add(item.subject) })
  detail.value?.tasks?.forEach((item) => { if (item.subject) found.add(item.subject) })
  manualSubjects.value.forEach((item) => found.add(item))
  return [...found].sort((a, b) => {
    const aIndex = subjectOrder.indexOf(a)
    const bIndex = subjectOrder.indexOf(b)
    if (aIndex === -1 || bIndex === -1) return a.localeCompare(b, 'zh-CN')
    return aIndex - bIndex
  })
})
const selectedPlan = computed(() => detail.value?.subject_plans?.find((item) => item.subject === selectedSubject.value))
const availableSubjects = computed(() => subjectOrder.filter((item) => !subjectOptions.value.includes(item)))
const canEditPlan = computed(() => detail.value?.can_manage && ['draft', 'pending_confirmation', 'adjusted'].includes(detail.value?.status) && !editingOverview.value && !editingTask.value)
const canEditOverview = computed(() => detail.value?.can_manage && ['draft', 'pending_confirmation'].includes(detail.value?.status) && !editingPlan.value && !editingTask.value)
const canEditTasks = computed(() => detail.value?.can_manage && detail.value?.status !== 'archived' && !editingPlan.value && !editingOverview.value)
const canCreateReview = computed(() => {
  if (!detail.value) return false
  if (auth.role === 'admin') return true
  return !!detail.value.can_manage
})
const reviewRoleTip = computed(() => {
  if (auth.role === 'admin') return '管理员提交校级/校长督察，班主任提交班主任/学科层级'
  if (detail.value?.can_manage) return '班主任可提交班主任/学科层级督查'
  return ''
})
// 学科方案缺失时展示总案原文作为参考，不抽取、不概括，避免导入内容被压缩。
const subjectProblemText = computed(() => detail.value?.overall_problem || '')
const subjectTargetText = computed(() => detail.value?.admission_target || '')

function createEmptyPlanForm() {
  return { problem_location: '', cause_analysis: '', struggle_goal: '', gaokao_requirement: '', reinforcement: '' }
}

function createEmptyTaskForm() {
  const today = new Date().toISOString().slice(0, 10)
  return { title: '', description: '', cadence: 'daily', starts_on: today, due_on: today }
}

function createEmptyOverviewForm() {
  return { overall_problem: '', admission_target: '', current_summary: '' }
}

function createEmptyReviewForm() {
  return { review_level: 'head_teacher', subject: '', problem: '', corrective_action: '', correction_due_on: '', recheck_result: '' }
}

function reviewLevelLabel(level) {
  return { school: '校级督查', principal: '校长督察', head_teacher: '班主任督查', subject: '学科督查' }[level] || level
}

async function saveReview() {
  if (!detail.value) return
  if (!reviewForm.value.problem.trim() && !reviewForm.value.corrective_action.trim()) {
    ElMessage.warning('请填写发现问题或整改要求')
    return
  }
  if (auth.role !== 'admin' && !detail.value.can_manage) {
    ElMessage.error('无权提交督查')
    return
  }
  savingReview.value = true
  try {
    const payload = {
      review_level: reviewForm.value.review_level,
      subject: reviewForm.value.subject || '',
      problem: reviewForm.value.problem,
      corrective_action: reviewForm.value.corrective_action,
      correction_due_on: reviewForm.value.correction_due_on || null,
      recheck_result: reviewForm.value.recheck_result || '',
    }
    const saved = await createCaseReview(detail.value.id, payload)
    detail.value.reviews.unshift(saved)
    reviewForm.value = createEmptyReviewForm()
    if (auth.role === 'admin') reviewForm.value.review_level = 'school'
    ElMessage.success('督查记录已提交')
  } finally {
    savingReview.value = false
  }
}

function startOverviewEdit() {
  if (!detail.value) return
  overviewForm.value = {
    overall_problem: detail.value.overall_problem || '',
    admission_target: detail.value.admission_target || '',
    current_summary: detail.value.current_summary || '',
  }
  editingOverview.value = true
}

function cancelOverviewEdit() {
  editingOverview.value = false
  overviewForm.value = createEmptyOverviewForm()
}

async function saveOverview() {
  if (!detail.value) return
  savingOverview.value = true
  try {
    const saved = await updateStudentCase(detail.value.id, {
      overall_problem: overviewForm.value.overall_problem,
      admission_target: overviewForm.value.admission_target,
      current_summary: overviewForm.value.current_summary,
    })
    detail.value.overall_problem = saved.overall_problem
    detail.value.admission_target = saved.admission_target
    detail.value.current_summary = saved.current_summary
    detail.value.updated_at = saved.updated_at
    editingOverview.value = false
    ElMessage.success('总览已保存')
  } finally {
    savingOverview.value = false
  }
}

function selectSubject(subject) {
  if ((editingPlan.value || editingTask.value || editingOverview.value) && subject !== selectedSubject.value) return
  selectedSubject.value = subject
  checkinForm.value.task_id = tasksFor(subject)[0]?.id || null
}

function addSubject(subject) {
  if (!manualSubjects.value.includes(subject)) manualSubjects.value.push(subject)
  selectedSubject.value = subject
  startPlanEdit()
}

function startPlanEdit() {
  const plan = selectedPlan.value
  planForm.value = plan ? {
    problem_location: plan.problem_location || '',
    cause_analysis: plan.cause_analysis || '',
    struggle_goal: plan.struggle_goal || '',
    gaokao_requirement: plan.gaokao_requirement || '',
    reinforcement: plan.reinforcement || '',
  } : createEmptyPlanForm()
  editingPlan.value = true
}

function cancelPlanEdit() {
  editingPlan.value = false
  planForm.value = createEmptyPlanForm()
}

async function savePlan() {
  if (!detail.value || !selectedSubject.value) return
  const teacherId = selectedPlan.value?.teacher_id || auth.user?.id
  if (!teacherId) {
    ElMessage.error('无法识别当前教师，请重新登录后再保存')
    return
  }
  savingPlan.value = true
  try {
    const saved = await upsertSubjectPlan(detail.value.id, selectedSubject.value, {
      subject: selectedSubject.value,
      teacher_id: teacherId,
      ...planForm.value,
    })
    const index = detail.value.subject_plans.findIndex((item) => item.subject === selectedSubject.value)
    if (index >= 0) detail.value.subject_plans.splice(index, 1, saved)
    else detail.value.subject_plans.push(saved)
    editingPlan.value = false
    planForm.value = createEmptyPlanForm()
    ElMessage.success(`${selectedSubject.value}方案已保存`)
  } finally {
    savingPlan.value = false
  }
}

function startTaskEdit(task = null) {
  editingTask.value = task?.id || 'new'
  taskForm.value = task ? {
    title: task.title || '',
    description: task.description || '',
    cadence: task.cadence || 'daily',
    starts_on: task.starts_on || '',
    due_on: task.due_on || '',
  } : createEmptyTaskForm()
}

function cancelTaskEdit() {
  editingTask.value = null
  taskForm.value = createEmptyTaskForm()
}

async function saveTask() {
  if (!taskForm.value.title.trim()) {
    ElMessage.warning('请填写任务名称')
    return
  }
  if (!taskForm.value.starts_on || !taskForm.value.due_on) {
    ElMessage.warning('请选择任务开始和截止日期')
    return
  }
  if (taskForm.value.due_on < taskForm.value.starts_on) {
    ElMessage.warning('截止日期不能早于开始日期')
    return
  }
  savingTask.value = true
  try {
    const payload = { subject: selectedSubject.value, ...taskForm.value, title: taskForm.value.title.trim() }
    const saved = editingTask.value === 'new'
      ? await createCaseTask(detail.value.id, payload)
      : await updateCaseTask(detail.value.id, editingTask.value, payload)
    const index = detail.value.tasks.findIndex((item) => item.id === saved.id)
    if (index >= 0) detail.value.tasks.splice(index, 1, saved)
    else detail.value.tasks.push(saved)
    cancelTaskEdit()
    ElMessage.success('任务已保存')
  } finally {
    savingTask.value = false
  }
}

function tasksFor(subject) {
  return detail.value?.tasks?.filter((item) => item.subject === subject) || []
}

function checkinsFor(subject) {
  const taskIds = new Set(tasksFor(subject).map((item) => item.id))
  return detail.value?.task_checkins?.filter((item) => taskIds.has(item.task_id)) || []
}

async function saveCheckin() {
  if (!checkinForm.value.task_id) {
    ElMessage.warning('请选择对应任务')
    return
  }
  savingCheckin.value = true
  try {
    const saved = await checkinCaseTask(checkinForm.value.task_id, {
      completion_rate: checkinForm.value.completion_rate,
      self_check: checkinForm.value.self_check,
    })
    detail.value.task_checkins.unshift(saved)
    const task = detail.value.tasks.find((item) => item.id === saved.task_id)
    if (task) task.status = saved.completion_rate === 100 ? 'completed' : saved.completion_rate > 0 ? 'in_progress' : 'pending'
    checkinForm.value = { task_id: null, completion_rate: 0, self_check: '' }
    ElMessage.success('执行记录已保存')
  } finally {
    savingCheckin.value = false
  }
}

function subjectStatusText(subject) {
  if (detail.value?.subject_plans?.some((item) => item.subject === subject)) return '方案已录入'
  if (tasksFor(subject).length) return '已有任务'
  return '待完善'
}

function taskTitle(taskId) {
  return detail.value?.tasks?.find((item) => item.id === taskId)?.title || '任务记录'
}

function cadenceLabel(value) {
  return { daily: '日计划', weekly: '周计划', monthly: '月计划' }[value] || value
}

function taskStatusLabel(value) {
  return { pending: '待执行', in_progress: '执行中', completed: '已完成', overdue: '已逾期' }[value] || value
}

function formatShortDate(value) {
  return value ? value.slice(5).replace('-', '/') : '未定'
}

function formatDate(value) {
  if (!value) return '暂无记录'
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value))
}
function formatDateTime(value) {
  if (!value) return '暂无时间'
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}
async function load() {
  loading.value = true
  try {
    detail.value = await getStudentCase(route.params.id)
    if (!subjectOptions.value.includes(selectedSubject.value)) selectedSubject.value = subjectOptions.value[0] || ''
    const firstTask = tasksFor(selectedSubject.value)[0]
    checkinForm.value.task_id = firstTask?.id || null
    if (auth.role === 'admin') reviewForm.value.review_level = 'school'
    else if (detail.value?.can_manage) reviewForm.value.review_level = 'head_teacher'
  } finally {
    loading.value = false
  }
}
async function submitForConfirmation() {
  await ElMessageBox.confirm('提交后总案将进入待确认状态，是否继续？', '提交教师确认', { confirmButtonText: '提交确认', cancelButtonText: '继续检查', type: 'warning' })
  submitting.value = true
  transitionError.value = ''
  try { await transitionStudentCase(detail.value.id, { target_status: 'pending_confirmation', reason: '历史材料核对完成' }); ElMessage.success('已提交确认'); await load() } catch (e) { transitionError.value = e?.response?.data?.detail || e.message || '流转失败' } finally { submitting.value = false }
}

async function doTransition(targetStatus, title, message, reason) {
  await ElMessageBox.confirm(message, title, { confirmButtonText: '确认', cancelButtonText: '取消', type: 'warning' })
  submitting.value = true
  transitionError.value = ''
  try {
    await transitionStudentCase(detail.value.id, { target_status: targetStatus, reason })
    ElMessage.success(`已切换为${labels[targetStatus] || targetStatus}`)
    await load()
  } catch (e) {
    transitionError.value = e?.response?.data?.detail || e.message || '流转失败'
  } finally {
    submitting.value = false
  }
}

async function handleExport() {
  if (!detail.value) return
  exporting.value = true
  try {
    const blob = await exportStudentCase(detail.value.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${detail.value.student_name || '学生'}_一生一案_V${detail.value.version}.docx`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    ElMessage.success(`已导出 V${detail.value.version} 版本`)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '导出失败，请重试')
  } finally {
    exporting.value = false
  }
}

async function handleArchive() {
  const { value } = await ElMessageBox.prompt('请输入归档原因（将保留历史版本）', '归档确认', { confirmButtonText: '确认归档', cancelButtonText: '取消', inputPlaceholder: '例如：本周期已结束，归档留存' })
  if (!value || !String(value).trim()) { ElMessage.warning('请填写归档原因'); return }
  submitting.value = true
  transitionError.value = ''
  try {
    await transitionStudentCase(detail.value.id, { target_status: 'archived', reason: String(value).trim() })
    ElMessage.success('已归档')
    await load()
  } catch (e) {
    transitionError.value = e?.response?.data?.detail || e.message || '归档失败'
  } finally { submitting.value = false }
}
onMounted(load)
</script>

<style scoped>
.case-page { min-height: 100%; }.page-skeleton { padding-top: 42px; }
.back-link { display: inline-flex; align-items: center; gap: 6px; margin: 2px 0 18px; padding: 6px 10px 6px 8px; color: var(--ink-secondary); background: var(--surface); border: 1px solid var(--line); border-radius: 999px; cursor: pointer; font-size: 13px; box-shadow: var(--shadow-soft); transition: border-color .18s, color .18s, background .18s; }.back-link:hover { color: var(--brand-strong); border-color: var(--line-strong); background: var(--surface); }
.case-header { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 20px 24px; align-items: start; padding: 22px 24px 20px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg) var(--radius-lg) 0 0; box-shadow: var(--shadow-soft); }.case-heading { min-width: 0; }.title-line { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }.title-line h1 { margin: 0; color: var(--ink); font-size: 30px; line-height: 1.2; letter-spacing: -.03em; text-wrap: balance; }.title-suffix { color: var(--ink-muted); font-size: 14px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; }
.case-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 14px; margin-top: 12px; color: var(--ink-muted); font-size: 12.5px; }.status-badge { display: inline-flex; align-items: center; gap: 7px; padding: 5px 10px; color: #8a5611; background: var(--warning-soft); border: 1px solid color-mix(in oklch, var(--warning) 14%, transparent); border-radius: 999px; font-weight: 700; font-size: 12px; letter-spacing: .02em; }.status-badge.is-executing, .status-badge.is-adjusted, .status-badge.is-archived { color: #1a6b44; background: oklch(0.96 0.03 155); border-color: color-mix(in oklch, var(--success) 14%, transparent); }.status-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; box-shadow: 0 0 0 3px color-mix(in oklch, currentColor 16%, transparent); }
.case-actions { display: flex; gap: 10px; justify-content: flex-end; align-items: center; flex-wrap: wrap; align-self: start; min-width: 280px; }.case-actions :deep(.el-button) { min-height: 36px; border-radius: 10px; font-weight: 600; }.case-actions :deep(.el-button.is-disabled) { opacity: .6; }.export-meta { padding: 6px 10px; color: var(--ink-muted); background: var(--surface-soft); border: 1px solid var(--line); border-radius: 999px; font-size: 11px; font-weight: 600; }.archived-tip { padding: 7px 12px; color: var(--ink-muted); background: var(--surface-soft); border: 1px solid var(--line); border-radius: 999px; font-size: 12px; font-weight: 600; }
.state-banner { display: flex; align-items: flex-start; gap: 14px; margin: 0; padding: 14px 24px 16px; color: #7a4d12; background: linear-gradient(180deg, color-mix(in oklch, var(--warning-soft) 88%, white), var(--warning-soft)); border: 1px solid color-mix(in oklch, var(--warning) 10%, var(--line)); border-top: 0; border-radius: 0 0 var(--radius-lg) var(--radius-lg); box-shadow: var(--shadow-soft); }.state-banner:not(.is-draft) { color: #1f5d3e; background: linear-gradient(180deg, oklch(0.98 0.015 155), oklch(0.96 0.02 155)); border-color: color-mix(in oklch, var(--success) 10%, var(--line)); }.state-icon { margin-top: 2px; font-size: 18px; flex-shrink: 0; }.state-banner strong { font-size: 13.5px; letter-spacing: -.01em; }.state-banner p { margin: 4px 0 0; max-width: 78ch; color: color-mix(in oklch, currentColor 74%, var(--ink)); font-size: 13px; line-height: 1.6; }
.transition-error { display: flex; align-items: center; gap: 10px; margin: 14px 0 0; padding: 12px 16px; color: #8a1f2a; background: #fef2f2; border: 1px solid #fecdd3; border-radius: 12px; font-size: 13px; box-shadow: var(--shadow-soft); }
.case-tabs { margin-top: 22px; }.case-tabs :deep(.el-tabs__header) { position: sticky; top: 0; z-index: 5; margin: 0; padding: 0 6px; background: color-mix(in oklch, var(--app-bg) 88%, white); backdrop-filter: blur(8px) saturate(1.05); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); }.case-tabs :deep(.el-tabs__nav-wrap) { padding: 4px; }.case-tabs :deep(.el-tabs__nav-wrap::after) { display: none; }.case-tabs :deep(.el-tabs__item) { height: 40px; padding: 0 16px; margin: 2px 4px 2px 0; color: var(--ink-secondary); font-size: 14px; font-weight: 600; border-radius: 10px; transition: background .18s, color .18s; }.case-tabs :deep(.el-tabs__item:hover) { color: var(--ink); background: var(--surface-soft); }.case-tabs :deep(.el-tabs__item.is-active) { color: var(--brand-strong); background: var(--brand-soft); font-weight: 700; box-shadow: inset 0 0 0 1px color-mix(in oklch, var(--brand) 12%, transparent); }.case-tabs :deep(.el-tabs__active-bar) { display: none; }.case-tabs :deep(.el-tabs__content) { overflow: visible; padding-top: 20px; }
.overview-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 14px; padding: 13px 16px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); }.overview-toolbar-tip { color: var(--ink-muted); font-size: 12px; line-height: 1.5; }.overview-editing-note { margin-bottom: 14px; border-radius: var(--radius-lg); border: 1px solid color-mix(in oklch, var(--brand) 10%, var(--line)); box-shadow: var(--shadow-soft); }.overview-edit-form { padding: 20px 22px 6px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); }.overview-edit-form :deep(.el-form-item) { margin-bottom: 14px; }.overview-edit-form :deep(.el-form-item__label) { padding-bottom: 6px; color: var(--ink); font-size: 13px; font-weight: 700; }.overview-edit-form :deep(.el-textarea__inner) { padding: 12px 14px; line-height: 1.7; background: var(--surface-soft); border-color: var(--line); }
.rail-owner { display: block; margin-top: 8px; color: var(--ink-muted); font-size: 11px; }
.overview-layout { display: grid; grid-template-columns: minmax(0, 1.42fr) 320px; gap: 18px; align-items: start; }.reading-column { min-width: 0; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); overflow: hidden; }.content-section { padding: 22px 24px 22px; }.content-section + .content-section { border-top: 1px solid var(--line); }
.section-heading { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 16px; }.section-heading > div { display: flex; align-items: center; gap: 10px; }.section-heading h2 { margin: 0; font-size: 16.5px; letter-spacing: -.02em; font-weight: 750; }.section-heading > span { color: var(--ink-muted); font-size: 11.5px; background: var(--surface-soft); border: 1px solid var(--line); padding: 4px 8px; border-radius: 999px; }.section-marker { width: 8px; height: 8px; border-radius: 3px; background: var(--brand); box-shadow: 0 0 0 4px color-mix(in oklch, var(--brand) 12%, transparent); }
.insight-row { display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--line); }.insight-row:last-child, .target-row:last-child { border-bottom: 0; }.subject-label { align-self: start; justify-self: start; padding: 4px 8px; color: var(--brand-strong); background: var(--brand-soft); border: 1px solid color-mix(in oklch, var(--brand) 10%, transparent); border-radius: 8px; font-size: 11.5px; font-weight: 700; }.insight-row p, .target-row p { margin: 0; max-width: 72ch; color: var(--ink-secondary); font-size: 14px; line-height: 1.75; text-wrap: pretty; }
.target-row { display: grid; grid-template-columns: 110px minmax(0, 1fr); gap: 14px; padding: 12px 0; border-bottom: 1px solid var(--line); }.target-row > span { color: var(--ink); font-size: 13.5px; font-weight: 700; }.placeholder-copy { color: var(--ink-muted); font-size: 13.5px; line-height: 1.6; }
.case-rail { overflow: hidden; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); }.rail-section { padding: 18px 18px; }.rail-section + .rail-section { border-top: 1px solid var(--line); }.rail-label { display: block; margin-bottom: 8px; color: var(--ink-muted); font-size: 11px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; }.rail-section > strong { display: block; font-size: 22px; letter-spacing: -.02em; }.rail-section > p { margin: 6px 0 0; color: var(--ink-secondary); font-size: 13px; line-height: 1.6; }.rail-section.compact { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }.rail-section.compact div { display: grid; gap: 5px; padding: 10px 12px; background: var(--surface-soft); border: 1px solid var(--line); border-radius: 12px; }.rail-section.compact span { color: var(--ink-muted); font-size: 11px; font-weight: 600; }.rail-section.compact strong { font-size: 20px; }
.source-note { background: var(--surface-soft); }.source-note p { color: var(--ink); font-weight: 650; }.source-note small { display: block; margin-top: 7px; color: var(--ink-secondary); line-height: 1.6; }.next-steps ol { display: grid; gap: 12px; margin: 0; padding: 0; list-style: none; }.next-steps li { display: flex; align-items: center; gap: 9px; color: var(--ink-secondary); font-size: 13px; }.next-steps li span { display: grid; place-items: center; width: 22px; height: 22px; color: var(--brand-strong); background: var(--brand-soft); border-radius: 50%; font-size: 11px; font-weight: 750; }
.empty-panel { display: grid; justify-items: center; padding: 56px 24px; color: var(--ink-muted); text-align: center; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); }.empty-panel > .el-icon { margin-bottom: 12px; color: var(--brand); font-size: 26px; }.empty-panel h3 { margin: 0; color: var(--ink); font-size: 16px; font-weight: 700; }.empty-panel p { margin: 8px 0 0; max-width: 56ch; line-height: 1.65; font-size: 13.5px; }.subject-empty { min-height: 260px; align-content: center; }.subject-create-actions { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; max-width: 760px; margin-top: 22px; }
.table-section { padding: 22px 24px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); }
.subject-workspace { display: grid; grid-template-columns: 212px minmax(0, 1fr); gap: 18px; align-items: start; }
.subject-nav { overflow: hidden; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); }
.subject-nav-heading { display: flex; justify-content: space-between; align-items: baseline; padding: 16px 16px 12px; border-bottom: 1px solid var(--line); background: color-mix(in oklch, var(--surface-soft) 55%, white); }.subject-nav-heading strong { font-size: 13px; letter-spacing: .02em; font-weight: 700; }.subject-nav-heading span { color: var(--ink-muted); font-size: 11px; background: var(--surface); border: 1px solid var(--line); padding: 3px 7px; border-radius: 999px; }
.subject-nav-item { display: grid; grid-template-columns: 32px minmax(0, 1fr) auto 14px; align-items: center; gap: 10px; width: 100%; padding: 11px 13px; color: var(--ink-secondary); background: transparent; border: 0; border-bottom: 1px solid var(--line); cursor: pointer; text-align: left; transition: background .18s, color .18s, border-color .18s; }.subject-nav-item:hover { background: var(--surface-soft); }.subject-nav-item.is-active { color: var(--brand-strong); background: linear-gradient(90deg, var(--brand-soft), color-mix(in oklch, var(--brand-soft) 70%, white)); border-left: 3px solid var(--brand); padding-left: 10px; }.subject-nav-item:disabled { cursor: not-allowed; opacity: .5; }.subject-avatar { display: grid; place-items: center; width: 32px; height: 32px; color: var(--ink-secondary); background: var(--surface-soft); border: 1px solid var(--line); border-radius: 9px; font-size: 12.5px; font-weight: 750; }.subject-nav-item.is-active .subject-avatar { color: #fff; background: var(--brand); border-color: transparent; }.subject-nav-item > span:nth-child(2) { display: grid; gap: 2px; }.subject-nav-item strong { color: var(--ink); font-size: 13.5px; }.subject-nav-item small { color: var(--ink-muted); font-size: 11px; }.subject-task-count { display: grid; place-items: center; min-width: 22px; height: 22px; padding: 0 6px; color: var(--ink-secondary); background: var(--surface-soft); border: 1px solid var(--line); border-radius: 999px; font-size: 11px; font-weight: 600; }.subject-nav-item .el-icon { color: var(--ink-muted); font-size: 11px; }.subject-add { display: flex; justify-content: center; padding: 10px 14px; border-top: 1px solid var(--line); background: var(--surface-soft); }.subject-add :deep(.el-button) { width: 100%; border-radius: 10px; }
.subject-detail { overflow: hidden; min-width: 0; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); }.subject-detail-header { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 18px 22px; border-bottom: 1px solid var(--line); background: color-mix(in oklch, var(--surface-soft) 45%, white); }.subject-detail-header > div:first-child { display: flex; align-items: center; gap: 10px; }.subject-detail-header h2 { margin: 0; font-size: 17px; font-weight: 750; letter-spacing: -.015em; }.subject-chip { padding: 6px 10px; color: #fff; background: var(--brand); border-radius: 9px; font-size: 11.5px; font-weight: 700; box-shadow: 0 2px 8px color-mix(in oklch, var(--brand) 24%, transparent); }.subject-header-actions { display: flex; align-items: center; gap: 10px; }.subject-counts { display: flex; gap: 12px; margin-right: 2px; color: var(--ink-muted); font-size: 11.5px; }.subject-counts span { background: var(--surface); border: 1px solid var(--line); padding: 4px 8px; border-radius: 999px; }.editing-note { display: flex; align-items: center; gap: 8px; padding: 10px 22px; color: var(--brand-strong); background: var(--brand-soft); border-top: 1px solid color-mix(in oklch, var(--brand) 12%, var(--line)); border-bottom: 1px solid color-mix(in oklch, var(--brand) 12%, var(--line)); font-size: 12px; font-weight: 600; }.editing-note .el-icon { font-size: 14px; }
.subject-section { padding: 20px 22px 22px; }.subject-section + .subject-section { border-top: 1px solid var(--line); }.subject-section-heading { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 14px; }.subject-section-heading > div { display: flex; align-items: center; gap: 8px; }.subject-section-heading .el-icon { color: #fff; background: var(--brand); width: 22px; height: 22px; display: grid; place-items: center; border-radius: 7px; font-size: 12px; padding: 4px; }.subject-section-heading h3 { margin: 0; font-size: 15px; font-weight: 700; }.subject-section-heading > span { color: var(--ink-muted); font-size: 11.5px; }
.subject-fields { margin: 0; }.subject-fields > div { display: grid; grid-template-columns: 86px minmax(0, 1fr); gap: 14px; padding: 11px 0; border-bottom: 1px solid var(--line); }.subject-fields > div:last-child { border-bottom: 0; }.subject-fields dt { color: var(--ink); font-size: 12.5px; font-weight: 700; white-space: nowrap; }.subject-fields dd { margin: 0; color: var(--ink-secondary); font-size: 13.5px; line-height: 1.7; overflow-wrap: anywhere; white-space: pre-wrap; text-wrap: pretty; }.plan-fields { margin-bottom: 14px; }
.subject-edit-form { display: grid; gap: 2px; }.subject-edit-form :deep(.el-form-item) { margin-bottom: 14px; }.subject-edit-form :deep(.el-form-item:last-child) { margin-bottom: 0; }.subject-edit-form :deep(.el-form-item__label) { padding-bottom: 6px; color: var(--ink); font-size: 12.5px; font-weight: 700; line-height: 1.4; }.subject-edit-form :deep(.el-textarea__inner) { padding: 11px 13px; color: var(--ink); background: var(--surface-soft); border-color: var(--line); font-family: inherit; font-size: 13.5px; line-height: 1.7; resize: vertical; }.plan-edit-form { margin-bottom: 14px; }
.task-list-heading { display: flex; justify-content: space-between; align-items: center; padding-top: 14px; border-top: 1px solid var(--line); }.task-list-heading > div { display: flex; align-items: baseline; gap: 8px; }.task-list-heading strong { font-size: 12.5px; font-weight: 700; }.task-list-heading span { color: var(--ink-muted); font-size: 11.5px; background: var(--surface-soft); border: 1px solid var(--line); padding: 3px 7px; border-radius: 999px; }.task-edit-form { margin-top: 12px; padding: 16px; background: var(--surface-soft); border: 1px solid var(--line); border-radius: 12px; }.task-edit-form :deep(.el-form-item) { margin-bottom: 12px; }.task-edit-form :deep(.el-form-item__label) { padding-bottom: 6px; color: var(--ink); font-size: 12px; font-weight: 700; line-height: 1.4; }.task-edit-form :deep(.el-input), .task-edit-form :deep(.el-select), .task-edit-form :deep(.el-date-editor) { width: 100%; }.task-edit-form :deep(.el-textarea__inner) { line-height: 1.65; }.task-form-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }.task-form-actions { display: flex; justify-content: flex-end; gap: 8px; }.task-list { margin-top: 8px; }.task-row { display: flex; justify-content: space-between; gap: 20px; padding: 12px 0; border-bottom: 1px solid var(--line); }.task-row:last-child { border-bottom: 0; }.task-row strong { font-size: 13.5px; }.task-row p { margin: 4px 0 0; color: var(--ink-muted); font-size: 12px; white-space: pre-wrap; line-height: 1.6; }.task-side { display: grid; justify-items: end; align-content: start; gap: 6px; flex-shrink: 0; }.task-meta { display: flex; align-items: flex-start; gap: 6px; flex-wrap: wrap; }.task-meta span { padding: 4px 7px; color: var(--ink-secondary); background: var(--surface); border: 1px solid var(--line); border-radius: 8px; font-size: 11px; font-weight: 600; }
.checkin-form { margin-bottom: 14px; padding: 16px; background: var(--surface-soft); border: 1px solid var(--line); border-radius: 12px; }.checkin-form-grid { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(160px, .9fr); gap: 14px; }.checkin-form :deep(.el-form-item) { margin-bottom: 12px; }.checkin-form :deep(.el-select) { width: 100%; }.checkin-form :deep(.el-form-item__label) { color: var(--ink); font-size: 12px; font-weight: 700; }.percent-suffix { margin-left: 6px; color: var(--ink-muted); font-weight: 600; }.checkin-list { display: grid; gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }.checkin-row { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 16px; padding: 14px 16px; background: var(--surface); }.checkin-row:first-child { border-radius: 12px 12px 0 0; }.checkin-row:last-child { border-bottom: 0; }.completion-rate { display: grid; align-content: center; justify-items: center; min-height: 54px; color: #fff; background: linear-gradient(135deg, var(--brand), var(--brand-strong)); border-radius: 10px; box-shadow: 0 2px 8px color-mix(in oklch, var(--brand) 22%, transparent); }.completion-rate strong { font-size: 16px; }.completion-rate span { margin-top: 1px; font-size: 10px; opacity: .9; }.checkin-row > div:last-child > strong { font-size: 13.5px; }.checkin-row p { margin: 4px 0; color: var(--ink-secondary); line-height: 1.6; font-size: 13px; white-space: pre-wrap; }.checkin-row time { color: var(--ink-muted); font-size: 11px; }.inline-empty { margin-top: 12px; padding: 16px; color: var(--ink-muted); background: var(--surface-soft); border: 1px dashed var(--line); border-radius: 10px; text-align: center; }.inline-empty p { margin: 0; font-size: 12.5px; }
.review-form-card { margin-bottom: 16px; padding: 20px 22px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); }.review-form-header { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid var(--line); }.review-form-header strong { font-size: 14px; font-weight: 750; letter-spacing: -.01em; }.review-form-header span { color: var(--ink-muted); font-size: 11.5px; }.review-form-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }.review-form :deep(.el-form-item__label) { padding-bottom: 6px; color: var(--ink); font-size: 12px; font-weight: 700; }.review-form :deep(.el-select), .review-form :deep(.el-date-editor) { width: 100%; }.review-form :deep(.el-input__wrapper), .review-form :deep(.el-textarea__inner) { border-radius: 10px; }.review-form-actions { display: flex; justify-content: flex-end; }.review-readonly-tip { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; padding: 12px 16px; color: var(--ink-secondary); background: var(--surface-soft); border: 1px solid var(--line); border-radius: 12px; font-size: 12.5px; }
.review-item-head { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 6px; }.review-level { padding: 4px 8px; color: #fff; background: var(--brand); border-radius: 999px; font-size: 11px; font-weight: 700; letter-spacing: .02em; }.review-level.is-school { background: #7c3aed; }.review-level.is-principal { background: #be123c; }.review-level.is-head_teacher { background: var(--brand); }.review-level.is-subject { background: #0ea5e9; }.review-subject, .review-due { padding: 4px 8px; color: var(--ink-secondary); background: var(--surface-soft); border: 1px solid var(--line); border-radius: 999px; font-size: 11px; font-weight: 600; }.review-problem { margin: 0; color: var(--ink); font-size: 13.5px; line-height: 1.7; white-space: pre-wrap; }.review-action, .review-recheck { margin: 6px 0 0; color: var(--ink-secondary); font-size: 12.5px; line-height: 1.6; white-space: pre-wrap; background: var(--surface-soft); border: 1px solid var(--line); padding: 8px 10px; border-radius: 10px; }
.review-timeline { padding: 16px 20px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); }.review-timeline :deep(.el-timeline-item__node) { border-color: var(--brand); background: var(--brand-soft); }.review-timeline :deep(.el-timeline-item__timestamp) { font-size: 11.5px; }
@media (max-width: 1100px) { .overview-layout { grid-template-columns: 1fr; }.case-rail { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }.rail-section + .rail-section { border-top: 0; border-left: 1px solid var(--line); } }
@media (max-width: 940px) { .subject-workspace { grid-template-columns: 1fr; }.subject-nav { display: flex; overflow-x: auto; }.subject-nav-heading { display: none; }.subject-nav-item { flex: 0 0 168px; border-bottom: 0; border-right: 1px solid var(--line); }.subject-nav-item:last-child { border-right: 0; } }
@media (max-width: 760px) { .case-header, .title-line { align-items: flex-start; flex-direction: column; }.title-line { gap: 4px; }.title-line h1 { font-size: 27px; }.case-actions { width: 100%; flex-wrap: wrap; }.case-actions :deep(.el-button) { flex: 1; }.case-tabs :deep(.el-tabs__item) { padding: 0 14px; }.content-section { padding: 22px 20px; }.insight-row, .target-row { grid-template-columns: 1fr; gap: 8px; }.case-rail { grid-template-columns: 1fr; }.rail-section + .rail-section { border-left: 0; border-top: 1px solid var(--line); }.subject-detail-header, .subject-section-heading, .task-row { align-items: flex-start; flex-direction: column; }.subject-detail-header, .subject-section { padding-left: 20px; padding-right: 20px; }.subject-header-actions { width: 100%; flex-wrap: wrap; }.subject-counts { width: 100%; flex-wrap: wrap; }.editing-note { padding-left: 20px; padding-right: 20px; }.subject-fields > div { grid-template-columns: 1fr; gap: 7px; }.task-form-grid, .review-form-grid { grid-template-columns: 1fr; }.task-side { justify-items: start; }.task-meta { flex-wrap: wrap; }.checkin-row { grid-template-columns: 62px minmax(0, 1fr); } }
</style>
