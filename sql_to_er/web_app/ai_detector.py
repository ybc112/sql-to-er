# -*- coding: utf-8 -*-
"""
AI内容检测模块
基于 Perplexity（困惑度）和 Burstiness（突发性）检测AI生成内容
"""

import math
import re
import numpy as np
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)

# 尝试导入深度学习库
try:
    import torch
    from transformers import GPT2LMHeadModel, GPT2Tokenizer, AutoModelForCausalLM, AutoTokenizer
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch/Transformers 未安装，将使用简化版检测")


class AIContentDetector:
    """AI内容检测器"""

    def __init__(self, model_name: str = 'gpt2', use_chinese_model: bool = False):
        """
        初始化检测器

        Args:
            model_name: 模型名称，默认 'gpt2'
            use_chinese_model: 是否使用中文模型
        """
        self.model = None
        self.tokenizer = None
        self.device = None
        self.model_loaded = False
        self.model_name = model_name
        self.current_language = None  # 当前加载的模型语言

        # 中文模型配置
        self.chinese_model_name = 'uer/gpt2-chinese-cluecorpussmall'
        self.english_model_name = 'gpt2'

        # 缓存两种模型
        self._zh_model = None
        self._zh_tokenizer = None
        self._en_model = None
        self._en_tokenizer = None

        # AI常用模板词/短语（中文）
        self.ai_template_phrases_zh = [
            "综上所述", "总而言之", "由此可见", "基于以上分析",
            "首先", "其次", "再次", "最后",  # 连续使用时
            "值得注意的是", "需要指出的是", "不可否认",
            "从某种程度上说", "在一定程度上",
            "具有重要意义", "具有深远影响",
            "本文将从以下几个方面", "主要包括以下几点",
            "综合来看", "总的来说", "概括而言",
            "通过上述分析", "经过深入研究",
            "这表明", "这说明", "这意味着",
            "进一步", "与此同时", "此外",
            "不仅...而且", "一方面...另一方面",
        ]

        # AI常用模板词/短语（英文）
        self.ai_template_phrases_en = [
            "in conclusion", "to summarize", "in summary",
            "it is worth noting", "it should be noted",
            "furthermore", "moreover", "additionally",
            "on the other hand", "in contrast",
            "as mentioned above", "as discussed",
            "this suggests that", "this indicates that",
            "it is important to", "it is essential to",
            "in this context", "in light of",
            "taking into account", "considering the fact",
        ]

        if TORCH_AVAILABLE:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            logger.info(f"使用设备: {self.device}")
            # 默认先加载英文模型
            self._load_model(model_name, use_chinese_model)

    def _is_chinese_text(self, text: str) -> bool:
        """
        检测文本是否主要是中文

        Args:
            text: 待检测文本

        Returns:
            True 如果中文字符占比超过30%
        """
        if not text:
            return False

        # 统计中文字符数量
        chinese_chars = 0
        total_chars = 0

        for char in text:
            if '\u4e00' <= char <= '\u9fff':  # 中文字符范围
                chinese_chars += 1
            if char.strip():  # 非空白字符
                total_chars += 1

        if total_chars == 0:
            return False

        # 中文占比超过30%则认为是中文文本
        chinese_ratio = chinese_chars / total_chars
        return chinese_ratio > 0.3

    def _switch_model(self, use_chinese: bool):
        """
        切换到对应语言的模型

        Args:
            use_chinese: 是否使用中文模型
        """
        target_lang = 'zh' if use_chinese else 'en'

        # 如果已经是目标语言的模型，直接返回
        if self.current_language == target_lang:
            return

        try:
            if use_chinese:
                # 使用中文模型
                if self._zh_model is None:
                    logger.info(f"首次加载中文模型: {self.chinese_model_name}")
                    self._zh_tokenizer = AutoTokenizer.from_pretrained(self.chinese_model_name)
                    self._zh_model = AutoModelForCausalLM.from_pretrained(self.chinese_model_name)
                    self._zh_model.to(self.device)
                    self._zh_model.eval()
                    logger.info("中文模型加载成功")

                self.model = self._zh_model
                self.tokenizer = self._zh_tokenizer
                self.model_name = self.chinese_model_name
                self.current_language = 'zh'

            else:
                # 使用英文模型
                if self._en_model is None:
                    logger.info(f"首次加载英文模型: {self.english_model_name}")
                    self._en_tokenizer = GPT2Tokenizer.from_pretrained(self.english_model_name)
                    self._en_model = GPT2LMHeadModel.from_pretrained(self.english_model_name)
                    self._en_model.to(self.device)
                    self._en_model.eval()
                    logger.info("英文模型加载成功")

                self.model = self._en_model
                self.tokenizer = self._en_tokenizer
                self.model_name = self.english_model_name
                self.current_language = 'en'

            self.model_loaded = True

        except Exception as e:
            logger.error(f"切换模型失败: {e}")
            # 如果切换失败，尝试使用另一个模型
            if self.model is not None:
                logger.info("保持使用当前模型")
            else:
                self.model_loaded = False

    def _load_model(self, model_name: str, use_chinese_model: bool):
        """加载语言模型"""
        try:
            if use_chinese_model:
                # 加载中文模型
                try:
                    self._zh_tokenizer = AutoTokenizer.from_pretrained(self.chinese_model_name)
                    self._zh_model = AutoModelForCausalLM.from_pretrained(self.chinese_model_name)
                    self._zh_model.to(self.device)
                    self._zh_model.eval()
                    self.model = self._zh_model
                    self.tokenizer = self._zh_tokenizer
                    self.model_name = self.chinese_model_name
                    self.current_language = 'zh'
                    logger.info(f"成功加载中文模型: {self.chinese_model_name}")
                except Exception as e:
                    logger.warning(f"加载中文模型失败: {e}，回退到英文模型")
                    use_chinese_model = False

            # 默认使用英文GPT2
            if not use_chinese_model:
                self._en_tokenizer = GPT2Tokenizer.from_pretrained(model_name)
                self._en_model = GPT2LMHeadModel.from_pretrained(model_name)
                self._en_model.to(self.device)
                self._en_model.eval()
                self.model = self._en_model
                self.tokenizer = self._en_tokenizer
                self.model_name = model_name
                self.current_language = 'en'
                logger.info(f"成功加载模型: {model_name}")

            self.model_loaded = True

        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            self.model_loaded = False

    def calculate_perplexity(self, text: str) -> float:
        """
        计算文本的困惑度

        困惑度越低，表示文本越"可预测"，越可能是AI生成
        困惑度越高，表示文本越"意外"，越可能是人类写作

        Args:
            text: 待检测文本

        Returns:
            困惑度值
        """
        if not self.model_loaded or not text.strip():
            return -1

        try:
            # 限制文本长度
            max_length = 1024

            # 编码文本
            encodings = self.tokenizer(
                text,
                return_tensors='pt',
                truncation=True,
                max_length=max_length
            )
            input_ids = encodings.input_ids.to(self.device)

            # 计算损失
            with torch.no_grad():
                outputs = self.model(input_ids, labels=input_ids)
                loss = outputs.loss

            # 困惑度 = exp(loss)
            perplexity = math.exp(loss.item())
            return perplexity

        except Exception as e:
            logger.error(f"计算困惑度失败: {e}")
            return -1

    def calculate_perplexity_per_sentence(self, text: str) -> List[float]:
        """
        计算每个句子的困惑度

        Args:
            text: 待检测文本

        Returns:
            每个句子的困惑度列表
        """
        # 分句（支持中英文）
        sentences = self._split_sentences(text)

        perplexities = []
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 10:  # 忽略太短的句子
                ppl = self.calculate_perplexity(sent)
                if ppl > 0:
                    perplexities.append(ppl)

        return perplexities

    def calculate_burstiness(self, text: str) -> float:
        """
        计算文本的突发性（Burstiness）

        突发性 = 句子困惑度的标准差
        突发性越低，表示文本越"均匀"，越可能是AI生成
        突发性越高，表示文本越"多变"，越可能是人类写作

        Args:
            text: 待检测文本

        Returns:
            突发性值
        """
        perplexities = self.calculate_perplexity_per_sentence(text)

        if len(perplexities) < 2:
            return 0

        return float(np.std(perplexities))

    def calculate_template_score(self, text: str) -> Dict[str, Any]:
        """
        计算模板词/短语匹配分数

        Args:
            text: 待检测文本

        Returns:
            模板匹配结果
        """
        text_lower = text.lower()

        # 检测中文模板词
        zh_matches = []
        for phrase in self.ai_template_phrases_zh:
            count = text.count(phrase)
            if count > 0:
                zh_matches.append({'phrase': phrase, 'count': count})

        # 检测英文模板词
        en_matches = []
        for phrase in self.ai_template_phrases_en:
            count = text_lower.count(phrase)
            if count > 0:
                en_matches.append({'phrase': phrase, 'count': count})

        # 计算模板词密度
        total_chars = len(text)
        total_matches = sum(m['count'] for m in zh_matches) + sum(m['count'] for m in en_matches)

        # 每1000字符的模板词数量
        density = (total_matches / max(total_chars, 1)) * 1000

        return {
            'zh_matches': zh_matches,
            'en_matches': en_matches,
            'total_matches': total_matches,
            'density': density
        }

    def calculate_sentence_uniformity(self, text: str) -> Dict[str, float]:
        """
        计算句子长度均匀度

        AI生成的文本句子长度往往更均匀

        Args:
            text: 待检测文本

        Returns:
            均匀度指标
        """
        sentences = self._split_sentences(text)
        lengths = [len(s.strip()) for s in sentences if len(s.strip()) > 5]

        if len(lengths) < 2:
            return {'mean': 0, 'std': 0, 'cv': 0}

        mean_len = np.mean(lengths)
        std_len = np.std(lengths)
        # 变异系数（CV）= 标准差/均值，越小越均匀
        cv = std_len / mean_len if mean_len > 0 else 0

        return {
            'mean': float(mean_len),
            'std': float(std_len),
            'cv': float(cv)  # 变异系数，AI文本通常 < 0.3
        }

    def _split_sentences(self, text: str) -> List[str]:
        """
        分句（支持中英文）

        Args:
            text: 文本

        Returns:
            句子列表
        """
        # 中英文分句
        pattern = r'[。！？.!?;；]+'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def detect(self, text: str, detailed: bool = False) -> Dict[str, Any]:
        """
        检测文本是否为AI生成

        Args:
            text: 待检测文本
            detailed: 是否返回详细分析

        Returns:
            检测结果
        """
        if not text or len(text.strip()) < 50:
            return {
                'success': False,
                'message': '文本太短，至少需要50个字符',
                'ai_probability': 0
            }

        text = text.strip()

        # 自动检测语言并切换模型
        is_chinese = self._is_chinese_text(text)
        if TORCH_AVAILABLE and self.model_loaded:
            self._switch_model(is_chinese)

        result = {
            'success': True,
            'text_length': len(text),
            'sentence_count': len(self._split_sentences(text)),
            'language': 'zh' if is_chinese else 'en'  # 返回检测到的语言
        }

        # 各项得分（满分100）
        scores = []
        score_details = []

        # 1. 困惑度分析
        if self.model_loaded:
            perplexity = self.calculate_perplexity(text)
            result['perplexity'] = round(perplexity, 2)

            # 困惑度评分：低困惑度 = 高AI概率
            # GPT-2对英文：AI文本通常 < 30，人类文本通常 > 60
            # 中文会有所不同
            if perplexity < 20:
                ppl_score = 90
            elif perplexity < 40:
                ppl_score = 70
            elif perplexity < 60:
                ppl_score = 50
            elif perplexity < 80:
                ppl_score = 30
            elif perplexity < 100:
                ppl_score = 20
            else:
                ppl_score = 10

            scores.append(ppl_score * 0.35)  # 权重35%
            score_details.append({
                'name': '困惑度分析',
                'value': perplexity,
                'score': ppl_score,
                'weight': 0.35,
                'interpretation': '困惑度越低，AI生成可能性越高'
            })

            # 2. 突发性分析
            burstiness = self.calculate_burstiness(text)
            result['burstiness'] = round(burstiness, 2)

            # 突发性评分：低突发性 = 高AI概率
            if burstiness < 10:
                burst_score = 85
            elif burstiness < 20:
                burst_score = 65
            elif burstiness < 40:
                burst_score = 45
            elif burstiness < 60:
                burst_score = 25
            else:
                burst_score = 10

            scores.append(burst_score * 0.30)  # 权重30%
            score_details.append({
                'name': '突发性分析',
                'value': burstiness,
                'score': burst_score,
                'weight': 0.30,
                'interpretation': '突发性越低，文本越均匀，AI生成可能性越高'
            })
        else:
            result['perplexity'] = None
            result['burstiness'] = None
            result['model_warning'] = '深度学习模型未加载，使用简化检测'

        # 3. 模板词分析
        template_result = self.calculate_template_score(text)
        result['template_matches'] = template_result['total_matches']
        result['template_density'] = round(template_result['density'], 2)

        # 模板词评分：高密度 = 高AI概率
        density = template_result['density']
        if density > 5:
            template_score = 80
        elif density > 3:
            template_score = 60
        elif density > 1.5:
            template_score = 40
        elif density > 0.5:
            template_score = 25
        else:
            template_score = 10

        scores.append(template_score * 0.20)  # 权重20%
        score_details.append({
            'name': '模板词分析',
            'value': density,
            'score': template_score,
            'weight': 0.20,
            'interpretation': '模板词密度越高，AI生成可能性越高'
        })

        # 4. 句子均匀度分析
        uniformity = self.calculate_sentence_uniformity(text)
        result['sentence_cv'] = round(uniformity['cv'], 3)

        # 均匀度评分：低变异系数 = 高AI概率
        cv = uniformity['cv']
        if cv < 0.2:
            uniformity_score = 75
        elif cv < 0.3:
            uniformity_score = 55
        elif cv < 0.4:
            uniformity_score = 35
        elif cv < 0.5:
            uniformity_score = 20
        else:
            uniformity_score = 10

        scores.append(uniformity_score * 0.15)  # 权重15%
        score_details.append({
            'name': '句式均匀度',
            'value': cv,
            'score': uniformity_score,
            'weight': 0.15,
            'interpretation': '句子长度越均匀，AI生成可能性越高'
        })

        # 计算综合AI概率
        ai_probability = sum(scores)

        # 如果模型未加载，调整权重
        if not self.model_loaded:
            # 只有模板词和均匀度，重新归一化
            ai_probability = (template_score * 0.6 + uniformity_score * 0.4)

        result['ai_probability'] = round(ai_probability, 1)

        # 判定结果 - 使用新阈值
        if ai_probability >= 80:
            result['verdict'] = '高度疑似AI生成'
            result['verdict_level'] = 'high'
        elif ai_probability >= 60:
            result['verdict'] = '可能包含AI辅助'
            result['verdict_level'] = 'medium'
        else:
            result['verdict'] = '未发现明显AI特征'
            result['verdict_level'] = 'low'

        if detailed:
            result['score_details'] = score_details
            result['template_phrases'] = {
                'zh': template_result['zh_matches'][:10],  # 最多显示10个
                'en': template_result['en_matches'][:10]
            }
            result['sentence_stats'] = uniformity

        return result

    def detect_sentences(self, text: str) -> List[Dict[str, Any]]:
        """
        逐句检测，标注每个句子的AI概率

        Args:
            text: 待检测文本

        Returns:
            每个句子的检测结果
        """
        if not self.model_loaded:
            return []

        # 自动检测语言并切换模型
        is_chinese = self._is_chinese_text(text)
        if TORCH_AVAILABLE:
            self._switch_model(is_chinese)

        sentences = self._split_sentences(text)
        results = []

        for i, sent in enumerate(sentences):
            sent = sent.strip()
            if len(sent) < 10:
                continue

            ppl = self.calculate_perplexity(sent)

            # 单句AI概率判断
            if ppl < 25:
                ai_prob = 85
            elif ppl < 40:
                ai_prob = 65
            elif ppl < 60:
                ai_prob = 45
            elif ppl < 80:
                ai_prob = 25
            else:
                ai_prob = 10

            results.append({
                'index': i,
                'sentence': sent,
                'perplexity': round(ppl, 2),
                'ai_probability': ai_prob
            })

        return results


