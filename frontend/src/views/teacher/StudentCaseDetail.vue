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
          <el-button :loading="exporting" :disabled="editingProfile || editingOverview || editingPlan || !!editingTask" @click="handleExport"><el-icon><Document /></el-icon>导出 DOCX</el-button>
          <span v-if="detail" class="export-meta">V{{ detail.version }} · {{ labels[detail.status] || detail.status }}</span>
          <template v-if="detail.can_manage && !editingProfile && !editingOverview && !editingPlan && !editingTask">
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
        <el-tab-pane label="基本信息" name="profile">
          <section class="profile-card">
            <header class="profile-card-header">
              <div>
                <span class="profile-kicker">学生档案</span>
                <h2>基本信息</h2>
                <p>记录学生身份、家庭反馈及需要关注的健康事项。</p>
              </div>
              <div v-if="detail.can_manage && detail.status !== 'archived'" class="profile-actions">
                <template v-if="!editingProfile">
                  <el-button plain @click="startProfileEdit"><el-icon><EditPen /></el-icon>编辑信息</el-button>
                </template>
                <template v-else>
                  <el-button :disabled="savingProfile" @click="cancelProfileEdit">取消</el-button>
                  <el-button type="primary" :loading="savingProfile" @click="saveProfile">保存信息</el-button>
                </template>
              </div>
            </header>

            <template v-if="!editingProfile">
              <div class="profile-section">
                <div class="profile-section-title"><span class="section-marker"></span><div><h3>学生信息</h3><p>用于识别学生、入学背景、入学成绩及家长联系方式</p></div></div>
                <dl class="profile-grid">
                  <div><dt>姓名</dt><dd>{{ profileValue('student_name') }}</dd></div>
                  <div><dt>性别</dt><dd>{{ profileValue('gender') }}</dd></div>
                  <div><dt>民族</dt><dd>{{ profileValue('ethnicity') }}</dd></div>
                  <div><dt>年级</dt><dd>{{ profileValue('grade') }}</dd></div>
                  <div class="profile-wide"><dt>生源地学校</dt><dd>{{ profileValue('source_school') }}</dd></div>
                </dl>
                <div class="merged-parent-divider is-entrance"><span>入学成绩</span><small>总分与各科均为选填，留空表示未录入</small></div>
                <dl class="profile-grid entrance-grid">
                  <div><dt>总分</dt><dd>{{ entranceScoreDisplay('entrance_total_score') }}</dd></div>
                  <div><dt>语文</dt><dd>{{ entranceScoreDisplay('entrance_chinese') }}</dd></div>
                  <div><dt>数学</dt><dd>{{ entranceScoreDisplay('entrance_math') }}</dd></div>
                  <div><dt>英语</dt><dd>{{ entranceScoreDisplay('entrance_english') }}</dd></div>
                  <div><dt>物理</dt><dd>{{ entranceScoreDisplay('entrance_physics') }}</dd></div>
                  <div><dt>化学</dt><dd>{{ entranceScoreDisplay('entrance_chemistry') }}</dd></div>
                  <div><dt>生物</dt><dd>{{ entranceScoreDisplay('entrance_biology') }}</dd></div>
                  <div><dt>政治</dt><dd>{{ entranceScoreDisplay('entrance_politics') }}</dd></div>
                  <div><dt>历史</dt><dd>{{ entranceScoreDisplay('entrance_history') }}</dd></div>
                  <div><dt>地理</dt><dd>{{ entranceScoreDisplay('entrance_geography') }}</dd></div>
                </dl>
                <div v-if="hasLegacyEntranceScores" class="entrance-legacy-tip">备注：{{ profileValue('entrance_scores') }}</div>
                <div class="merged-parent-divider"><span>家长联系方式</span><small>手机号即家长登录账号，录入后自动注册（默认密码 88888888）</small></div>
                <dl class="profile-grid parent-grid">
                  <div><dt>家长姓名</dt><dd>{{ profileValue('parent_name') }}</dd></div>
                  <div><dt>联系电话</dt><dd>{{ profileValue('parent_phone') }}</dd></div>
                  <div><dt>与学生关系</dt><dd>{{ parentRelationshipLabel(profileValue('parent_relationship')) }}</dd></div>
                </dl>
                <div v-if="detail.guardian_accounts && detail.guardian_accounts.length" class="parent-account-tip">
                  <el-icon><CircleCheckFilled /></el-icon>
                  <span>已绑定家长账号：<strong v-for="acc in detail.guardian_accounts" :key="acc.parent_id" class="parent-account-chip">{{ acc.name }}（{{ acc.username }}）</strong> 默认密码 88888888</span>
                </div>
                <div v-else-if="profileValue('parent_phone') !== '暂未填写'" class="parent-account-tip is-warn"><el-icon><WarningFilled /></el-icon><span>已记录家长手机号，保存后系统将自动注册家长账号（默认密码 88888888）并绑定至该学生</span></div>
                <div v-else class="parent-empty-tip">尚未录入家长联系方式，录入后系统将自动注册家长账号</div>
              </div>
              <div class="profile-section">
                <div class="profile-section-title"><span class="section-marker"></span><div><h3>家庭反馈</h3><p>由班主任根据家长沟通情况如实记录</p></div></div>
                <dl class="profile-grid profile-copy-grid">
                  <div><dt>家长评价</dt><dd>{{ profileValue('parent_evaluation') }}</dd></div>
                  <div><dt>主要需求</dt><dd>{{ profileValue('primary_needs') }}</dd></div>
                </dl>
              </div>
              <div class="profile-section health-section">
                <div class="profile-section-title">
                  <span class="section-marker"></span>
                  <div><h3>健康与体检信息</h3><p>仅记录教育服务和在校安全确有必要的信息</p></div>
                  <span class="health-visibility-badge" :class="healthVisible ? 'is-visible' : 'is-hidden'">
                    <el-icon><View v-if="healthVisible" /><Hide v-else /></el-icon>
                    {{ healthVisible ? '已公开' : '仅校长可见' }}
                  </span>
                </div>
                <div v-if="!healthVisible" class="health-hidden-tip">
                  <el-icon><WarningFilled /></el-icon>
                  <span v-if="auth.role === 'admin'">该体检史已设为仅校长可见，当前以校长身份可查看完整内容。</span>
                  <span v-else>该体检史已设为仅校长可见，具体内容已隐藏。</span>
                </div>
                <dl class="profile-grid health-grid">
                  <div><dt>过敏史</dt><dd>{{ healthFieldValue('allergy_history') }}</dd></div>
                  <div><dt>隐性疾病</dt><dd>{{ healthFieldValue('underlying_conditions') }}</dd></div>
                  <div class="profile-wide"><dt>其他</dt><dd>{{ healthFieldValue('other_health_notes') }}</dd></div>
                </dl>
              </div>
            </template>

            <el-form v-else label-position="top" class="profile-form">
              <div class="profile-form-block">
                <h3>学生信息</h3>
                <div class="profile-form-grid">
                  <el-form-item label="姓名"><el-input v-model="profileForm.student_name" maxlength="64" /></el-form-item>
                  <el-form-item label="性别"><el-select v-model="profileForm.gender" clearable placeholder="请选择"><el-option label="男" value="男" /><el-option label="女" value="女" /><el-option label="其他" value="其他" /></el-select></el-form-item>
                  <el-form-item label="民族"><el-input v-model="profileForm.ethnicity" maxlength="32" placeholder="例如：汉族" /></el-form-item>
                  <el-form-item label="年级">
                    <el-select v-model="profileForm.grade" clearable placeholder="请选择年级">
                      <el-option v-for="grade in gradeOptions" :key="grade" :label="grade" :value="grade" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="生源地学校" class="profile-form-wide"><el-input v-model="profileForm.source_school" maxlength="128" placeholder="填写学生原就读学校" /></el-form-item>
                </div>
                <div class="merged-parent-divider is-form is-entrance"><span>入学成绩</span><small>总分与各科均为选填，留空表示未录入</small></div>
                <div class="profile-form-grid entrance-form-grid">
                  <el-form-item label="总分"><el-input-number v-model="profileForm.entrance_total_score" :min="0" :max="750" controls-position="right" placeholder="选填" style="width:100%" /></el-form-item>
                  <el-form-item label="语文"><el-input-number v-model="profileForm.entrance_chinese" :min="0" :max="150" controls-position="right" placeholder="选填" style="width:100%" /></el-form-item>
                  <el-form-item label="数学"><el-input-number v-model="profileForm.entrance_math" :min="0" :max="150" controls-position="right" placeholder="选填" style="width:100%" /></el-form-item>
                  <el-form-item label="英语"><el-input-number v-model="profileForm.entrance_english" :min="0" :max="150" controls-position="right" placeholder="选填" style="width:100%" /></el-form-item>
                  <el-form-item label="物理"><el-input-number v-model="profileForm.entrance_physics" :min="0" :max="150" controls-position="right" placeholder="选填" style="width:100%" /></el-form-item>
                  <el-form-item label="化学"><el-input-number v-model="profileForm.entrance_chemistry" :min="0" :max="150" controls-position="right" placeholder="选填" style="width:100%" /></el-form-item>
                  <el-form-item label="生物"><el-input-number v-model="profileForm.entrance_biology" :min="0" :max="150" controls-position="right" placeholder="选填" style="width:100%" /></el-form-item>
                  <el-form-item label="政治"><el-input-number v-model="profileForm.entrance_politics" :min="0" :max="150" controls-position="right" placeholder="选填" style="width:100%" /></el-form-item>
                  <el-form-item label="历史"><el-input-number v-model="profileForm.entrance_history" :min="0" :max="150" controls-position="right" placeholder="选填" style="width:100%" /></el-form-item>
                  <el-form-item label="地理"><el-input-number v-model="profileForm.entrance_geography" :min="0" :max="150" controls-position="right" placeholder="选填" style="width:100%" /></el-form-item>
                </div>
                <div class="merged-parent-divider is-form"><span>家长联系方式</span><small>手机号即家长登录账号，录入后自动注册</small></div>
                <div class="parent-notice"><el-icon><CircleCheckFilled /></el-icon><span>录入手机号后系统将自动以该手机号注册家长账号，默认密码 <strong>88888888</strong>，家长可直接登录查看已确认档案。</span></div>
                <div class="profile-form-grid parent-form-grid">
                  <el-form-item label="家长姓名"><el-input v-model="profileForm.parent_name" maxlength="64" placeholder="例如：张先生 / 李女士" /></el-form-item>
                  <el-form-item label="联系电话"><el-input v-model="profileForm.parent_phone" maxlength="32" placeholder="11位手机号，自动作为家长登录账号" /></el-form-item>
                  <el-form-item label="与学生关系">
                    <el-select v-model="profileForm.parent_relationship" clearable placeholder="请选择">
                      <el-option label="父亲" value="父亲" /><el-option label="母亲" value="母亲" /><el-option label="监护人" value="监护人" /><el-option label="其他" value="其他" />
                    </el-select>
                  </el-form-item>
                </div>
              </div>
              <div class="profile-form-block">
                <h3>家庭反馈</h3>
                <div class="profile-form-grid profile-form-copy">
                  <el-form-item label="家长评价"><el-input v-model="profileForm.parent_evaluation" type="textarea" :autosize="{ minRows: 3, maxRows: 8 }" maxlength="4000" show-word-limit placeholder="填写家长对学生学习、习惯和状态的评价" /></el-form-item>
                  <el-form-item label="主要需求"><el-input v-model="profileForm.primary_needs" type="textarea" :autosize="{ minRows: 3, maxRows: 8 }" maxlength="4000" show-word-limit placeholder="填写家长及学生当前最主要的支持需求" /></el-form-item>
                </div>
              </div>
              <div class="profile-form-block health-section">
                <div class="health-notice"><el-icon><WarningFilled /></el-icon><span>健康信息属于敏感资料，请仅填写与学生安全和教学支持直接相关的必要内容。</span></div>
                <div class="health-visibility-control">
                  <div class="health-visibility-label">
                    <strong>是否显示体检史</strong>
                    <span>关闭后仅校长端可见，教师与家长端将隐藏具体内容</span>
                  </div>
                  <el-switch
                    v-model="profileForm.health_visible"
                    active-text="公开显示"
                    inactive-text="仅校长可见"
                    inline-prompt
                    style="--el-switch-on-color: var(--brand);"
                  />
                </div>
                <h3>健康与体检信息</h3>
                <div class="profile-form-grid profile-form-health">
                  <el-form-item label="过敏史"><el-input v-model="profileForm.allergy_history" type="textarea" :autosize="{ minRows: 2, maxRows: 6 }" maxlength="2000" placeholder="无相关情况可填写“无”" /></el-form-item>
                  <el-form-item label="隐性疾病"><el-input v-model="profileForm.underlying_conditions" type="textarea" :autosize="{ minRows: 2, maxRows: 6 }" maxlength="2000" placeholder="填写需要学校关注的既往或潜在疾病" /></el-form-item>
                  <el-form-item label="其他" class="profile-form-wide"><el-input v-model="profileForm.other_health_notes" type="textarea" :autosize="{ minRows: 2, maxRows: 6 }" maxlength="2000" placeholder="填写其他体检或健康注意事项" /></el-form-item>
                </div>
              </div>
            </el-form>
          </section>
        </el-tab-pane>

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
                  <section v-for="(item, index) in targetSections" :key="`${item.label}-${item.text}`" class="target-stage" :class="{ 'is-expanded': expandedTargetIndex === index }">
                    <button class="target-row target-stage-trigger" type="button" :aria-expanded="expandedTargetIndex === index" @click="toggleTargetStage(index)">
                      <span>{{ item.label }}</span><p>{{ item.text }}</p><el-icon><ArrowRight /></el-icon>
                    </button>
                    <div v-if="expandedTargetIndex === index" class="target-progress-panel">
                      <div v-if="targetScoresLoading" class="target-progress-skeleton" aria-label="正在读取最新周测成绩"><span v-for="n in 6" :key="n"></span></div>
                      <template v-else-if="subjectTargets(item).length">
                        <section v-if="!isGaokaoStage(item, index)" class="goal-axis" :aria-label="`${item.label}各科目标进度`">
                          <header class="goal-axis-legend"><span><i class="is-current"></i>当前成绩</span><span><i class="is-target"></i>阶段目标</span></header>
                          <div class="goal-axis-rows">
                            <div v-for="row in stageProgressRows(item)" :key="row.subject" class="goal-axis-row">
                              <strong class="goal-subject">{{ row.subject }}</strong>
                              <div class="goal-track" :title="goalRowTitle(row)">
                                <span class="goal-target-range" :style="{ width: scoreWidth(row.targetScore, item) }"></span>
                                <span v-if="row.current" class="goal-current-range" :style="{ width: scoreWidth(row.current.score, item) }"></span>
                                <span class="goal-task-copy">{{ row.taskText }}</span>
                                <span class="goal-target-marker" :style="{ left: scoreWidth(row.targetScore, item) }"></span>
                              </div>
                              <div class="goal-score-copy"><strong>{{ row.targetScore }}分</strong><span>{{ row.current ? `当前 ${row.current.score}分` : '当前待录入' }}</span></div>
                            </div>
                          </div>
                          <div class="goal-axis-scale" aria-hidden="true"><span></span><div><i v-for="tick in stageAxisTicks(item)" :key="tick" :style="{ left: `${(tick / stageAxisMax(item)) * 100}%` }">{{ tick }}</i></div><span>分数</span></div>
                        </section>

                        <section v-else class="gaokao-timeline" aria-label="高考目标各科任务时间轴">
                          <header><div><strong>各科任务时间轴</strong><span>高考目标</span></div><small>点击科目对应月份查看任务</small></header>
                          <div class="gaokao-timeline-scroll">
                            <div class="gaokao-month-head" :style="timelineColumns(item, index)">
                              <span>科目</span>
                              <button v-for="month in stageTimelineMonths(item, index)" :key="month.key" type="button" :class="{ 'is-selected': selectedGaokaoMonthKey === month.key }" :aria-pressed="selectedGaokaoMonthKey === month.key" @click="selectGaokaoMonth(month.key)">{{ month.label }}</button>
                            </div>
                            <div v-for="row in gaokaoSubjectTimelineRows(item, index)" :key="row.subject" class="gaokao-subject-row">
                              <strong>{{ row.subject }}</strong>
                              <div class="gaokao-subject-track" :style="timelineTrackStyle(item, index, row)">
                                <el-popover v-for="(month, monthIndex) in stageTimelineMonths(item, index)" :key="month.key" placement="bottom" trigger="click" :width="320" popper-class="gaokao-task-popper">
                                  <template #reference>
                                    <button type="button" class="gaokao-month-cell" :class="{ 'is-selected': selectedGaokaoMonthKey === month.key }" :style="{ gridColumn: monthIndex + 1, gridRow: '1 / -1' }" :aria-label="`查看${month.label}${row.subject}任务`" @click="selectGaokaoMonth(month.key)"></button>
                                  </template>
                                  <div class="gaokao-cell-detail">
                                    <header><strong>{{ row.subject }} · {{ month.label }}</strong><span>{{ gaokaoSubjectMonthTasks(item, index, row.subject, month.key).length }} 项</span></header>
                                    <div v-if="gaokaoSubjectMonthTasks(item, index, row.subject, month.key).length">
                                      <article v-for="task in gaokaoSubjectMonthTasks(item, index, row.subject, month.key)" :key="task.key"><p>{{ task.content }}</p><small>{{ task.range }}</small></article>
                                    </div>
                                    <p v-else class="gaokao-cell-empty">该月份尚未安排具体任务。</p>
                                  </div>
                                </el-popover>
                                <span v-for="segment in row.segments" :key="segment.key" class="gaokao-task-segment" :class="{ 'is-empty': segment.empty }" :style="{ gridColumn: `${segment.start + 1} / ${segment.end + 2}`, gridRow: segment.row }" :title="segment.title">{{ segment.title }}</span>
                              </div>
                            </div>
                          </div>
                        </section>
                        <p class="target-progress-note">{{ isGaokaoStage(item, index) ? '时间轴依据各科已确认任务的开始和截止日期生成。' : '当前成绩取各科最新一次周测；具体任务来自已确认的学科任务，目标分数来自本阶段升学目标。' }}</p>
                      </template>
                      <div v-else class="target-progress-loading">该阶段目标中尚未识别到各科目标分数。</div>
                    </div>
                  </section>
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
                :disabled="(editingProfile || editingPlan || editingTask || editingOverview) && selectedSubject !== subject"
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
        <el-tab-pane label="周测成绩" name="weekly">
          <div class="weekly-section">
            <div class="weekly-header">
              <div><strong>周测成绩趋势</strong><span>{{ weeklyRows.length }} 条记录</span></div>
              <div class="weekly-actions">
                <el-select v-model="weeklySubject" placeholder="全部学科" clearable style="width: 140px" @change="loadWeekly"><el-option v-for="s in subjectOrder.slice(0,9)" :key="s" :label="s" :value="s" /></el-select>
                <el-button @click="loadWeekly">刷新</el-button>
                <el-button type="primary" plain @click="$router.push('/teacher/weekly-scores')">去录入</el-button>
              </div>
            </div>
            <div v-if="weeklyRows.length" ref="weeklyChartRef" style="height: 260px; margin: 12px 0; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 12px"></div>
            <el-table v-if="weeklyRows.length" :data="weeklyRows" max-height="360">
              <el-table-column prop="subject" label="学科" width="100" />
              <el-table-column prop="exam_date" label="日期" width="120" />
              <el-table-column prop="exam_name" label="周次" min-width="140" show-overflow-tooltip />
              <el-table-column label="分数" width="120"><template #default="{ row }">{{ row.score }} / {{ row.max_score }}</template></el-table-column>
              <el-table-column prop="rank_in_class" label="排名" width="90"><template #default="{ row }">{{ row.rank_in_class || '-' }}</template></el-table-column>
              <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
            </el-table>
            <div v-else class="empty-panel"><h3>暂无周测成绩</h3><p>班主任可在“周测成绩”页面按班级批量录入，该生的历次周测将在此汇聚并展示趋势。</p></div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="月报" name="monthly">
          <div class="weekly-section">
            <div class="weekly-header">
              <div><strong>月报</strong><span>{{ monthlyRows.length }} 份</span></div>
              <div class="weekly-actions">
                <el-button @click="loadMonthly">刷新</el-button>
                <el-button type="primary" plain @click="$router.push('/teacher/monthly-reports')">去管理</el-button>
              </div>
            </div>
            <el-table v-if="monthlyRows.length" :data="monthlyRows" style="margin-top:12px">
              <el-table-column prop="month_label" label="月份" width="110" />
              <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="monthlyStatusType(row.status)">{{ monthlyStatusText(row.status) }}</el-tag></template></el-table-column>
              <el-table-column label="摘要" min-width="300" show-overflow-tooltip><template #default="{ row }">{{ (row.final_content || row.ai_content || '').slice(0,80) }}</template></el-table-column>
              <el-table-column label="操作" width="120"><template #default="{ row }"><el-button link type="primary" @click="$router.push('/teacher/monthly-reports')">查看</el-button></template></el-table-column>
            </el-table>
            <div v-else class="empty-panel"><h3>暂无月报</h3><p>班主任可在“月报”页面按月生成 AI 初稿，汇总学情与德育并给出改进方案。</p></div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="历史版本" name="versions"><div class="empty-panel"><h3>当前为第 {{ detail.version }} 版</h3><p>正式调整后，旧版本将在这里保留并支持对比。</p></div></el-tab-pane>
      </el-tabs>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowRight, Calendar, CircleCheck, CircleCheckFilled, Document, EditPen, Hide, Plus, Search, View, WarningFilled } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { checkinCaseTask, createCaseReview, createCaseTask, exportStudentCase, getStudentCase, transitionStudentCase, updateCaseTask, updateStudentCase, updateStudentProfile, upsertSubjectPlan } from '../../api/studentCases'
