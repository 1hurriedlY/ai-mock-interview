-- ============================================================
-- 模拟面试 AI 助手 — MySQL 数据库脚本（v2：含用户认证）
-- 目标库：interview（utf8mb4）
-- 说明：本脚本仅生成建库/建表语句，不会自动执行。
--       实际运行由后端启动时 Base.metadata.create_all() 自动建表，
--       本脚本仅供手动建库参考，两者表结构保持一致。
-- ============================================================

---------- 1. 建库（默认不执行，请手动确认后执行） ----------
CREATE DATABASE IF NOT EXISTS interview
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE interview;

-- ---------- 2. 用户表（JWT 认证） ----------
CREATE TABLE IF NOT EXISTS users (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    username      VARCHAR(64)     NOT NULL COMMENT '用户名（唯一）',
    password_hash VARCHAR(255)    NOT NULL COMMENT '密码哈希（PBKDF2）',
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_users_username (username)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '注册用户';

-- ---------- 3. 面试会话表 ----------
CREATE TABLE IF NOT EXISTS interview_sessions (
    id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id          BIGINT UNSIGNED NOT NULL COMMENT '所属用户',
    job_title        VARCHAR(255)    NOT NULL COMMENT '目标岗位',
    interviewer_role VARCHAR(32)     NOT NULL DEFAULT 'technical'
                     COMMENT '面试官角色：technical/HR/stress，默认技术面',
    resume_text      LONGTEXT        NULL COMMENT '简历文本（供 Agent 使用）',
    status           VARCHAR(32)     NOT NULL DEFAULT 'in_progress'
                     COMMENT '状态：in_progress/completed',
    created_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at         DATETIME        NULL COMMENT '面试结束时间',
    PRIMARY KEY (id),
    KEY idx_sessions_user (user_id),
    KEY idx_sessions_status (status),
    KEY idx_sessions_created (created_at),
    CONSTRAINT fk_sessions_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '面试会话';

-- ---------- 4. 聊天消息表 ----------
CREATE TABLE IF NOT EXISTS chat_messages (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    session_id  BIGINT UNSIGNED NOT NULL COMMENT '所属会话',
    role        VARCHAR(16)     NOT NULL COMMENT 'user/assistant/system',
    content     LONGTEXT        NOT NULL COMMENT '消息内容',
    reference   LONGTEXT        NULL COMMENT 'AI 回复的参考要点(讲解)，面试结束后展示',
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_messages_session (session_id),
    CONSTRAINT fk_messages_session FOREIGN KEY (session_id)
        REFERENCES interview_sessions (id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '聊天消息';

-- ---------- 5. 面试报告表 ----------
CREATE TABLE IF NOT EXISTS interview_reports (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    session_id     BIGINT UNSIGNED NOT NULL COMMENT '所属会话',
    summary        TEXT            NULL COMMENT '总体评语',
    overall_score  INT             NOT NULL DEFAULT 0 COMMENT '总分 0-100',
    dimensions     TEXT            NULL COMMENT '五维评分 JSON：专业技能/沟通表达/逻辑思维/项目经验/岗位匹配 0-100',
    match_analysis TEXT            NULL COMMENT '岗位匹配度分析 JSON：匹配亮点/差距/改进建议',
    suggestions    TEXT            NULL COMMENT '改进建议 JSON 列表',
    expression_analysis TEXT        NULL COMMENT '表情时间轴 + 点评 JSON（视觉模块）',
    created_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_reports_session (session_id),
    CONSTRAINT fk_reports_session FOREIGN KEY (session_id)
        REFERENCES interview_sessions (id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '面试报告';

-- ---------- 6. 行业调研报告表 ----------
CREATE TABLE IF NOT EXISTS industry_reports (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id       BIGINT UNSIGNED NOT NULL COMMENT '所属用户',
    industry_name VARCHAR(255)    NOT NULL COMMENT '调研行业名称',
    content       LONGTEXT        NOT NULL COMMENT '调研报告 JSON（产业链/头部玩家/商业模式/趋势/岗位技能/面试题）',
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_industry_user (user_id),
    CONSTRAINT fk_industry_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '行业调研报告';

-- ---------- 7. 项目报告表（求职渠道 / 讲项目话术） ----------
CREATE TABLE IF NOT EXISTS project_reports (
    id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id      BIGINT UNSIGNED NOT NULL COMMENT '所属用户',
    type         VARCHAR(32)     NOT NULL COMMENT '类型：channels 渠道清单 / script 讲项目话术',
    project_name VARCHAR(255)    NULL COMMENT '话术对应的项目名称（type=script 时填写）',
    content      LONGTEXT        NOT NULL COMMENT '内容 JSON（渠道清单或 STAR 话术脚本）',
    created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_project_user (user_id),
    KEY idx_project_type (type),
    CONSTRAINT fk_project_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '求职渠道/讲项目话术报告';
