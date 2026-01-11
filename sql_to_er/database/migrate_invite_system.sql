-- =====================================================
-- 邀请码系统升级迁移脚本
-- 添加邀请系统安全增强功能所需的数据库字段
-- 执行方式: mysql -u root -p your_database < migrate_invite_system.sql
-- =====================================================

-- 1. 为 users 表添加注册IP字段（用于防刷检查）
ALTER TABLE `users`
ADD COLUMN IF NOT EXISTS `register_ip` VARCHAR(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '注册IP地址' AFTER `last_login_ip`;

-- 如果 IF NOT EXISTS 不支持，使用以下备用语句（需先检查列是否存在）
-- ALTER TABLE `users` ADD COLUMN `register_ip` VARCHAR(45) NULL DEFAULT NULL COMMENT '注册IP地址';

-- 为 register_ip 添加索引（用于快速查询同IP注册数量）
CREATE INDEX IF NOT EXISTS `idx_register_ip` ON `users` (`register_ip`);


-- 2. 为 invite_records 表添加奖励类型字段
ALTER TABLE `invite_records`
ADD COLUMN IF NOT EXISTS `reward_type` VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'registration' COMMENT '奖励类型：registration注册奖励，first_recharge首充奖励' AFTER `reward_amount`;

-- 为 reward_type 添加索引
CREATE INDEX IF NOT EXISTS `idx_reward_type` ON `invite_records` (`reward_type`);


-- 3. 在 system_config 表中添加邀请系统相关配置
INSERT INTO `system_config` (`config_key`, `config_value`, `description`)
VALUES
    ('invite_reward', '5.00', '邀请注册奖励金额（元）'),
    ('invite_recharge_rate', '0.10', '首充返利比例（0.10表示10%）'),
    ('max_register_per_ip', '3', '同一IP 24小时内最大注册数量')
ON DUPLICATE KEY UPDATE
    `description` = VALUES(`description`);


-- 4. 查看当前表结构（验证迁移成功）
-- DESCRIBE users;
-- DESCRIBE invite_records;
-- SELECT * FROM system_config WHERE config_key LIKE 'invite%' OR config_key = 'max_register_per_ip';

-- =====================================================
-- 迁移完成说明：
-- 1. register_ip: 记录用户注册时的IP，用于限制同IP注册数量
-- 2. reward_type: 区分奖励类型（注册奖励/首充奖励）
-- 3. 新增系统配置项用于灵活控制邀请奖励参数
-- =====================================================