import { listWeeklyScores } from '../../api/weeklyScores'
import { listMonthlyReports } from '../../api/monthlyReports'
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
const editingProfile = ref(false)
const savingProfile = ref(false)
const detail = ref(null)
const active = ref('overview')
const expandedTargetIndex = ref(null)
const selectedGaokaoMonthKey = ref('')
const targetScoreRows = ref([])
const targetScoresLoaded = ref(false)
const targetScoresLoading = ref(false)
const weeklyRows = ref([])
const weeklySubject = ref('')
const weeklyChartRef = ref(null)
let weeklyChart = null
const monthlyRows = ref([])
const selectedSubject = ref('')
const manualSubjects = ref([])
const planForm = ref(createEmptyPlanForm())
const taskForm = ref(createEmptyTaskForm())
const overviewForm = ref(createEmptyOverviewForm())
const profileForm = ref(createEmptyProfileForm())
const checkinForm = ref({ task_id: null, completion_rate: 0, self_check: '' })
const reviewForm = ref(createEmptyReviewForm())
const labels = { draft: '草稿', pending_confirmation: '待确认', executing: '执行中', pending_review: '待复盘', adjusted: '已调整', archived: '已归档' }
const gradeOptions = ['初一', '初二', '初三', '高一', '高二', '高三', '复读']
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
const canEditPlan = computed(() => detail.value?.can_manage && ['draft', 'pending_confirmation', 'adjusted'].includes(detail.value?.status) && !editingProfile.value && !editingOverview.value && !editingTask.value)
const canEditOverview = computed(() => detail.value?.can_manage && ['draft', 'pending_confirmation'].includes(detail.value?.status) && !editingProfile.value && !editingPlan.value && !editingTask.value)
const canEditTasks = computed(() => detail.value?.can_manage && detail.value?.status !== 'archived' && !editingProfile.value && !editingPlan.value && !editingOverview.value)
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

