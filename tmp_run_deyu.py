import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from app.core.database import SessionLocal
from app.models.student_case import StudentCase, SubjectPlan, CaseTask, CaseDiagnosis
from app.models.user import User
from datetime import date

deyu_data = {
    "侯思伊": {
        "problem_location": "课堂参与偏被动：政治等学科课堂上较少主动回答问题，师生互动频率低，课堂生成性思考呈现不足；作业与笔记：能按时提交但规范性与细节完整度待提升，政治主观题书写与要点提炼需更精准；集体表现：集体活动参与意愿中等，主动承担任务次数少，课间与自习时间管理偶有松散。",
        "cause_analysis": "学业压力传导至行为：偏科焦虑导致在弱项课堂上回避发言，担心答错影响自信；习惯层面：重结果轻过程，课堂上倾向听讲记录而非主动生成，缺乏提问-回应-复盘闭环；同伴与环境：小组讨论中角色边缘化，缺少正向激励与示范，需通过同伴互助与教师点名激励补位。",
        "struggle_goal": "两周内课堂主动发言/回应>=4次，笔记完整度达90%以上；四周内作业按时率100%且规范分>=85分，政治主观题卷面整洁度提升；月度内主动承担班级任务1次，自习专注时长单次>=40分钟，迟到/缺勤0次。",
        "gaokao_requirement": "对标校规与高考规范：按时到岗不迟到早退、课堂抬头率与互动参与达标；笔记完整、作业规范、卷面整洁可机读；诚信守纪、尊重师长、团结同学，符合《中学生日常行为规范》与考试纪律要求。",
        "reinforcement": "每日：课前3分钟预习提问准备、课中强制1次主动回应、晚自习10分钟当日行为复盘；每周：班主任1次面对面谈话激励、小组互助检查笔记与作业规范、周五作业规范评比；家校：每周五家校群反馈本周出勤与作业情况，需家长周末督促作息与复习节奏。",
        "tasks": [("德育·课堂主动参与打卡", "每节课争取1次主动回答或提问，班主任每日课堂观察记录，周汇总发言次数与质量", "daily"), ("德育·作业与笔记规范周检", "每日自查笔记完整与作业卷面，每周五班主任收检1次并打规范分，未达标当日补齐", "weekly")],
    },
    "唐俊翔": {
        "problem_location": "学习状态与纪律：上课易犯困、注意力不集中，课堂知识吸收率低，偶有趴桌与走神；规范意识：卷面书写潦草，机扫辨识度低，作业与答题卡填涂不规范被扣卷面分；出勤连续性：请假较频繁，知识衔接断裂，课后缺席补课不及时，自习时间利用率不足60%。",
        "cause_analysis": "作息与精力管理失衡：晚睡或作息不规律导致白天犯困，精力分配未向弱科倾斜；基础薄弱引发畏难：数学、理化全面断层导致课堂跟不上、产生回避心理，以犯困形式外显；习惯未养成：未建立预习-听讲-复习-复盘闭环，错题与缺课未及时补，自我监控与时间管理能力弱，家庭督促与家校联动频次不足。",
        "struggle_goal": "两周内课堂瞌睡次数降至<=1次/周，抬头听讲率>=85%；四周内作业按时率>=95%、卷面整洁度达B+以上，早读与自习出勤率100%；月度内缺勤0次、迟到0次，能独立完成当日错题当日清，自习专注度显著提升。",
        "gaokao_requirement": "对标校规与考试规范：作息规律、按时到岗、着装与仪容符合要求；课堂遵守纪律、不迟到不瞌睡、及时笔记与训练；作业与考试书写工整、卷面整洁、答题卡规范填涂，诚信应考、服从监考。",
        "reinforcement": "每日：早读前到岗点名+课前1分钟状态自检、同桌互提醒抬头机制、晚自习15分钟复盘当日出勤与作业；每周：班主任2次课堂巡查与1次谈话激励、宿舍/家庭作息联动检查、周末缺课补学清单；家校：家长每日监督23:00前就寝与早起，班主任周通报出勤与卷面改进情况。",
        "tasks": [("德育·作息与出勤自律打卡", "每日23:00前就寝、按时到岗签到，班主任与家长共管，缺勤当日补课并登记", "daily"), ("德育·卷面与规范强化训练", "每日1次书写与答题卡规范练习，每周评选卷面进步之星，未达标重练", "daily")],
    },
    "张俊超": {
        "problem_location": "学习态度与规划：全学科基础薄弱背景下学习规划混乱、主动性不足，错题零复盘、自信心严重不足；课堂与作业：注意力分散，作业敷衍、卷面潦草，考试态度一度不端正（敷衍作答、漏题）；集体与规范：集体活动参与少，时间分配不合理，弱科投入不足，需强化目标感与抗压能力。",
        "cause_analysis": "长期学业挫败感累积：多科<=30分导致自我效能感低，形成学不会到不愿学到更学不会循环；方法缺失：无系统学习方法与时间规划，缺乏可执行的每日清单与反馈；动机与压力：对高考紧迫感认知不足，抗压与情绪管理能力弱，需外部正向激励与小步成功体验重建信心；家庭与同伴支持待加强，榜样与约束不足。",
        "struggle_goal": "两周内作业敷衍次数0次、卷面整洁度提升至B级，课堂专注时长单次>=30分钟；四周内建立每日清单+晚复盘习惯完成率>=90%，错题本日更、周清；月度内考试态度端正无敷衍/漏题，主动提问>=2次/周，自信心与班级归属感量表提升。",
        "gaokao_requirement": "对标校规与诚信考试：端正学习态度、诚信应考不敷衍、按时完成作业并保证质量；遵守课堂纪律、尊重师长、团结同学、爱护公物；按作息到岗、仪容规范、行为符合《中学生守则》与高考考场规则。",
        "reinforcement": "每日：晨间目标卡（3件必做）+晚15分钟复盘与打卡，小组长逐日检查作业与错题本；每周：班主任1次一对一谈话与1次小组激励会，展示小进步并给予正向反馈；家校：每周家长会商1次，共定下周行为小目标，家校群每日通报完成度，形成学校约束+家庭鼓励双支持。",
        "tasks": [("德育·每日清单与晚复盘", "每日晨间列3件必做（作业/笔记/错题），晚自习15分钟复盘完成度并签字确认", "daily"), ("德育·诚信与规范周约", "每周诚信考试与作业规范承诺1次，班主任周检卷面与完成质量并公示进步", "weekly")],
    },
    "张筠舒": {
        "problem_location": "专注与投入：上课专注度不够，心思偶不在课堂，对高考紧迫感与重要性认知不足，听课吸收效率不高；出勤与衔接：后期缺勤率较高，材料信息解读不全面，热点与原理衔接不紧，地理等学科复习断档；自我驱动：重难点内容浅尝辄止，课后未能及时巩固拓展，主动学习动力与方法待加强。",
        "cause_analysis": "目标感阶段性模糊：优势学科（语文97、英语93）带来短暂满足，对数学/历史/政治/地理等中等薄弱模块紧迫性预估不足；时间与情绪管理：未能建立目标-计划-执行-反馈闭环，缺勤后缺乏补学路径，压力应对以回避为主；环境支持：需要更清晰的阶段目标分解与可视化进度，以及班主任与学科教师的协同提醒与同伴学习氛围带动。",
        "struggle_goal": "两周内课堂专注度（抬头率与互动）>=85%，缺勤0次、迟到0次；四周内课后当日巩固完成率>=90%，薄弱学科错题整理周清；月度内能自主制定周计划并执行率>=85%，对高考目标认知明确，学习主动性自评提升1档。",
        "gaokao_requirement": "对标校规与备考纪律：按时到岗、课堂全程专注、笔记完整；遵守自习与考试纪律，作业与测试诚信规范；仪容仪表、行为举止符合中学生规范，具备高三备考生的时间观念与集体意识。",
        "reinforcement": "每日：课前2分钟目标默念+课中同桌互检专注、晚10分钟计划复盘；每周：班主任1次目标分解谈话、学科教师1次学法点拨、周末缺课补学清单闭环；家校：家长周末检查作息与周计划执行，周通报专注与出勤改进，树立每日小目标达成正反馈。",
        "tasks": [("德育·专注与出勤自律打卡", "每日专注自评与出勤签到，缺勤当日补学并登记，班主任周汇总公示", "daily"), ("德育·周计划执行与复盘", "每周日制定下周学习与行为计划，周五复盘执行率并调整下周重点", "weekly")],
    },
    "徐援伟": {
        "problem_location": "行为与状态：上课易犯困、注意力不集中，课堂效率低，仅偶尔能专注回应；规范与连续性：卷面书写潦草，机扫辨识度低，请假频繁导致知识缺失、复习节奏被打乱；基础与习惯：无明显优势学科，时间分配与弱科投入不足，学习自信心待提升，作业与笔记细节遗漏多。",
        "cause_analysis": "作息与基础双重制约：作息不规律与基础断层叠加，课堂跟不上易产生倦怠与瞌睡；方法与反馈缺失：未掌握预习-听讲-复习-错题闭环，缺课后无补学机制，薄弱点越积越多；动机与支持：目标（350分）较远但分解不足，需小步阶梯与高频正反馈，家校协同与同伴带动频次不足，未形成外部约束与激励。",
        "struggle_goal": "两周内课堂犯困<=1次/周、笔记完整度>=85%，作业按时率>=95%；四周内作息规律（23:00前就寝）达标率>=90%，卷面整洁度提升至B+，缺勤0次；月度内能按基础题60%拿分节奏稳定执行，错题日清周清完成率>=85%，自信心与规范意识显著改善。",
        "gaokao_requirement": "对标校规与考试规范：作息规律、按时到岗、仪容规范；课堂遵守纪律、不迟到不瞌睡、及时笔记；作业与考试书写工整、卷面整洁、答题卡规范，诚信应考、服从管理，符合高考考场与日常行为规范。",
        "reinforcement": "每日：早到点名+课前状态自检、同桌互提醒、晚自习10分钟行为与作业复盘；每周：班主任1次谈话与1次宿舍/家庭作息抽查、学科教师1次规范抽检；家校：家长每日监督就寝与到岗，班主任周通报出勤、规范与作业完成度，未达标当日补齐并跟踪。",
        "tasks": [("德育·作息与课堂状态打卡", "每日就寝与到岗打卡、课堂专注自评，班主任与家长共管并周通报", "daily"), ("德育·作业规范与补学清单", "每日作业规范自查与缺课补学清单打卡，每周评选规范进步之星", "daily")],
    },
    "王五": {
        "problem_location": "新构建档待养成：作为试点班新纳入学生，德育行为基线待建立，需重点养成高三备考生的时间观念、课堂参与与作业规范；目前课堂互动、笔记完整度与作业按时率尚未形成稳定记录，需从零建立行为台账与反馈闭环。",
        "cause_analysis": "环境适应期：新班级与备考节奏需适应，尚未形成稳定的预习-听讲-复习-复盘习惯与同伴支持网络；目标与规则待内化：对高三校规与备考纪律的细节要求理解不深，需通过明确示范与高频提醒转化为自觉行为；家校协同待启动，需尽快建立家长联络与周反馈机制以提供外部约束与激励。",
        "struggle_goal": "两周内出勤率100%、课堂抬头率>=85%、笔记完整度>=85%；四周内作业按时率>=95%、卷面整洁度B+以上，主动发言>=2次/周；月度内能执行每日清单+晚复盘且完成率>=85%，行为台账无迟到/缺勤/重大违纪。",
        "gaokao_requirement": "对标《中学生日常行为规范》与高考考场规则：按时到岗、仪容规范、课堂守纪、笔记完整、作业规范、卷面整洁、诚信守纪、尊重师长、团结同学、服从管理。",
        "reinforcement": "每日：晨间3件事清单+课中主动参与1次+晚10分钟行为复盘打卡；每周：班主任1次谈话与1次规范抽检、小组互查笔记与作业；家校：建群周通报出勤与规范表现，家长周末督促作息与计划执行，形成家校双向反馈。",
        "tasks": [("德育·高三备考行为养成打卡", "每日出勤、课堂参与、笔记与作业规范四项打卡，班主任日检周评", "daily"), ("德育·周行为复盘与表彰", "每周五复盘本周行为台账，评选守纪与规范进步之星并公示", "weekly")],
    },
}

