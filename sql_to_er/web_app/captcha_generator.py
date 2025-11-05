"""
高级图形验证码生成器 - 生成专业级验证码图片
包含噪点、干扰线、扭曲效果等高级特性
"""

import random
import string
import io
import base64
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

class AdvancedCaptchaGenerator:
    """高级图形验证码生成器"""

    def __init__(self, width=120, height=40):
        self.width = width
        self.height = height
        self.font_size = 20
        
    def generate_text(self, length=4):
        """生成验证码文本 - 排除容易混淆的字符"""
        # 排除 0、O、I、l、1 等容易混淆的字符
        chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
        return ''.join(random.choices(chars, k=length))
    
    def get_random_color(self, min_val=0, max_val=255):
        """获取随机颜色"""
        return (
            random.randint(min_val, max_val),
            random.randint(min_val, max_val),
            random.randint(min_val, max_val)
        )
    
    def draw_interference_lines(self, draw):
        """绘制干扰线"""
        for _ in range(random.randint(3, 6)):
            x1 = random.randint(0, self.width)
            y1 = random.randint(0, self.height)
            x2 = random.randint(0, self.width)
            y2 = random.randint(0, self.height)
            draw.line([(x1, y1), (x2, y2)], fill=self.get_random_color(100, 200), width=1)
    
    def draw_interference_points(self, draw):
        """绘制干扰点"""
        for _ in range(random.randint(20, 40)):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            draw.point((x, y), fill=self.get_random_color(50, 150))
    
    def create_font(self):
        """创建字体"""
        try:
            # 尝试使用系统字体
            font_paths = [
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/calibri.ttf",
                "/System/Library/Fonts/Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ]
            
            for font_path in font_paths:
                try:
                    return ImageFont.truetype(font_path, self.font_size)
                except:
                    continue
            
            # 如果没有找到字体，使用默认字体
            return ImageFont.load_default()
        except:
            return ImageFont.load_default()
    
    def generate_simple_captcha(self):
        """生成简单清晰的验证码图片"""
        # 生成验证码文本
        text = self.generate_text()

        # 创建图片，使用白色背景
        image = Image.new('RGB', (self.width, self.height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)

        # 创建字体
        font = self.create_font()

        # 绘制文字 - 精确计算位置确保所有字符可见
        total_text_width = len(text) * 25  # 每个字符预留25像素
        start_x = (self.width - total_text_width) // 2

        for i, char in enumerate(text):
            x = start_x + i * 25 + random.randint(-3, 3)
            y = 8 + random.randint(-2, 2)

            # 使用深色字体
            color = self.get_random_color(0, 80)
            draw.text((x, y), char, font=font, fill=color)

        # 添加轻微的干扰线
        for _ in range(2):
            x1 = random.randint(0, self.width)
            y1 = random.randint(0, self.height)
            x2 = random.randint(0, self.width)
            y2 = random.randint(0, self.height)
            draw.line([(x1, y1), (x2, y2)], fill=self.get_random_color(150, 200), width=1)

        # 添加少量噪点
        for _ in range(15):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            draw.point((x, y), fill=self.get_random_color(100, 180))

        # 转换为base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return text, f"data:image/png;base64,{img_str}"

    def create_gradient_background(self, image):
        """创建渐变背景"""
        draw = ImageDraw.Draw(image)
        for y in range(self.height):
            # 创建从浅到深的渐变
            ratio = y / self.height
            r = int(245 + ratio * 10)
            g = int(248 + ratio * 7)
            b = int(252 + ratio * 3)
            color = (min(255, r), min(255, g), min(255, b))
            draw.line([(0, y), (self.width, y)], fill=color)

    def draw_noise_points(self, draw, count=100):
        """绘制噪点效果"""
        for _ in range(count):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            # 使用半透明的彩色噪点
            color = self.get_random_color(80, 200)
            draw.point((x, y), fill=color)
            # 有时绘制2x2的点
            if random.random() < 0.3:
                draw.point((x+1, y), fill=color)
                draw.point((x, y+1), fill=color)

    def draw_bezier_curves(self, draw, count=5):
        """绘制贝塞尔曲线干扰线"""
        for _ in range(count):
            # 随机起点和终点
            start_x = random.randint(0, self.width // 3)
            start_y = random.randint(0, self.height)
            end_x = random.randint(2 * self.width // 3, self.width)
            end_y = random.randint(0, self.height)

            # 控制点
            ctrl1_x = random.randint(self.width // 4, 3 * self.width // 4)
            ctrl1_y = random.randint(0, self.height)
            ctrl2_x = random.randint(self.width // 4, 3 * self.width // 4)
            ctrl2_y = random.randint(0, self.height)

            # 绘制贝塞尔曲线
            points = []
            for t in range(0, 101, 2):
                t = t / 100.0
                x = int((1-t)**3 * start_x + 3*(1-t)**2*t * ctrl1_x + 3*(1-t)*t**2 * ctrl2_x + t**3 * end_x)
                y = int((1-t)**3 * start_y + 3*(1-t)**2*t * ctrl1_y + 3*(1-t)*t**2 * ctrl2_y + t**3 * end_y)
                points.append((x, y))

            # 绘制曲线
            color = self.get_random_color(120, 180)
            for i in range(len(points) - 1):
                draw.line([points[i], points[i+1]], fill=color, width=random.randint(1, 2))

    def create_distorted_char(self, char, font):
        """创建轻微扭曲的字符图片"""
        # 创建字符图片
        char_size = 35
        char_img = Image.new('RGBA', (char_size, char_size), (255, 255, 255, 0))
        char_draw = ImageDraw.Draw(char_img)

        # 随机字体大小（范围缩小）
        font_size = random.randint(18, 22)
        try:
            font = ImageFont.truetype(font.path, font_size) if hasattr(font, 'path') else font
        except:
            pass

        # 随机颜色
        color = self.get_random_color(30, 120)

        # 绘制字符
        char_draw.text((8, 6), char, font=font, fill=color)

        # 轻微随机旋转（减少角度）
        rotation_angle = random.randint(-15, 15)
        if rotation_angle != 0:
            char_img = char_img.rotate(rotation_angle, expand=False)

        return char_img

    def generate_professional_captcha(self):
        """生成清晰的专业级验证码"""
        # 生成验证码文本
        text = self.generate_text()

        # 创建图片
        image = Image.new('RGB', (self.width, self.height), (255, 255, 255))

        # 创建渐变背景
        self.create_gradient_background(image)

        draw = ImageDraw.Draw(image)

        # 绘制少量贝塞尔曲线干扰线
        self.draw_bezier_curves(draw, 2)

        # 创建字体
        font = self.create_font()

        # 绘制扭曲的字符
        char_spacing = (self.width - 20) // len(text)
        for i, char in enumerate(text):
            # 创建扭曲字符
            char_img = self.create_distorted_char(char, font)

            # 计算位置
            x = 10 + i * char_spacing + random.randint(-2, 2)
            y = random.randint(2, 8)

            # 粘贴字符
            if char_img.mode == 'RGBA':
                image.paste(char_img, (x, y), char_img)
            else:
                image.paste(char_img, (x, y))

        # 绘制少量噪点
        self.draw_noise_points(draw, 30)

        # 不添加模糊效果，保持清晰

        # 轻微调整对比度
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)

        # 转换为base64，使用高质量
        buffer = io.BytesIO()
        image.save(buffer, format='PNG', quality=100, optimize=True)
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return text, f"data:image/png;base64,{img_str}"
    
    def generate_advanced_captcha(self):
        """生成高级验证码（带扭曲效果）"""
        text = self.generate_text()
        
        # 创建更大的临时图片用于扭曲
        temp_width = self.width + 20
        temp_height = self.height + 20
        temp_image = Image.new('RGB', (temp_width, temp_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(temp_image)
        
        # 渐变背景
        for y in range(temp_height):
            color_val = 240 + int(15 * math.sin(y * 0.1))
            color = (color_val, color_val, color_val)
            draw.line([(0, y), (temp_width, y)], fill=color)
        
        # 绘制干扰线
        for _ in range(random.randint(2, 4)):
            x1 = random.randint(0, temp_width)
            y1 = random.randint(0, temp_height)
            x2 = random.randint(0, temp_width)
            y2 = random.randint(0, temp_height)
            draw.line([(x1, y1), (x2, y2)], fill=self.get_random_color(150, 200), width=2)
        
        # 创建字体
        font = self.create_font()
        
        # 绘制文字 - 改进布局确保所有字符可见
        char_width = (temp_width - 40) // len(text)  # 留出更多边距
        for i, char in enumerate(text):
            x = 20 + char_width * i + random.randint(0, 10)
            y = random.randint(5, 10)

            # 随机旋转角度
            angle = random.randint(-12, 12)

            # 创建单个字符图片，增大尺寸
            char_img = Image.new('RGBA', (35, 35), (255, 255, 255, 0))
            char_draw = ImageDraw.Draw(char_img)
            char_draw.text((8, 8), char, font=font, fill=self.get_random_color(0, 80))

            # 旋转字符
            if angle != 0:
                char_img = char_img.rotate(angle, expand=True)

            # 粘贴到主图片
            temp_image.paste(char_img, (x, y), char_img)
        
        # 添加噪点
        for _ in range(random.randint(30, 60)):
            x = random.randint(0, temp_width)
            y = random.randint(0, temp_height)
            draw.point((x, y), fill=self.get_random_color(100, 200))
        
        # 裁剪到目标尺寸
        image = temp_image.crop((10, 10, self.width + 10, self.height + 10))
        
        # 转换为base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return text, f"data:image/png;base64,{img_str}"
