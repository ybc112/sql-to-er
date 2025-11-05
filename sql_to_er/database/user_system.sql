-- 用户系统数据库设计
-- 创建数据库
CREATE DATABASE IF NOT EXISTS user_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE user_system;

-- 1. 用户表
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    balance DECIMAL(10,2) DEFAULT 0.00 COMMENT '账户余额/额度',
    invite_code VARCHAR(20) UNIQUE NOT NULL COMMENT '个人邀请码',
    invited_by VARCHAR(20) DEFAULT NULL COMMENT '被谁邀请的邀请码',
    total_recharge DECIMAL(10,2) DEFAULT 0.00 COMMENT '累计充值金额',
    total_consumption DECIMAL(10,2) DEFAULT 0.00 COMMENT '累计消费额度',
    invite_earnings DECIMAL(10,2) DEFAULT 0.00 COMMENT '邀请收益',
    status TINYINT DEFAULT 1 COMMENT '账户状态：1正常，0禁用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    last_login_at TIMESTAMP NULL COMMENT '最后登录时间',
    
    INDEX idx_username (username),
    INDEX idx_invite_code (invite_code),
    INDEX idx_invited_by (invited_by),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 2. 充值记录表
CREATE TABLE recharge_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用户ID',
    order_no VARCHAR(50) UNIQUE NOT NULL COMMENT '订单号',
    amount DECIMAL(10,2) NOT NULL COMMENT '充值金额',
    bonus_amount DECIMAL(10,2) DEFAULT 0.00 COMMENT '赠送金额',
    total_amount DECIMAL(10,2) NOT NULL COMMENT '实际到账金额',
    payment_method VARCHAR(20) DEFAULT 'alipay' COMMENT '支付方式：alipay',
    trade_no VARCHAR(100) DEFAULT NULL COMMENT '支付宝交易号',
    status TINYINT DEFAULT 0 COMMENT '状态：0待支付，1已支付，2已取消，3已退款',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    paid_at TIMESTAMP NULL COMMENT '支付时间',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_order_no (order_no),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='充值记录表';

-- 3. 消费记录表
CREATE TABLE consumption_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用户ID',
    service_type VARCHAR(50) NOT NULL COMMENT '服务类型：sql_to_er, defense_questions等',
    amount DECIMAL(10,2) NOT NULL COMMENT '消费金额',
    description VARCHAR(255) DEFAULT NULL COMMENT '消费描述',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '消费时间',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_service_type (service_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消费记录表';

-- 4. 邀请记录表
CREATE TABLE invite_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inviter_id INT NOT NULL COMMENT '邀请人ID',
    invitee_id INT NOT NULL COMMENT '被邀请人ID',
    invite_code VARCHAR(20) NOT NULL COMMENT '使用的邀请码',
    reward_amount DECIMAL(10,2) DEFAULT 5.00 COMMENT '邀请奖励金额',
    status TINYINT DEFAULT 1 COMMENT '状态：1已发放，0待发放',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '邀请时间',
    
    FOREIGN KEY (inviter_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (invitee_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_inviter_id (inviter_id),
    INDEX idx_invitee_id (invitee_id),
    INDEX idx_invite_code (invite_code),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='邀请记录表';

-- 5. 系统配置表
CREATE TABLE system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键',
    config_value TEXT NOT NULL COMMENT '配置值',
    description VARCHAR(255) DEFAULT NULL COMMENT '配置描述',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- 插入默认配置
INSERT INTO system_config (config_key, config_value, description) VALUES
('invite_reward', '5.00', '邀请奖励金额'),
('new_user_bonus', '10.00', '新用户注册奖励'),
('sql_to_er_cost', '1.00', 'SQL转ER图服务费用'),
('defense_questions_cost', '2.00', '论文答辩问题生成费用'),
('test_case_cost', '1.50', '测试用例生成费用'),
('paper_structure_cost', '2.50', '论文结构生成费用');

-- 6. 用户会话表（可选，用于记住登录状态）
CREATE TABLE user_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用户ID',
    session_token VARCHAR(255) NOT NULL UNIQUE COMMENT '会话令牌',
    expires_at TIMESTAMP NOT NULL COMMENT '过期时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_session_token (session_token),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户会话表';

-- 创建生成邀请码的函数
DELIMITER //
CREATE FUNCTION generate_invite_code() RETURNS VARCHAR(20)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE code VARCHAR(20);
    DECLARE done INT DEFAULT 0;
    
    REPEAT
        SET code = CONCAT(
            CHAR(65 + FLOOR(RAND() * 26)),  -- A-Z
            CHAR(65 + FLOOR(RAND() * 26)),  -- A-Z
            LPAD(FLOOR(RAND() * 1000000), 6, '0')  -- 6位数字
        );
        
        SELECT COUNT(*) INTO done FROM users WHERE invite_code = code;
    UNTIL done = 0 END REPEAT;
    
    RETURN code;
END //
DELIMITER ;

-- 创建用户余额变更的存储过程
DELIMITER //
CREATE PROCEDURE update_user_balance(
    IN p_user_id INT,
    IN p_amount DECIMAL(10,2),
    IN p_type VARCHAR(20),  -- 'recharge' 或 'consumption'
    IN p_description VARCHAR(255)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    
    IF p_type = 'recharge' THEN
        UPDATE users SET 
            balance = balance + p_amount,
            total_recharge = total_recharge + p_amount
        WHERE id = p_user_id;
    ELSEIF p_type = 'consumption' THEN
        UPDATE users SET 
            balance = balance - p_amount,
            total_consumption = total_consumption + p_amount
        WHERE id = p_user_id AND balance >= p_amount;
        
        IF ROW_COUNT() = 0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '余额不足';
        END IF;
    END IF;
    
    COMMIT;
END //
DELIMITER ;

-- 7. 论文答辩问题生成历史记录表
CREATE TABLE defense_question_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用户ID',
    session_id VARCHAR(50) NOT NULL COMMENT '会话ID',
    generation_mode VARCHAR(20) DEFAULT 'single' COMMENT '生成模式：single单次, category分类, fragment片段',
    thesis_title VARCHAR(255) NOT NULL COMMENT '论文标题',
    research_field VARCHAR(100) NOT NULL COMMENT '研究领域',
    thesis_data JSON NOT NULL COMMENT '论文输入数据',
    questions_data JSON NOT NULL COMMENT '生成的问题数据',
    generation_time INT DEFAULT 0 COMMENT '生成耗时（秒）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='论文答辩问题生成历史记录表';

-- 8. 论文生成历史记录表
CREATE TABLE paper_generation_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用户ID',
    session_id VARCHAR(50) NOT NULL COMMENT '会话ID',
    paper_title VARCHAR(255) NOT NULL COMMENT '论文标题',
    research_field VARCHAR(100) NOT NULL COMMENT '研究领域',
    paper_type VARCHAR(20) DEFAULT 'undergraduate' COMMENT '论文类型：undergraduate本科, master硕士, doctor博士',
    word_count INT DEFAULT 0 COMMENT '论文字数',
    paper_data JSON NOT NULL COMMENT '论文输入数据',
    content_data JSON NOT NULL COMMENT '生成的论文内容数据',
    generation_time INT DEFAULT 0 COMMENT '生成耗时（秒）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_paper_title (paper_title),
    INDEX idx_research_field (research_field),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='论文生成历史记录表';

-- 更新系统配置表，添加论文生成费用配置
INSERT INTO system_config (config_key, config_value, description) VALUES
('paper_generation_cost', '5.00', 'AI论文生成服务费用');
