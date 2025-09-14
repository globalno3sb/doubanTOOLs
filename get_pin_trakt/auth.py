# -*- coding: utf-8 -*-
"""
认证模块 - Trakt OAuth 认证逻辑
"""
import requests
import time
import json

def get_device_code(client_id):
    """获取设备代码"""
    url = "https://api.trakt.tv/oauth/device/code"
    payload = {"client_id": client_id}
    
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"获取设备代码失败: {e}")
        return None

def poll_for_token(device_code, interval, expires_in, client_id, client_secret):
    """轮询获取访问令牌"""
    url = "https://api.trakt.tv/oauth/device/token"
    payload = {
        "code": device_code,
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    start_time = time.time()
    
    print("\n请按照以下步骤操作:")
    print("1. 在浏览器中打开上述验证网址")
    print("2. 输入显示的 PIN 码")
    print("3. 授权应用程序")
    print("4. 等待系统自动获取访问令牌...")
    print("-" * 40)

    while time.time() - start_time < expires_in:
        try:
            r = requests.post(url, json=payload, timeout=30)
            
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 400:
                # 授权还没确认，继续等待
                pass
            elif r.status_code == 404:
                print("设备代码无效")
                break
            elif r.status_code == 409:
                print("该设备代码已经被使用过")
                break
            elif r.status_code == 410:
                print("该设备代码已过期")
                break
            elif r.status_code == 418:
                print("授权尚未确认，请检查是否已完成浏览器中的授权步骤")
            elif r.status_code == 429:
                print("请求过于频繁，等待稍后重试...")
                time.sleep(interval + 5)
            else:
                print(f"未知错误: HTTP {r.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            
        # 显示等待提示
        remaining = int(expires_in - (time.time() - start_time))
        if remaining % 10 == 0:  # 每10秒显示一次
            print(f"等待中... 剩余时间: {remaining}秒")
            
        time.sleep(interval)
    
    return None

def save_token(token_data, output_path):
    """保存令牌到文件"""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存令牌失败: {e}")
        return False