function createEmptyProfileForm() {
  return {
    student_name: '', gender: '', ethnicity: '', source_school: '', grade: '',
    entrance_scores: '',
    entrance_total_score: null,
    entrance_chinese: null,
    entrance_math: null,
    entrance_english: null,
    entrance_physics: null,
    entrance_chemistry: null,
    entrance_biology: null,
    entrance_politics: null,
    entrance_history: null,
    entrance_geography: null,
    parent_evaluation: '', primary_needs: '', allergy_history: '',
    underlying_conditions: '', other_health_notes: '',
    health_visible: true,
    parent_name: '', parent_phone: '', parent_relationship: '',
  }
}

const healthVisible = computed(() => {
  const v = detail.value?.student_profile?.health_visible
  return v !== false
})

function healthFieldValue(field) {
  if (!healthVisible.value && auth.role !== 'admin') {
    return '仅校长可见'
  }
  return detail.value?.student_profile?.[field] || '暂未填写'
}

function entranceScoreDisplay(field) {
  const v = detail.value?.student_profile?.[field]
  if (v === null || v === undefined || v === '') return '—'
  return String(v)
}

const hasLegacyEntranceScores = computed(() => {
  const p = detail.value?.student_profile
  if (!p) return false
  const legacy = (p.entrance_scores || '').trim()
  if (!legacy) return false
  const hasNew = ['entrance_total_score','entrance_chinese','entrance_math','entrance_english','entrance_physics','entrance_chemistry','entrance_biology','entrance_politics','entrance_history','entrance_geography'].some(k => p[k] !== null && p[k] !== undefined && p[k] !== '')
  return !hasNew
})

