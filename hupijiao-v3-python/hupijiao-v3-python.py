# *-* coding: UTF-8 *-*

import hashlib
import time
import json
import requests
import random
import string
import os
from urllib.parse import urlencode, unquote_plus

# 尝试从config文件加载域名配置
try:
    import config
    DEFAULT_DOMAIN = getattr(config, 'domain', 'http://localhost:5000')
except ImportError:
    DEFAULT_DOMAIN = 'http://localhost:5000'

def ksort(d):
    return [(k, d[k]) for k in sorted(d.keys())]

def generate_nonce_str(length=16):
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

class Hupi(object):
    def __init__(self, appid=None, appsecret=None, domain=None):
        """
        初始化虎皮椒支付
        优先级：参数传入 > 环境变量 > 默认值/配置文件
        """
        # AppID: 参数 > 环境变量 > 默认值
        self.appid = appid or os.getenv('HUPI_APPID', '201906173259')
        # AppSecret: 参数 > 环境变量 > 默认值
        self.AppSecret = appsecret or os.getenv('HUPI_APPSECRET', 'ad53393e3490b654819cfacc24af2c6f')
        # 域名: 参数 > 环境变量 > config文件
        self.domain = domain or os.getenv('SITE_DOMAIN', DEFAULT_DOMAIN)

        self.api_urls = [
            "https://api.xunhupay.com/payment/do.html",  # 正式环境
            "https://api.dpweixin.com/payment/do.html",  # 备用平台
            "https://api.diypc.com.cn/payment/do.html"   # 其他平台
        ]
        self.notify_url = self.domain + '/notify_url/'
        self.return_url = self.domain + '/payment/success/'
        self.callback_url = self.domain + '/payment/callback/'
    
    def curl(self, data, url):
        """发送HTTP请求"""
        data['hash'] = self.sign(data)
        print(f"支付请求数据: {data}")
        headers = {
            "Referer": config.domain,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        try:
            r = requests.post(url, data=data, headers=headers, timeout=30)
            print(f"支付接口响应: {r.status_code} - {r.text}")
            return r
        except Exception as e:
            print(f"支付请求异常: {e}")
            raise e

    def sign(self, attributes):
        """生成签名"""
        # 过滤空值并排序
        filtered_data = {k: v for k, v in attributes.items() if v is not None and v != ''}
        sorted_data = ksort(filtered_data)
        
        print(f"签名参数: {sorted_data}")
        
        # 构建签名字符串
        sign_str = urlencode(sorted_data)
        sign_str = unquote_plus(sign_str)
        sign_str += self.AppSecret
        
        print(f"签名字符串: {sign_str}")
        
        # 生成MD5签名
        m = hashlib.md5()
        m.update(sign_str.encode('utf-8'))
        sign = m.hexdigest().lower()  # 确保是小写
        
        print(f"生成签名: {sign}")
        return sign

    def Pay(self, trade_order_id, payment, total_fee, title, **kwargs):
        """
        发起支付请求
        payment: alipay(支付宝)
        """
        # 只支持支付宝
        if payment != 'alipay':
            raise Exception("当前仅支持支付宝支付")
            
        data = {
            "version": "1.1",
            "appid": self.appid,
            "trade_order_id": trade_order_id,
            "total_fee": str(total_fee),
            "title": title[:127],  # 限制标题长度
            "time": str(int(time.time())),
            "notify_url": self.notify_url,
            "return_url": self.return_url,
            "callback_url": self.callback_url,
            "nonce_str": generate_nonce_str(16),
            "plugins": "flask_app"
        }
        
        # 添加可选参数
        if kwargs.get('attach'):
            data['attach'] = kwargs['attach']
        
        # 尝试不同的API接口
        last_error = None
        for api_url in self.api_urls:
            try:
                print(f"尝试支付接口: {api_url}")
                response = self.curl(data, api_url)
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        if result.get('errcode') == 0:
                            return response
                        else:
                            print(f"支付接口返回错误: {result}")
                            last_error = result.get('errmsg', '支付接口错误')
                    except json.JSONDecodeError:
                        print(f"支付接口返回非JSON数据: {response.text}")
                        last_error = "支付接口返回格式错误"
                else:
                    print(f"支付接口HTTP错误: {response.status_code}")
                    last_error = f"HTTP {response.status_code}"
                    
            except Exception as e:
                print(f"支付接口 {api_url} 调用失败: {e}")
                last_error = str(e)
                continue
        
        # 所有接口都失败，抛出异常
        raise Exception(f"所有支付接口都无法使用，最后错误: {last_error}")
    
    def verify_notify(self, post_data):
        """验证支付通知签名"""
        try:
            received_hash = post_data.pop('hash', '')
            calculated_hash = self.sign(post_data)
            return received_hash == calculated_hash
        except Exception as e:
            print(f"验证通知签名失败: {e}")
            return False

if __name__ == "__main__":
    obj = Hupi()
    r = obj.Pay("2_13534545343dfd","alipay","0.1","test")
    print(r,r.text)
    print(r.json()["url"])