class SimpleAIDetector:
    """
    简化版AI检测器（不依赖深度学习模型）
    基于统计特征和规则检测
    """

    def __init__(self):
        # AI常用模板词
        self.ai_patterns = {
            'zh': [
                "综上所述", "总而言之", "由此可见", "基于以上",
                "首先.*其次.*最后", "一方面.*另一方面",
                "值得注意", "需要指出", "不可否认",
                "具有重要意义", "具有深远影响",
                "进一步", "与此同时", "此外",
            ],
            'en': [
                r"in conclusion", r"to summarize", r"in summary",
                r"furthermore", r"moreover", r"additionally",
                r"it is (worth|important|essential)",
                r"on the other hand",
            ]
        }

        # 过于完美的结构模式
        self.structure_patterns = [
            r"第[一二三四五六七八九十]+[,，]",  # 第一，第二...
            r"[（(][1-9][)）]",  # (1) (2) (3)
            r"首先.*其次.*再次.*最后",  # 典型四段论
        ]

    def detect(self, text: str) -> Dict[str, Any]:
        """简化版检测"""
        if len(text) < 50:
            return {'success': False, 'message': '文本太短'}

        scores = []

        # 1. 模板词检测
        template_count = 0
        for pattern in self.ai_patterns['zh']:
            template_count += len(re.findall(pattern, text))
        for pattern in self.ai_patterns['en']:
            template_count += len(re.findall(pattern, text.lower()))

        template_density = template_count / (len(text) / 1000)
        if template_density > 3:
            scores.append(70)
        elif template_density > 1.5:
            scores.append(50)
        else:
            scores.append(20)

        # 2. 句子长度均匀度
        sentences = re.split(r'[。！？.!?]+', text)
        lengths = [len(s.strip()) for s in sentences if len(s.strip()) > 5]

        if len(lengths) >= 3:
            cv = np.std(lengths) / np.mean(lengths) if np.mean(lengths) > 0 else 0
            if cv < 0.25:
                scores.append(65)
            elif cv < 0.4:
                scores.append(40)
            else:
                scores.append(15)

        # 3. 结构模式检测
        structure_score = 0
        for pattern in self.structure_patterns:
            if re.search(pattern, text):
                structure_score += 20
        scores.append(min(structure_score, 60))

        ai_probability = np.mean(scores) if scores else 30

        return {
            'success': True,
            'ai_probability': round(ai_probability, 1),
            'template_density': round(template_density, 2),
            'verdict': '高度疑似AI生成' if ai_probability >= 80 else
                      ('可能包含AI辅助' if ai_probability >= 60 else '未发现明显AI特征'),
            'verdict_level': 'high' if ai_probability >= 80 else ('medium' if ai_probability >= 60 else 'low'),
            'note': '简化版检测，建议安装 PyTorch 获得更准确结果'
        }


# 单例模式
_detector_instance = None

def get_detector(use_simple: bool = False) -> AIContentDetector:
    """获取检测器实例"""
    global _detector_instance

    if use_simple or not TORCH_AVAILABLE:
        return SimpleAIDetector()

    if _detector_instance is None:
        _detector_instance = AIContentDetector()

    return _detector_instance


# 便捷函数
def detect_ai_content(text: str, detailed: bool = False) -> Dict[str, Any]:
    """
    检测文本是否为AI生成

    Args:
        text: 待检测文本
        detailed: 是否返回详细分析

    Returns:
        检测结果
    """
    detector = get_detector()
    return detector.detect(text, detailed)