function parentRelationshipLabel(value) {
  if (!value || value === '暂未填写') return '暂未填写'
  return value
}

function profileValue(field) {
  return detail.value?.student_profile?.[field] || '暂未填写'
}

function startProfileEdit() {
  profileForm.value = { ...createEmptyProfileForm(), ...(detail.value?.student_profile || {}) }
  editingProfile.value = true
}

function cancelProfileEdit() {
  editingProfile.value = false
  profileForm.value = createEmptyProfileForm()
}

async function saveProfile() {
  if (!detail.value) return
  if (!profileForm.value.student_name.trim()) {
    ElMessage.warning('请填写学生姓名')
    return
  }
  if (profileForm.value.parent_phone && !/^1[3-9]\d{9}$/.test(profileForm.value.parent_phone.trim())) {
    ElMessage.warning('家长联系方式需为11位手机号')
    return
  }
  savingProfile.value = true
  try {
    const wasPhone = (detail.value.student_profile?.parent_phone || '').trim()
    const newPhone = (profileForm.value.parent_phone || '').trim()
    const saved = await updateStudentProfile(detail.value.id, profileForm.value)
    detail.value.student_profile = saved
    detail.value.student_name = saved.student_name
    editingProfile.value = false
    try {
      const refreshed = await getStudentCase(detail.value.id)
      detail.value.guardian_accounts = refreshed.guardian_accounts || detail.value.guardian_accounts
    } catch {}
    if (newPhone && newPhone !== wasPhone) {
      ElMessage.success('已保存，家长账号 ' + newPhone + ' 已自动注册，默认密码 88888888')
    } else {
      ElMessage.success('学生基本信息已保存')
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败，请重试')
  } finally {
    savingProfile.value = false
  }
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

function subjectTargets(stage) {
  return subjectOrder.slice(0, 9).flatMap((subject) => {
    const match = stage?.text?.match(new RegExp(`${subject}\\s*(\\d+(?:\\.\\d+)?)`))
    return match ? [{ subject, targetScore: Number(match[1]) }] : []
  })
}

function latestSubjectScore(subject) {
  const latest = targetScoreRows.value
    .filter((item) => item.subject === subject)
    .sort((a, b) => String(b.exam_date).localeCompare(String(a.exam_date)))[0]
  return latest ? { score: Number(latest.score), examDate: latest.exam_date, examName: latest.exam_name } : null
}

function subjectTaskText(subject) {
  const task = [...tasksFor(subject)].sort((a, b) => String(a.starts_on).localeCompare(String(b.starts_on)))[0]
  if (!task) return '尚未安排具体任务'
  const firstLine = String(task.description || '').split(/\r?\n/).map((line) => line.trim()).find(Boolean)
  return firstLine || task.title
}

function stageProgressRows(stage) {
  return subjectTargets(stage).map((item) => ({ ...item, current: latestSubjectScore(item.subject), taskText: subjectTaskText(item.subject) }))
}

function stageAxisMax(stage) {
  const values = stageProgressRows(stage).flatMap((row) => [row.targetScore, row.current?.score || 0])
  return Math.max(100, Math.ceil(Math.max(...values, 0) / 20) * 20)
}

function stageAxisTicks(stage) {
  const max = stageAxisMax(stage)
  const step = max <= 100 ? 20 : Math.ceil(max / 5 / 10) * 10
  const ticks = []
  for (let value = 0; value < max; value += step) ticks.push(value)
  if (ticks[ticks.length - 1] !== max) ticks.push(max)
  return ticks
}

function scoreWidth(value, stage) {
  const max = stageAxisMax(stage)
  const normalized = Math.max(0, Math.min(max, Number(value) || 0))
  return `${(normalized / max) * 100}%`
}

function goalRowTitle(row) {
  const current = row.current ? `当前 ${row.current.score} 分，记录于 ${row.current.examDate}` : '当前成绩待录入'
  return `${row.subject}：${current}；阶段目标 ${row.targetScore} 分；任务：${row.taskText}`
}

function parseCaseDate(value) {
  const [year, month, day] = String(value || '').slice(0, 10).split('-').map(Number)
  return year && month && day ? new Date(year, month - 1, day) : null
}

function addCalendarMonths(date, offset) {
  return new Date(date.getFullYear(), date.getMonth() + offset, 1)
}

function monthKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

function stageBaseDate() {
  const starts = (detail.value?.tasks || []).map((task) => parseCaseDate(task.starts_on)).filter(Boolean).sort((a, b) => a - b)
  const base = starts[0] || new Date()
  return new Date(base.getFullYear(), base.getMonth(), 1)
}

function stageMonthBounds(stage, index) {
  const range = stage?.label?.match(/(\d+)\s*[-—－~～至]\s*(\d+)\s*个?月/)
  if (range) return [Math.max(0, Number(range[1]) - 1), Math.max(0, Number(range[2]) - 1)]
  const priorEnd = targetSections.value.slice(0, index).reduce((max, item) => {
    const match = item.label?.match(/(\d+)\s*[-—－~～至]\s*(\d+)\s*个?月/)
    return match ? Math.max(max, Number(match[2])) : max
  }, 0)
  const base = stageBaseDate()
  const latestDue = (detail.value?.tasks || []).map((task) => parseCaseDate(task.due_on)).filter(Boolean).sort((a, b) => b - a)[0]
  const latestOffset = latestDue ? (latestDue.getFullYear() - base.getFullYear()) * 12 + latestDue.getMonth() - base.getMonth() : priorEnd + 5
  return [priorEnd, Math.max(priorEnd + 5, Math.min(latestOffset, priorEnd + 11))]
}

function stageTimelineMonths(stage, index) {
  const base = stageBaseDate()
  const [startOffset, endOffset] = stageMonthBounds(stage, index)
  return Array.from({ length: endOffset - startOffset + 1 }, (_, position) => {
    const date = addCalendarMonths(base, startOffset + position)
    return { key: monthKey(date), label: `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}` }
  })
}

function isGaokaoStage(stage, index) {
  return /高考/.test(stage?.label || '') || index === targetSections.value.length - 1
}

function timelineColumns(stage, index) {
  const count = stageTimelineMonths(stage, index).length
  return { gridTemplateColumns: `58px repeat(${count}, minmax(112px, 1fr))` }
}

function timelineTrackStyle(stage, index, row) {
  const count = stageTimelineMonths(stage, index).length
  return {
    gridTemplateColumns: `repeat(${count}, minmax(112px, 1fr))`,
    gridTemplateRows: `repeat(${Math.max(row.segments.length, 1)}, 24px)`,
    '--timeline-month-width': `${100 / count}%`,
  }
}

function selectGaokaoMonth(key) {
  selectedGaokaoMonthKey.value = key
}

function taskDisplayText(task) {
  const firstLine = String(task.description || '').split(/\r?\n/).map((line) => line.trim()).find(Boolean)
  return firstLine || task.title || '未命名任务'
}

function gaokaoSubjectTimelineRows(stage, index) {
  const months = stageTimelineMonths(stage, index)
  const visibleStart = months[0]?.key
  const visibleEnd = months[months.length - 1]?.key
  return subjectTargets(stage).map(({ subject }) => {
    const segments = tasksFor(subject).flatMap((task) => {
      const starts = parseCaseDate(task.starts_on)
      const due = parseCaseDate(task.due_on)
      if (!starts || !due) return []
      const startKey = monthKey(starts)
      const endKey = monthKey(due)
      if (endKey < visibleStart || startKey > visibleEnd) return []
      const start = Math.max(0, months.findIndex((month) => month.key >= startKey))
      const end = months.reduce((last, month, monthIndex) => month.key <= endKey ? monthIndex : last, 0)
      return [{ key: task.id, start, end: Math.max(start, end), row: 1, title: taskDisplayText(task), empty: false }]
    }).map((segment, segmentIndex) => ({ ...segment, row: segmentIndex + 1 }))
    return { subject, segments: segments.length ? segments : [{ key: `${subject}-empty`, start: 0, end: months.length - 1, row: 1, title: '尚未安排具体任务', empty: true }] }
  })
}

function gaokaoSubjectMonthTasks(stage, index, subject, selectedKey) {
  if (!selectedKey || !stageTimelineMonths(stage, index).some((month) => month.key === selectedKey)) return []
  if (!subjectTargets(stage).some((item) => item.subject === subject)) return []
  return (detail.value?.tasks || [])
    .filter((task) => {
      const starts = parseCaseDate(task.starts_on)
      const due = parseCaseDate(task.due_on)
      return task.subject === subject && starts && due && monthKey(starts) <= selectedKey && monthKey(due) >= selectedKey
    })
    .sort((a, b) => String(a.starts_on).localeCompare(String(b.starts_on)))
    .map((task) => ({ key: task.id, content: String(task.description || '').trim() || task.title || '未填写任务内容', range: `${formatDate(task.starts_on)} 至 ${formatDate(task.due_on)}，${taskStatusLabel(task.status)}` }))
}

async function toggleTargetStage(index) {
  if (expandedTargetIndex.value === index) {
    expandedTargetIndex.value = null
    return
  }
  expandedTargetIndex.value = index
  if (isGaokaoStage(targetSections.value[index], index)) return
  targetScoresLoading.value = true
  try {
    if (!targetScoresLoaded.value) {
      targetScoreRows.value = await listWeeklyScores({ student_id: detail.value.student_id })
      targetScoresLoaded.value = true
    }
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '周测成绩读取失败')
  } finally {
    targetScoresLoading.value = false
  }
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
async function loadWeekly() {
  if (!detail.value) return
  const params = { student_id: detail.value.student_id }
  if (weeklySubject.value) params.subject = weeklySubject.value
  weeklyRows.value = await listWeeklyScores(params)
  await nextTick()
  if (weeklyChartRef.value && weeklyRows.value.length) {
    if (weeklyChart) weeklyChart.dispose()
    weeklyChart = echarts.init(weeklyChartRef.value)
    const sorted = [...weeklyRows.value].sort((a,b) => a.exam_date.localeCompare(b.exam_date))
    weeklyChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: sorted.map(d => d.exam_date) },
      yAxis: { type: 'value' },
      series: [{ type: 'line', smooth: true, data: sorted.map(d => d.score), areaStyle: {}, itemStyle: { color: '#4a86ff' } }],
      grid: { left: 36, right: 16, top: 16, bottom: 28 }
    })
  }
}
async function loadMonthly() {
  if (!detail.value) return
  monthlyRows.value = await listMonthlyReports({ student_id: detail.value.student_id })
}
function monthlyStatusText(s) { return { generating:'生成中', generated:'待发布', published:'已发布', failed:'生成失败'}[s] || s }
function monthlyStatusType(s) { return { generated:'warning', published:'success', failed:'danger'}[s] || 'info' }

