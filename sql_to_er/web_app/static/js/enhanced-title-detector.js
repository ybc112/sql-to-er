/**
 * 智能标题识别算法 - 增强版
 * 基于机器学习特征和规则引擎的混合方法
 */

class EnhancedTitleDetector {
    constructor() {
        // 标题识别规则配置
        this.titleRules = {
            // 明确的标题模式（高权重）
            explicit: [
                { pattern: /^第[一二三四五六七八九十\d]+章\s*(.*)/, level: 1, weight: 0.95 },
                { pattern: /^第[一二三四五六七八九十\d]+节\s*(.*)/, level: 2, weight: 0.90 },
                { pattern: /^\d+\.\s*(.+)/, level: 2, weight: 0.85 },
                { pattern: /^\d+\.\d+\s*(.+)/, level: 3, weight: 0.85 },
                { pattern: /^\d+\.\d+\.\d+\s*(.+)/, level: 4, weight: 0.80 },
                { pattern: /^[一二三四五六七八九十]+、\s*(.*)/, level: 2, weight: 0.80 },
                { pattern: /^\([一二三四五六七八九十\d]+\)\s*(.*)/, level: 3, weight: 0.75 },
                { pattern: /^[①②③④⑤⑥⑦⑧⑨⑩]\s*(.*)/, level: 3, weight: 0.75 }
            ],
            // 学术标题关键词（中权重）
            academic: [
                { pattern: /^摘\s*要$/i, level: 1, weight: 0.95 },
                { pattern: /^abstract$/i, level: 1, weight: 0.95 },
                { pattern: /^引\s*言$/i, level: 1, weight: 0.90 },
                { pattern: /^前\s*言$/i, level: 1, weight: 0.90 },
                { pattern: /^绪\s*论$/i, level: 1, weight: 0.90 },
                { pattern: /^结\s*论$/i, level: 1, weight: 0.90 },
                { pattern: /^总\s*结$/i, level: 1, weight: 0.90 },
                { pattern: /^参考文献$/i, level: 1, weight: 0.95 },
                { pattern: /^致\s*谢$/i, level: 1, weight: 0.90 },
                { pattern: /^附\s*录/i, level: 1, weight: 0.85 },
                { pattern: /^目\s*录$/i, level: 1, weight: 0.95 }
            ],
            // 通用学术概念（中权重）
            concepts: [
                { keywords: ['研究背景', '研究现状', '文献综述'], level: 2, weight: 0.70 },
                { keywords: ['研究方法', '实验方法', '技术路线'], level: 2, weight: 0.70 },
                { keywords: ['系统设计', '架构设计', '模块设计'], level: 2, weight: 0.70 },
                { keywords: ['实验结果', '结果分析', '性能分析'], level: 2, weight: 0.70 },
                { keywords: ['问题分析', '需求分析', '可行性分析'], level: 2, weight: 0.70 },
                { keywords: ['总结展望', '未来工作', '改进方向'], level: 2, weight: 0.70 }
            ]
        };

        // 特征权重配置
        this.featureWeights = {
            length: 0.20,           // 长度特征
            position: 0.15,         // 位置特征
            formatting: 0.25,       // 格式特征
            semantic: 0.30,         // 语义特征
            context: 0.10           // 上下文特征
        };

        // 标题长度阈值
        this.lengthThresholds = {
            min: 2,         // 最小长度
            max: 80,        // 最大长度
            optimal: 30     // 最优长度
        };

        // 语义特征词汇库
        this.semanticFeatures = {
            titleWords: [
                '研究', '分析', '设计', '实现', '方法', '算法', '模型', '系统',
                '技术', '应用', '评估', '优化', '改进', '创新', '探索', '开发',
                '建构', '构建', '框架', '机制', '策略', '方案', '模式', '理论'
            ],
            fieldTerms: [
                '计算机', '网络', '数据库', '人工智能', '机器学习', '深度学习',
                '软件工程', '信息系统', '电子商务', '物联网', '云计算', '大数据'
            ],
            actionWords: [
                '基于', '面向', '针对', '关于', '论', '浅谈', '探讨', '初探'
            ]
        };

        // 初始化统计信息
        this.statistics = {
            totalProcessed: 0,
            correctDetections: 0,
            falsePositives: 0,
            falseNegatives: 0
        };
    }