db = SessionLocal()
try:
    cases = db.query(StudentCase).all()
    updated = 0
    for case in cases:
        stu = db.get(User, case.student_id)
        name = stu.name if stu else f"case{case.id}"
        data = deyu_data.get(name, deyu_data["王五"])
        plan = db.query(SubjectPlan).filter_by(student_case_id=case.id, subject="德育").first()
        if plan is None:
            plan = SubjectPlan(student_case_id=case.id, subject="德育", teacher_id=case.owner_teacher_id, problem_location=data["problem_location"], cause_analysis=data["cause_analysis"], struggle_goal=data["struggle_goal"], gaokao_requirement=data["gaokao_requirement"], reinforcement=data["reinforcement"], status="draft")
            db.add(plan)
            db.flush()
            print(f"CREATED 德育 for {name} (case {case.id})")
            updated += 1
        else:
            plan.problem_location = data["problem_location"]
            plan.cause_analysis = data["cause_analysis"]
            plan.struggle_goal = data["struggle_goal"]
            plan.gaokao_requirement = data["gaokao_requirement"]
            plan.reinforcement = data["reinforcement"]
            plan.teacher_id = case.owner_teacher_id
            print(f"UPDATED 德育 for {name} (case {case.id})")
            updated += 1
        for title, desc, cadence in data["tasks"]:
            existing = db.query(CaseTask).filter_by(student_case_id=case.id, subject="德育", title=title).first()
            if existing is None:
                task = CaseTask(student_case_id=case.id, subject="德育", title=title, description=desc, cadence=cadence, starts_on=date.today(), due_on=date(2027,6,30), status="pending", created_by=case.owner_teacher_id)
                db.add(task)
                print(f"  + task {title}")
            else:
                existing.description = desc
                existing.cadence = cadence
                print(f"  ~ task {title} updated")
        diag2 = db.query(CaseDiagnosis).filter_by(student_case_id=case.id, subject="德育").first()
        if diag2 is None:
            db.add(CaseDiagnosis(student_case_id=case.id, subject="德育", category="behavior", content=data["problem_location"] + "\n" + data["cause_analysis"], source="manual_supplement", is_confirmed=False))
            print(f"  + diagnosis 德育")
    db.commit()
    print(f"Done updated {updated} 德育 plans")
    for case2 in db.query(StudentCase).all():
        stu2 = db.get(User, case2.student_id)
        plan2 = db.query(SubjectPlan).filter_by(student_case_id=case2.id, subject="德育").first()
        tasks2 = db.query(CaseTask).filter_by(student_case_id=case2.id, subject="德育").all()
        print(f"{stu2.name}: plan exists={plan2 is not None} tasks={len(tasks2)} len={len(plan2.problem_location) if plan2 else 0}")
finally:
    db.close()