watch(active, (v) => { if (v === 'weekly') loadWeekly(); if (v === 'monthly') loadMonthly() })
watch(weeklySubject, loadWeekly)

async function load() {
  loading.value = true
  try {
    detail.value = await getStudentCase(route.params.id)
    if (!subjectOptions.value.includes(selectedSubject.value)) selectedSubject.value = subjectOptions.value[0] || ''
    const firstTask = tasksFor(selectedSubject.value)[0]
    checkinForm.value.task_id = firstTask?.id || null
    if (auth.role === 'admin') reviewForm.value.review_level = 'school'
    else if (detail.value?.can_manage) reviewForm.value.review_level = 'head_teacher'
    if (active.value === 'weekly') await loadWeekly()
    if (active.value === 'monthly') await loadMonthly()
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
.profile-card { overflow: hidden; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); }.profile-card-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; padding: 22px 24px; border-bottom: 1px solid var(--line); background: linear-gradient(135deg, color-mix(in oklch, var(--brand-soft) 46%, white), var(--surface)); }.profile-kicker { display: block; margin-bottom: 5px; color: var(--brand-strong); font-size: 11px; font-weight: 750; letter-spacing: .12em; }.profile-card-header h2 { margin: 0; font-size: 20px; letter-spacing: -.02em; }.profile-card-header p { margin: 7px 0 0; color: var(--ink-muted); font-size: 12.5px; }.profile-actions { display: flex; gap: 8px; flex-shrink: 0; }.profile-section { padding: 22px 24px 24px; }.profile-section + .profile-section { border-top: 1px solid var(--line); }.profile-section-title { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }.profile-section-title > div { display: grid; gap: 3px; }.profile-section-title h3 { margin: 0; font-size: 15px; }.profile-section-title p { margin: 0; color: var(--ink-muted); font-size: 11.5px; }.profile-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1px; margin: 0; overflow: hidden; background: var(--line); border: 1px solid var(--line); border-radius: 12px; }.profile-grid > div { min-width: 0; padding: 14px 16px; background: var(--surface-soft); }.profile-grid .profile-wide { grid-column: 1 / -1; }.profile-grid dt { margin-bottom: 6px; color: var(--ink-muted); font-size: 11.5px; font-weight: 650; }.profile-grid dd { margin: 0; color: var(--ink); font-size: 13.5px; line-height: 1.65; white-space: pre-wrap; overflow-wrap: anywhere; }.profile-copy-grid > div, .health-grid > div { min-height: 96px; }.health-section { background: color-mix(in oklch, var(--surface-soft) 58%, white); }.profile-form { padding: 0; }.profile-form-block { padding: 22px 24px 10px; }.profile-form-block + .profile-form-block { border-top: 1px solid var(--line); }.profile-form-block h3 { margin: 0 0 16px; font-size: 15px; }.profile-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 16px; }.profile-form-wide { grid-column: 1 / -1; }.profile-form-copy :deep(.el-form-item), .profile-form-health :deep(.el-form-item) { align-self: start; }.profile-form :deep(.el-form-item__label) { padding-bottom: 6px; color: var(--ink); font-size: 12.5px; font-weight: 700; }.profile-form :deep(.el-select) { width: 100%; }.profile-form :deep(.el-input__wrapper), .profile-form :deep(.el-textarea__inner) { background: var(--surface-soft); border-radius: 10px; }.profile-form :deep(.el-textarea__inner) { line-height: 1.65; }.health-notice { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 16px; padding: 11px 13px; color: #7a4d12; background: var(--warning-soft); border: 1px solid color-mix(in oklch, var(--warning) 14%, var(--line)); border-radius: 10px; font-size: 12px; line-height: 1.55; }.health-notice .el-icon { margin-top: 2px; flex-shrink: 0; }
.entrance-grid { grid-template-columns: repeat(5, minmax(0, 1fr)); }
.parent-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.entrance-form-grid { grid-template-columns: repeat(5, minmax(0, 1fr)); }
.parent-form-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.merged-parent-divider { display: flex; align-items: center; gap: 10px; margin: 18px 0 12px; padding-top: 16px; border-top: 1px solid var(--line); }
.merged-parent-divider span { font-size: 12.5px; font-weight: 700; color: var(--ink); white-space: nowrap; }
.merged-parent-divider small { color: var(--ink-muted); font-size: 11.5px; }
.merged-parent-divider.is-form { margin: 16px 0 8px; padding: 14px 0 0; border-top: 1px dashed var(--line); }
.entrance-legacy-tip { margin-top: 8px; color: var(--ink-muted); font-size: 12px; }
.parent-account-tip { display: flex; align-items: center; gap: 8px; margin-top: 12px; padding: 10px 12px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; font-size: 12.5px; color: #166534; }
.parent-account-tip.is-warn { background: var(--warning-soft); border-color: #fde68a; color: #92400e; }
.parent-account-chip { display: inline-flex; align-items: center; padding: 2px 8px; background: #fff; border: 1px solid var(--line); border-radius: 999px; font-size: 12px; margin-left: 4px; }
.parent-empty-tip { margin-top: 12px; padding: 10px 12px; background: var(--surface-soft); border: 1px dashed var(--line); border-radius: 10px; color: var(--ink-muted); font-size: 12.5px; text-align: center; }
.parent-notice { display: flex; gap: 8px; padding: 10px 12px; background: var(--surface-soft); border: 1px solid var(--line); border-radius: 10px; font-size: 12.5px; color: var(--ink-secondary); margin-bottom: 12px; }
.health-visibility-badge { display: inline-flex; align-items: center; gap: 5px; padding: 4px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; border: 1px solid var(--line); }
.health-visibility-badge.is-visible { color: #166534; background: #f0fdf4; border-color: #bbf7d0; }
.health-visibility-badge.is-hidden { color: #7c2d12; background: #fff7ed; border-color: #fed7aa; }
.health-hidden-tip { display: flex; gap: 8px; padding: 10px 12px; background: #fff7ed; border: 1px solid #fed7aa; border-radius: 10px; color: #9a3412; font-size: 12.5px; margin-bottom: 12px; }
.health-visibility-control { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 12px 14px; background: var(--surface-soft); border: 1px solid var(--line); border-radius: 10px; margin-bottom: 16px; }
.health-visibility-label { display: grid; gap: 2px; }
.health-visibility-label strong { font-size: 13px; }
.health-visibility-label span { font-size: 11.5px; color: var(--ink-muted); }
.health-form-hidden-tip { display: flex; gap: 8px; margin-top: 10px; padding: 10px 12px; background: #fff7ed; border: 1px solid #fed7aa; border-radius: 10px; color: #9a3412; font-size: 12px; }
.section-marker { width: 3px; height: 18px; border-radius: 999px; background: var(--brand); }
.overview-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 14px; padding: 13px 16px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); }.overview-toolbar-tip { color: var(--ink-muted); font-size: 12px; line-height: 1.5; }.overview-editing-note { margin-bottom: 14px; border-radius: var(--radius-lg); border: 1px solid color-mix(in oklch, var(--brand) 10%, var(--line)); box-shadow: var(--shadow-soft); }.overview-edit-form { padding: 20px 22px 6px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); }.overview-edit-form :deep(.el-form-item) { margin-bottom: 14px; }.overview-edit-form :deep(.el-form-item__label) { padding-bottom: 6px; color: var(--ink); font-size: 13px; font-weight: 700; }.overview-edit-form :deep(.el-textarea__inner) { padding: 12px 14px; line-height: 1.7; background: var(--surface-soft); border-color: var(--line); }
.rail-owner { display: block; margin-top: 8px; color: var(--ink-muted); font-size: 11px; }
.overview-layout { display: grid; grid-template-columns: minmax(0, 1.42fr) 320px; gap: 18px; align-items: start; }.reading-column { min-width: 0; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); overflow: hidden; }.content-section { padding: 22px 24px 22px; }.content-section + .content-section { border-top: 1px solid var(--line); }
.section-heading { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 16px; }.section-heading > div { display: flex; align-items: center; gap: 10px; }.section-heading h2 { margin: 0; font-size: 16.5px; letter-spacing: -.02em; font-weight: 750; }.section-heading > span { color: var(--ink-muted); font-size: 11.5px; background: var(--surface-soft); border: 1px solid var(--line); padding: 4px 8px; border-radius: 999px; }.section-marker { width: 8px; height: 8px; border-radius: 3px; background: var(--brand); box-shadow: 0 0 0 4px color-mix(in oklch, var(--brand) 12%, transparent); }
.insight-row { display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--line); }.insight-row:last-child, .target-stage:last-child .target-row { border-bottom: 0; }.subject-label { align-self: start; justify-self: start; padding: 4px 8px; color: var(--brand-strong); background: var(--brand-soft); border: 1px solid color-mix(in oklch, var(--brand) 10%, transparent); border-radius: 8px; font-size: 11.5px; font-weight: 700; }.insight-row p, .target-row p { margin: 0; max-width: 72ch; color: var(--ink-secondary); font-size: 14px; line-height: 1.75; text-wrap: pretty; }
.target-list { margin: 0 -24px -22px; }
.target-stage { border-bottom: 1px solid var(--line); }
.target-stage:last-child { border-bottom: 0; }
.target-row { display: grid; grid-template-columns: 110px minmax(0, 1fr) 18px; align-items: center; gap: 14px; width: 100%; padding: 12px 24px; background: transparent; border: 0; color: inherit; cursor: pointer; font: inherit; text-align: left; }
.target-row:hover, .target-stage.is-expanded > .target-row { background: var(--surface-soft); }
.target-row > span { color: var(--ink); font-size: 13.5px; font-weight: 700; }
.target-row > .el-icon { color: var(--ink-muted); transition: transform .2s ease, color .2s ease; }
.target-stage.is-expanded .target-row > .el-icon { color: var(--brand); transform: rotate(90deg); }
.target-progress-panel { padding: 14px 16px 12px; border-top: 1px solid var(--line); background: var(--surface); }
.goal-axis { padding: 12px 14px 10px; border: 1px solid var(--line); border-radius: 12px; }
.goal-axis-legend { display: flex; justify-content: flex-end; gap: 18px; margin-bottom: 11px; color: var(--ink-secondary); font-size: 11px; }
.goal-axis-legend span { display: inline-flex; align-items: center; gap: 6px; }
.goal-axis-legend i { width: 22px; height: 7px; border-radius: 3px; }
.goal-axis-legend .is-current { background: var(--brand); }
.goal-axis-legend .is-target { background: var(--line-strong); }
.goal-axis-rows { display: grid; gap: 8px; }
.goal-axis-row { display: grid; grid-template-columns: 44px minmax(0, 1fr) 76px; align-items: center; gap: 10px; }
.goal-subject { color: var(--ink); font-size: 12.5px; text-align: right; }
.goal-track { position: relative; overflow: hidden; height: 28px; background-color: var(--surface-soft); background-image: linear-gradient(to right, var(--line) 1px, transparent 1px); background-size: 20% 100%; border: 1px solid var(--line-strong); border-radius: 5px; }
.goal-target-range, .goal-current-range { position: absolute; inset: 0 auto 0 0; }
.goal-target-range { background: color-mix(in oklch, var(--line-strong) 62%, transparent); }
.goal-current-range { top: auto; bottom: 2px; z-index: 2; height: 3px; background: var(--brand); border-radius: 0 3px 3px 0; }
.goal-target-marker { position: absolute; z-index: 3; top: 3px; bottom: 3px; width: 2px; background: var(--ink-secondary); transform: translateX(-1px); }
.goal-task-copy { position: absolute; z-index: 4; top: 3px; left: 8px; max-width: calc(100% - 16px); overflow: hidden; color: var(--ink); font-size: 10.5px; font-weight: 650; line-height: 19px; text-overflow: ellipsis; white-space: nowrap; }
.goal-score-copy { display: grid; gap: 2px; min-width: 0; }
.goal-score-copy strong { color: var(--ink); font-size: 12.5px; }
.goal-score-copy span { color: var(--ink-muted); font-size: 10px; white-space: nowrap; }
.goal-axis-scale { display: grid; grid-template-columns: 44px minmax(0, 1fr) 76px; gap: 10px; margin-top: 4px; }
.goal-axis-scale > div { position: relative; height: 20px; }
.goal-axis-scale i { position: absolute; top: 3px; color: var(--ink-muted); font-size: 10px; font-style: normal; transform: translateX(-50%); }
.goal-axis-scale i:first-child { transform: none; }
.goal-axis-scale i:last-child { transform: translateX(-100%); }
.goal-axis-scale > span:last-child { color: var(--ink-muted); font-size: 10px; }
.gaokao-timeline { padding: 12px 14px 10px; background: var(--surface-soft); border-radius: 12px; }
.gaokao-timeline > header { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; margin-bottom: 10px; }
.gaokao-timeline > header > div { display: flex; align-items: baseline; gap: 8px; }
.gaokao-timeline > header strong { font-size: 13px; }
.gaokao-timeline > header span { color: var(--brand-strong); font-size: 11px; font-weight: 650; }
.gaokao-timeline > header small { color: var(--ink-muted); font-size: 10.5px; }
.gaokao-timeline-scroll { overflow-x: auto; padding-bottom: 6px; }
.gaokao-month-head { display: grid; align-items: center; width: max-content; min-width: 100%; border-bottom: 1px solid var(--line-strong); }
.gaokao-month-head span { padding: 0 8px 7px; color: var(--ink-muted); font-size: 10.5px; font-weight: 650; text-align: right; }
.gaokao-month-head button { margin: 0 4px 5px; padding: 4px 6px; color: var(--ink-secondary); background: transparent; border: 0; border-radius: 5px; cursor: pointer; font: inherit; font-size: 10.5px; font-weight: 650; }
.gaokao-month-head button:hover, .gaokao-month-head button.is-selected { color: var(--brand-strong); background: var(--brand-soft); }
.gaokao-month-head button:focus-visible, .gaokao-month-cell:focus-visible { outline: 2px solid var(--brand); outline-offset: -2px; }
.gaokao-subject-row { display: grid; grid-template-columns: 58px minmax(0, 1fr); width: max-content; min-width: 100%; border-bottom: 1px solid var(--line); }
.gaokao-subject-row:last-child { border-bottom: 0; }
.gaokao-subject-row > strong { align-self: center; padding-right: 9px; color: var(--ink); font-size: 12px; text-align: right; }
.gaokao-subject-track { display: grid; min-height: 30px; background-color: color-mix(in oklch, var(--surface) 72%, transparent); background-image: linear-gradient(to right, var(--line) 1px, transparent 1px); background-size: var(--timeline-month-width) 100%; }
.gaokao-month-cell { z-index: 0; width: 100%; min-width: 0; padding: 0; background: transparent; border: 0; cursor: pointer; }
.gaokao-month-cell:hover, .gaokao-month-cell.is-selected { background: color-mix(in oklch, var(--brand-soft) 62%, transparent); }
.gaokao-task-segment { z-index: 1; align-self: center; overflow: hidden; margin: 2px 4px; padding: 3px 6px; color: var(--ink); background: color-mix(in oklch, var(--line-strong) 70%, var(--surface)); border-radius: 4px; font-size: 10px; font-weight: 650; line-height: 1.3; text-overflow: ellipsis; white-space: nowrap; pointer-events: none; }
.gaokao-task-segment.is-empty { color: var(--ink-muted); background: transparent; border: 1px dashed var(--line-strong); font-weight: 500; text-align: center; }
.gaokao-cell-detail > header { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--line); }
.gaokao-cell-detail > header strong { color: var(--ink); font-size: 12.5px; }
.gaokao-cell-detail > header span { color: var(--ink-muted); font-size: 10.5px; }
.gaokao-cell-detail article { padding: 9px 0 2px; }
.gaokao-cell-detail article + article { margin-top: 7px; border-top: 1px solid var(--line); }
.gaokao-cell-detail article p { margin: 0; color: var(--ink-secondary); font-size: 11.5px; line-height: 1.55; white-space: pre-wrap; }
.gaokao-cell-detail article small { display: block; margin-top: 5px; color: var(--ink-muted); font-size: 10px; }
.gaokao-cell-empty { margin: 0; padding: 12px 0 4px; color: var(--ink-muted); font-size: 11.5px; text-align: center; }
.target-progress-note { margin: 9px 0 0; color: var(--ink-muted); font-size: 10.5px; line-height: 1.5; }
.target-progress-loading { padding: 28px 16px; color: var(--ink-muted); text-align: center; font-size: 12.5px; }
.target-progress-skeleton { display: grid; gap: 8px; }
.target-progress-skeleton span { height: 28px; background: var(--surface-soft); border-radius: 5px; }
.placeholder-copy { color: var(--ink-muted); font-size: 13.5px; line-height: 1.6; }
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
.weekly-section { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); padding: 18px 20px; }
.weekly-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.weekly-header strong { font-size: 14px; }
.weekly-header span { color: var(--ink-muted); font-size: 12px; margin-left: 8px; }
.weekly-actions { display: flex; gap: 8px; align-items: center; }
@media (max-width: 1100px) { .overview-layout { grid-template-columns: 1fr; }.case-rail { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }.rail-section + .rail-section { border-top: 0; border-left: 1px solid var(--line); } }
@media (max-width: 940px) { .subject-workspace { grid-template-columns: 1fr; }.subject-nav { display: flex; overflow-x: auto; }.subject-nav-heading { display: none; }.subject-nav-item { flex: 0 0 168px; border-bottom: 0; border-right: 1px solid var(--line); }.subject-nav-item:last-child { border-right: 0; } }
@media (max-width: 760px) { .case-header, .title-line, .profile-card-header { align-items: flex-start; flex-direction: column; }.title-line { gap: 4px; }.title-line h1 { font-size: 27px; }.case-actions, .profile-actions { width: 100%; flex-wrap: wrap; }.case-actions :deep(.el-button), .profile-actions :deep(.el-button) { flex: 1; }.case-tabs :deep(.el-tabs__item) { padding: 0 14px; }.profile-card-header, .profile-section, .profile-form-block, .content-section { padding-left: 20px; padding-right: 20px; }.profile-grid, .profile-form-grid { grid-template-columns: 1fr; }.profile-grid .profile-wide, .profile-form-wide { grid-column: auto; }.insight-row, .target-row { grid-template-columns: 1fr; gap: 8px; }.case-rail { grid-template-columns: 1fr; }.rail-section + .rail-section { border-left: 0; border-top: 1px solid var(--line); }.subject-detail-header, .subject-section-heading, .task-row { align-items: flex-start; flex-direction: column; }.subject-detail-header, .subject-section { padding-left: 20px; padding-right: 20px; }.subject-header-actions { width: 100%; flex-wrap: wrap; }.subject-counts { width: 100%; flex-wrap: wrap; }.editing-note { padding-left: 20px; padding-right: 20px; }.subject-fields > div { grid-template-columns: 1fr; gap: 7px; }.task-form-grid, .review-form-grid { grid-template-columns: 1fr; }.task-side { justify-items: start; }.task-meta { flex-wrap: wrap; }.checkin-row { grid-template-columns: 62px minmax(0, 1fr); } }
@media (max-width: 760px) { .target-list { margin-right: -20px; margin-left: -20px; }.target-row { grid-template-columns: 1fr 18px; gap: 6px 8px; padding-right: 20px; padding-left: 20px; }.target-row > span, .target-row > p { grid-column: 1; }.target-row > .el-icon { grid-column: 2; grid-row: 1 / span 2; }.target-progress-panel { padding-right: 8px; padding-left: 8px; }.goal-axis { padding: 10px 6px 8px; }.goal-axis-legend { gap: 10px; }.goal-axis-row, .goal-axis-scale { grid-template-columns: 30px minmax(0, 1fr) 48px; gap: 5px; }.goal-subject { font-size: 11px; }.goal-task-copy { left: 4px; max-width: calc(100% - 8px); font-size: 9.5px; }.goal-score-copy strong { font-size: 11px; }.goal-score-copy span { font-size: 8.5px; line-height: 1.25; white-space: normal; }.goal-axis-scale i { font-size: 8.5px; }.gaokao-timeline { padding-right: 8px; padding-left: 8px; }.gaokao-timeline > header { align-items: flex-start; flex-direction: column; gap: 3px; } }
</style>