    /**
     * 主要检测方法
     * @param {string} text - 待检测的文本
     * @param {Object} context - 上下文信息
     * @returns {Object} 检测结果
     */
    detectTitles(text, context = {}) {
        const lines = this.preprocessText(text);
        const results = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (!line.trim()) continue;

            const detection = this.analyzeLine(line, i, lines, context);
            results.push({
                text: line,
                lineNumber: i,
                isTitle: detection.isTitle,
                confidence: detection.confidence,
                level: detection.level,
                features: detection.features,
                reasoning: detection.reasoning
            });
        }

        // 后处理优化
        return this.postProcessResults(results);
    }

    /**
     * 文本预处理
     */
    preprocessText(text) {
        return text
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0);
    }

    /**
     * 分析单行文本
     */
    analyzeLine(line, position, allLines, context) {
        const features = this.extractFeatures(line, position, allLines, context);
        const ruleScore = this.applyRules(line);
        const mlScore = this.computeMLScore(features);
        
        // 综合评分
        const finalScore = this.combineScores(ruleScore, mlScore, features);
        
        const isTitle = finalScore.score > 0.5;
        const level = this.determineLevel(line, finalScore.score, ruleScore.level);

        return {
            isTitle,
            confidence: finalScore.score,
            level,
            features,
            reasoning: finalScore.reasoning
        };
    }

    /**
     * 特征提取
     */
    extractFeatures(line, position, allLines, context) {
        const features = {};

        // 长度特征
        features.length = this.analyzeLengthFeature(line);
        
        // 位置特征
        features.position = this.analyzePositionFeature(position, allLines.length);
        
        // 格式特征  
        features.formatting = this.analyzeFormattingFeature(line);
        
        // 语义特征
        features.semantic = this.analyzeSemanticFeature(line);
        
        // 上下文特征
        features.context = this.analyzeContextFeature(line, position, allLines);

        return features;
    }

    /**
     * 长度特征分析
     */
    analyzeLengthFeature(line) {
        const length = line.length;
        const { min, max, optimal } = this.lengthThresholds;

        if (length < min || length > max) {
            return { score: 0, reason: '长度超出合理范围' };
        }

        // 使用正态分布函数计算最优分数
        const score = Math.exp(-Math.pow(length - optimal, 2) / (2 * Math.pow(optimal / 3, 2)));
        
        return {
            score,
            length,
            reason: length <= optimal ? '长度适中' : '长度偏长'
        };
    }

    /**
     * 位置特征分析
     */
    analyzePositionFeature(position, totalLines) {
        const relativePosition = position / Math.max(totalLines - 1, 1);
        
        // 文档开头和结尾更可能是标题
        let score;
        if (relativePosition < 0.1 || relativePosition > 0.9) {
            score = 0.8;
        } else if (relativePosition < 0.2 || relativePosition > 0.8) {
            score = 0.6;
        } else {
            score = 0.4;
        }

        return {
            score,
            position,
            relativePosition,
            reason: `文档相对位置 ${(relativePosition * 100).toFixed(1)}%`
        };
    }

    /**
     * 格式特征分析
     */
    analyzeFormattingFeature(line) {
        const features = {
            score: 0,
            details: {},
            reason: []
        };

        // 检查是否包含标点符号（标题通常不以句号结尾）
        if (!line.endsWith('。') && !line.endsWith('.')) {
            features.score += 0.3;
            features.reason.push('不以句号结尾');
        }

        // 检查是否包含问号或冒号（可能是标题）
        if (line.includes('？') || line.includes('?') || line.includes('：') || line.includes(':')) {
            features.score += 0.2;
            features.reason.push('包含问号或冒号');
        }

        // 检查是否全为大写英文（可能是标题）
        if (/^[A-Z\s]+$/.test(line) && line.length > 2) {
            features.score += 0.4;
            features.reason.push('全大写英文');
        }

        // 检查数字开头（章节编号）
        if (/^\d+/.test(line)) {
            features.score += 0.5;
            features.reason.push('数字开头');
        }

        // 检查是否包含过多逗号（标题通常较少逗号）
        const commaCount = (line.match(/[，,]/g) || []).length;
        if (commaCount === 0) {
            features.score += 0.2;
            features.reason.push('无逗号');
        } else if (commaCount > 3) {
            features.score -= 0.3;
            features.reason.push('逗号过多');
        }

        features.details = {
            endsWithPeriod: line.endsWith('。') || line.endsWith('.'),
            hasQuestionMark: line.includes('？') || line.includes('?'),
            hasColon: line.includes('：') || line.includes(':'),
            isAllCaps: /^[A-Z\s]+$/.test(line),
            startsWithNumber: /^\d+/.test(line),
            commaCount
        };

        return features;
    }

    /**
     * 语义特征分析
     */
    analyzeSemanticFeature(line) {
        const features = {
            score: 0,
            matches: [],
            reason: []
        };

        // 检查标题关键词
        const titleWordMatches = this.semanticFeatures.titleWords.filter(word => 
            line.includes(word)
        );
        if (titleWordMatches.length > 0) {
            features.score += Math.min(titleWordMatches.length * 0.2, 0.6);
            features.matches.push(...titleWordMatches);
            features.reason.push(`包含标题词: ${titleWordMatches.join(', ')}`);
        }

        // 检查领域术语
        const fieldTermMatches = this.semanticFeatures.fieldTerms.filter(term => 
            line.includes(term)
        );
        if (fieldTermMatches.length > 0) {
            features.score += Math.min(fieldTermMatches.length * 0.15, 0.3);
            features.matches.push(...fieldTermMatches);
            features.reason.push(`包含领域术语: ${fieldTermMatches.join(', ')}`);
        }

        // 检查动作词
        const actionWordMatches = this.semanticFeatures.actionWords.filter(word => 
            line.includes(word)
        );
        if (actionWordMatches.length > 0) {
            features.score += Math.min(actionWordMatches.length * 0.1, 0.2);
            features.matches.push(...actionWordMatches);
            features.reason.push(`包含动作词: ${actionWordMatches.join(', ')}`);
        }

        // 检查是否包含过多连接词（标题通常连接词较少）
        const connectors = ['的', '和', '与', '或', '但是', '然而', '因此', '所以'];
        const connectorCount = connectors.filter(connector => line.includes(connector)).length;
        if (connectorCount > 2) {
            features.score -= 0.2;
            features.reason.push('连接词过多');
        }

        return features;
    }

    /**
     * 上下文特征分析
     */
    analyzeContextFeature(line, position, allLines) {
        const features = {
            score: 0,
            reason: []
        };

        // 检查前后行是否为空行（标题前后通常有空行）
        const prevLine = position > 0 ? allLines[position - 1]?.trim() : '';
        const nextLine = position < allLines.length - 1 ? allLines[position + 1]?.trim() : '';

        if (!prevLine && nextLine) {
            features.score += 0.3;
            features.reason.push('前面有空行');
        }

        if (!nextLine && prevLine) {
            features.score += 0.2;
            features.reason.push('后面有空行');
        }

        // 检查后续行是否像正文（长度较长，包含句号）
        const nextFewLines = allLines.slice(position + 1, position + 3);
        const hasContentAfter = nextFewLines.some(line => 
            line && line.length > 50 && (line.includes('。') || line.includes('.'))
        );
        
        if (hasContentAfter) {
            features.score += 0.4;
            features.reason.push('后续有正文内容');
        }

        return features;
    }

    /**
     * 应用规则评分
     */
    applyRules(line) {
        let maxScore = 0;
        let level = 2;
        let matchedRule = null;

        // 检查明确模式
        for (const rule of this.titleRules.explicit) {
            if (rule.pattern.test(line)) {
                if (rule.weight > maxScore) {
                    maxScore = rule.weight;
                    level = rule.level;
                    matchedRule = rule;
                }
            }
        }

        // 检查学术标题
        for (const rule of this.titleRules.academic) {
            if (rule.pattern.test(line)) {
                if (rule.weight > maxScore) {
                    maxScore = rule.weight;
                    level = rule.level;
                    matchedRule = rule;
                }
            }
        }

        // 检查概念关键词
        for (const rule of this.titleRules.concepts) {
            const hasKeyword = rule.keywords.some(keyword => line.includes(keyword));
            if (hasKeyword && rule.weight > maxScore) {
                maxScore = rule.weight;
                level = rule.level;
                matchedRule = rule;
            }
        }

        return {
            score: maxScore,
            level,
            rule: matchedRule
        };
    }

    /**
     * 计算机器学习评分
     */
    computeMLScore(features) {
        let score = 0;
        
        // 加权计算各特征分数
        score += features.length.score * this.featureWeights.length;
        score += features.position.score * this.featureWeights.position;
        score += features.formatting.score * this.featureWeights.formatting;
        score += features.semantic.score * this.featureWeights.semantic;
        score += features.context.score * this.featureWeights.context;

        return Math.min(score, 1.0); // 确保不超过1
    }

    /**
     * 综合评分
     */
    combineScores(ruleScore, mlScore, features) {
        // 如果规则匹配度很高，优先使用规则分数
        if (ruleScore.score > 0.8) {
            return {
                score: ruleScore.score,
                reasoning: `规则匹配: ${ruleScore.rule?.pattern || '明确模式'}`
            };
        }

        // 否则综合规则和ML分数
        const combinedScore = (ruleScore.score * 0.6) + (mlScore * 0.4);
        
        let reasoning = [];
        if (ruleScore.score > 0.3) {
            reasoning.push(`规则匹配(${(ruleScore.score * 100).toFixed(1)}%)`);
        }
        if (mlScore > 0.3) {
            reasoning.push(`特征分析(${(mlScore * 100).toFixed(1)}%)`);
        }

        return {
            score: combinedScore,
            reasoning: reasoning.join(' + ') || '综合分析'
        };
    }

    /**
     * 确定标题级别
     */
    determineLevel(line, confidence, ruleLevel) {
        if (ruleLevel) return ruleLevel;

        // 基于内容推断级别
        if (/^第.*章/.test(line) || /^Chapter/i.test(line)) return 1;
        if (/^\d+\./.test(line)) return 2;
        if (/^\d+\.\d+/.test(line)) return 3;
        if (/^\d+\.\d+\.\d+/.test(line)) return 4;

        // 基于置信度推断
        if (confidence > 0.8) return 1;
        if (confidence > 0.6) return 2;
        return 3;
    }

    /**
     * 后处理结果
     */
    postProcessResults(results) {
        // 平滑处理：如果周围都是标题，提高当前行的标题概率
        for (let i = 1; i < results.length - 1; i++) {
            const current = results[i];
            const prev = results[i - 1];
            const next = results[i + 1];

            if (!current.isTitle && prev.isTitle && next.isTitle) {
                // 检查是否可能是被误判的标题
                if (current.confidence > 0.3 && current.text.length < 50) {
                    current.isTitle = true;
                    current.confidence = Math.min(current.confidence + 0.2, 0.9);
                    current.reasoning += ' + 上下文调整';
                }
            }
        }

        // 级别一致性检查
        this.adjustLevelConsistency(results);

        return results;
    }

    /**
     * 调整级别一致性
     */
    adjustLevelConsistency(results) {
        const titles = results.filter(r => r.isTitle);
        
        for (let i = 0; i < titles.length - 1; i++) {
            const current = titles[i];
            const next = titles[i + 1];

            // 如果级别跳跃过大，调整
            if (next.level - current.level > 2) {
                next.level = current.level + 1;
                next.reasoning += ' + 级别调整';
            }
        }
    }

    /**
     * 性能评估
     */
    evaluate(testData) {
        let correct = 0;
        let total = testData.length;

        for (const test of testData) {
            const result = this.detectTitles(test.text);
            const predicted = result.map(r => r.isTitle);
            const actual = test.labels;

            for (let i = 0; i < Math.min(predicted.length, actual.length); i++) {
                if (predicted[i] === actual[i]) correct++;
            }
        }

        const accuracy = correct / total;
        console.log(`标题识别准确率: ${(accuracy * 100).toFixed(2)}%`);
        
        return accuracy;
    }

    /**
     * 导出配置
     */
    exportConfig() {
        return {
            titleRules: this.titleRules,
            featureWeights: this.featureWeights,
            lengthThresholds: this.lengthThresholds,
            semanticFeatures: this.semanticFeatures
        };
    }

    /**
     * 导入配置
     */
    importConfig(config) {
        Object.assign(this, config);
    }
}

// 使用示例和测试
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EnhancedTitleDetector;
} else {
    // 浏览器环境下的全局导出
    window.EnhancedTitleDetector = EnhancedTitleDetector;
}

/**
 * 使用示例：
 * 
 * const detector = new EnhancedTitleDetector();
 * const text = `
 * 第一章 绪论
 * 
 * 1.1 研究背景
 * 随着计算机技术的快速发展，人工智能在各个领域都得到了广泛应用。
 * 
 * 1.2 研究意义
 * 本研究对于推动相关技术发展具有重要意义。
 * `;
 * 
 * const results = detector.detectTitles(text);
 * console.log(results);
 */