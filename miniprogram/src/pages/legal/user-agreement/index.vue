<template>
  <scroll-view class="legal-page" scroll-y>
    <view class="legal-card">
      <text class="legal-title">用户服务协议</text>
      <text class="legal-meta">生效日期：2026年9月22日</text>

      <view v-for="section in sections" :key="section.title" class="legal-section">
        <text class="legal-heading">{{ section.title }}</text>
        <text class="legal-text">{{ section.content }}</text>
      </view>
    </view>
  </scroll-view>
</template>

<script setup>
const sections = [
  {
    title: '一、协议适用范围',
    content: '欢迎使用“一生一案学业发展”小程序（以下简称“本小程序”）。本小程序由白粉高级英才中学运营，用于学校高三学生的学业发展档案、学习任务、成绩评定及家校协同管理。请在使用前认真阅读本协议；点击勾选同意并登录或注册，即表示您已阅读、理解并接受本协议及《隐私政策》。未满十四周岁的学生应在监护人同意和指导下使用。'
  },
  {
    title: '二、账号与使用规则',
    content: '您应使用本人或经授权的账号登录。学生使用学号，其他角色可使用手机号作为账号；不得出借、转让、冒用账号或协助他人绕过权限控制。您应妥善保管密码，如发现账号异常，请立即联系学校管理员。学校会依据账号角色分配可访问的数据范围。'
  },
  {
    title: '三、服务内容与使用目的',
    content: '本小程序用于展示和管理学习计划、学习任务及打卡、成绩与评定、学生发展档案、班级课程安排和必要的家校沟通信息。教师、学校管理人员仅可在履行教育教学和学生管理职责的必要范围内处理相关信息；家长仅可查看已授权关联学生的信息。'
  },
  {
    title: '四、用户责任',
    content: '您提交的信息应真实、准确、合法。不得上传违法内容、侵犯他人权益的材料，或未经授权查看、下载、传播其他学生信息。因您违反本协议或法律法规造成的损失，由您依法承担相应责任。'
  },
  {
    title: '五、服务变更与联系我们',
    content: '我们可能因教育教学安排、法律法规或系统安全需要调整服务，并通过本小程序公示。若您对本协议、账号或个人信息处理有疑问、意见或投诉，可联系学校管理员处理。'
  }
]
</script>

<style scoped>
@import "../../../styles/legal.css";
</style>
